"""Operate isolated QEMU machines and collect guest assessment evidence."""

import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tarfile
import time


def observe(command, log_path, timeout, passphrase):
    deadline = time.monotonic() + timeout
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        recent = b""
        unlocked = False
        try:
            while selector.get_map():
                if time.monotonic() > deadline:
                    raise TimeoutError("The VM exceeded its time limit. Examine the serial log.")
                for key, _ in selector.select(timeout=1):
                    data = os.read(key.fd, 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    log.write(data)
                    log.flush()
                    recent = (recent + data)[-4096:]
                    if any(message in recent for message in (
                        b"Non interactive installation failed:",
                        b"Unable to allocate requested partition scheme.",
                        b"The following mandatory spokes are not completed:",
                        b"occurred during the execution of the post-installation script",
                    )):
                        raise ValueError(f"The installer rejected the configuration. Examine {log_path}.")
                    prompt = recent.lower()
                    if passphrase and not unlocked and b"passphrase" in prompt and b":" in prompt.split(b"passphrase")[-1]:
                        process.stdin.write((passphrase + "\n").encode())
                        process.stdin.flush()
                        unlocked = True
            rc = process.wait(timeout=max(1, deadline - time.monotonic()))
            if rc:
                raise ValueError(f"QEMU exited with status {rc}. Examine {log_path}.")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            selector.close()
            process.stdin.close()
            process.stdout.close()


def extract_evidence(archive, target):
    with tarfile.open(archive, "r:gz") as stream:
        members = stream.getmembers()
        if len(members) > 100 or sum(m.size for m in members) > 256 * 1024 * 1024:
            raise ValueError("The guest evidence exceeds the permitted size.")
        for member in members:
            path = Path(member.name)
            if not path.parts or path.is_absolute() or ".." in path.parts or path.parts[0] != "evidence":
                raise ValueError("The guest evidence contains an unsafe path.")
            if not member.isfile() and not member.isdir():
                raise ValueError("The guest evidence contains an unsafe file type.")
        if target.exists():
            raise ValueError("The evidence directory exists. Select a new VM directory.")
        target.mkdir(mode=0o700)
        # Only ordinary files and directories with constrained paths are accepted.
        for member in members:
            destination = target / member.name
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True, mode=0o700)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with stream.extractfile(member) as source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output)


def decode_evidence(stream, archive):
    marker = b"\nBALBOA_EVIDENCE_V1\n"
    if stream.stat().st_size > 256 * 1024 * 1024:
        raise ValueError("The evidence stream exceeds the permitted size.")
    data = stream.read_bytes()
    if data.count(marker) != 1:
        raise ValueError("The evidence stream must contain exactly one report frame.")
    payload = data.split(marker, 1)[1]
    if not payload.startswith(b"\x1f\x8b"):
        raise ValueError("The evidence frame does not contain a compressed archive.")
    archive.write_bytes(payload)


def inspect_dvd_evidence(manifest, evidence):
    if not manifest.get("package_source_policy"):
        return
    for name in ("native-before.json", "native-after.json", "native-initial-complete.json"):
        path = evidence / name
        if not path.is_file():
            raise ValueError(f"The guest lacks initial DVD package evidence: {name}.")
        record = json.loads(path.read_text())
        if record.get("passed") is not True or record.get("dvd_package_versions") != "passed":
            raise ValueError(f"The initial DVD package assessment did not pass: {name}.")


def inspect_system(manifest, evidence, definition):
    inspect_dvd_evidence(manifest, evidence)
    if not json.loads((evidence / "native-final.json").read_text())["passed"]:
        raise ValueError("The native Rocky policy tests did not pass.")
    packages = {line.rsplit("-", 2)[0] for line in (evidence / "packages.txt").read_text().splitlines()}
    forbidden = packages.intersection(definition["exclude"])
    if forbidden:
        raise ValueError(f"The guest contains excluded packages: {', '.join(sorted(forbidden))}.")
    if ("openssh-server" in packages) != (manifest["flavor"] == "server"):
        raise ValueError("The SSH server package does not match the selected flavor.")
    if manifest["flavor"] == "server" and (evidence / "sshd.txt").read_text().strip() != "active":
        raise ValueError("The server SSH service did not start.")
    mounts = {}
    for line in (evidence / "mounts.txt").read_text().splitlines():
        match = re.search(r"(/\S*)\s+(/dev/mapper/system-\S+)\s+(\S+)\s+(\S+)", line)
        if match:
            mounts[match[1]] = (match[2], set(match[4].split(",")))
    for volume in manifest["storage"]["volumes"]:
        if volume["mount"] == "swap":
            continue
        entry = mounts.get(volume["mount"])
        required = set(volume["options"].split(",")) - {"defaults", ""}
        if not entry or entry[0] != f'/dev/mapper/system-{volume["name"]}' or not required <= entry[1]:
            raise ValueError(f'The guest mount does not match the LVM policy: {volume["mount"]}.')
    if (evidence / "selinux.txt").read_text().strip() != "Enforcing":
        raise ValueError("The guest did not enforce SELinux.")
    if "crypt" not in (evidence / "storage.txt").read_text():
        raise ValueError("The guest did not report encrypted storage.")


def vm(args):
    from .cli import ROOT, run, sha256

    iso = args.iso.resolve()
    manifest = json.loads(iso.with_suffix(".json").read_text())
    if sha256(iso) != manifest["iso_sha256"]:
        raise ValueError("The custom ISO does not match its manifest.")
    if args.lab_secrets and not manifest["lab"]:
        raise ValueError("Lab credentials cannot unlock a production installation.")
    if manifest.get("boot_splash"):
        raise ValueError("Use scripts/start-qemu.py for graphical splash media and disk unlock. Omit --boot-splash for automated lab tests.")
    if not manifest["lab"]:
        raise ValueError("The automated VM command requires disposable lab media. Use the manual procedure for production media.")
    if args.phase == "boot" and args.lab_secrets is None:
        raise ValueError("Set --lab-secrets to unlock the encrypted test disk.")
    if args.timeout < 60:
        raise ValueError("The VM time limit must be at least 60 seconds.")
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    work.chmod(0o700)
    disk = work / "system.qcow2"
    identity = work / "machine.json"
    expected = {"iso_sha256": manifest["iso_sha256"], "firmware": args.firmware}
    if args.phase == "install":
        if disk.exists() or identity.exists():
            raise ValueError("The VM disk exists. Select a new VM directory.")
        run(["qemu-img", "create", "-f", "qcow2", disk, str(manifest["storage"]["disk_bytes"])])
        identity.write_text(json.dumps(expected) + "\n")
    elif not disk.is_file() or json.loads(identity.read_text()) != expected:
        raise ValueError("The VM disk identity does not match the image and firmware.")
    command = ["qemu-system-x86_64", "-machine", f"q35,accel={args.accel}",
               "-cpu", "host" if args.accel == "kvm" else "max", "-smp", "4", "-m", "4096",
               "-drive", f"file={disk},format=qcow2,if=virtio", "-nic", "user,model=virtio-net-pci",
               "-display", "none", "-serial", "stdio", "-monitor", "none", "-no-reboot"]
    if args.firmware == "uefi":
        variables = work / "OVMF_VARS.fd"
        if args.phase == "install":
            shutil.copyfile(args.ovmf_vars, variables)
        command += ["-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={args.ovmf_code.resolve()}",
                    "-drive", f"if=pflash,format=raw,unit=1,file={variables}"]
    if args.phase == "install":
        command += ["-cdrom", str(iso), "-boot", "once=d"]
    stream = work / "evidence.stream"
    archive = work / "evidence.tar.gz"
    command += ["-serial", f"file:{stream}"]
    # QEMU uses commas to separate drive and chardev properties.
    if any("," in str(p) for p in (iso, work, args.ovmf_code, args.ovmf_vars)):
        raise ValueError("QEMU paths cannot contain commas.")
    passphrase = None
    if args.lab_secrets:
        passphrase = json.loads(args.lab_secrets.read_text())["passphrase"]
    log = work / f"{args.phase}-{time.time_ns()}.log"
    print(f"The VM serial log is {log}.", flush=True)
    observe(command, log, args.timeout, passphrase)
    if args.phase == "install":
        if b"BALBOA_INSTALL_COMPLETE" not in log.read_bytes():
            raise ValueError("The installer did not report completion. Examine the serial log.")
        print("The installer stopped. Boot the VM to apply the security profile.")
        return
    if not stream.exists() or b"\nBALBOA_EVIDENCE_V1\n" not in stream.read_bytes():
        if b"BALBOA_REMEDIATION_COMPLETE" in log.read_bytes():
            print("Remediation completed. Boot the VM again for assessment.")
            return
        raise ValueError("The VM stopped without remediation or assessment evidence. Examine the serial log.")
    decode_evidence(stream, archive)
    target = work / "collected"
    extract_evidence(archive, target)
    evidence = target / "evidence"
    if not (evidence / "assessment.xml").exists():
        raise ValueError(f"The guest service failed before assessment. Examine {evidence}.")
    definition = json.loads((ROOT / "flavors" / f'{manifest["flavor"]}.json').read_text())
    inspect_system(manifest, evidence, definition)
    disk_info = json.loads(run(["qemu-img", "info", "--output=json", disk], capture_output=True, text=True).stdout)
    if disk_info["virtual-size"] != manifest["storage"]["disk_bytes"]:
        raise ValueError("The virtual disk size does not match the fixed storage policy.")
    print("The package boundary and fixed encrypted LVM mount tests passed.")
    run(["python3", ROOT / "guest/result_gate.py", evidence / "assessment.xml",
         "--profile", manifest["profile"]])
    if (evidence / "oscap-exit-status").read_text().strip() != "0":
        raise ValueError("The guest scanner returned an error or findings.")
    print(f"The automated assessment passed. Review the manual controls in {evidence}.")
