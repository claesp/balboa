"""Build authenticated Rocky Linux installation media."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from .render import render
from .vm import vm

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "sources.lock.json"
TOOLS = "localhost/balboa-tools:10"


def run(argv, **kwargs):
    return subprocess.run([str(arg) for arg in argv], check=True, **kwargs)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_lock():
    return json.loads(LOCK.read_text())


def checksum_entry(text, filename):
    matches = re.findall(r"^SHA256 \(([^\r\n]+)\) = ([0-9a-f]{64})$", text, re.M)
    values = [value for name, value in matches if name == filename]
    if len(values) != 1:
        raise ValueError("The signed checksum must contain exactly one matching image.")
    return values[0]


def download(url, target):
    target = Path(target)
    partial = target.with_suffix(target.suffix + ".partial")
    try:
        run(["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
             "--tlsv1.2", "--retry", "3", "--output", partial, url])
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def fetch(args):
    lock = source_lock()
    image = lock["images"][args.kind]
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    # Keep the signed release evidence even when the cached ISO already exists.
    with tempfile.TemporaryDirectory(prefix="balboa-gpg-") as temp:
        key = cache / "Rocky-10-key.asc"
        sums = cache / (image["filename"] + ".CHECKSUM")
        signature = cache / (sums.name + ".asc")
        download(lock["key_url"], key)
        download(f'{lock["base_url"]}/{sums.name}', sums)
        download(f'{lock["base_url"]}/{signature.name}', signature)
        gpg = ["gpg", "--homedir", temp, "--batch", "--no-auto-key-retrieve"]
        keys = run(gpg + ["--with-colons", "--show-keys", key], capture_output=True, text=True)
        fingerprints = [line.split(":")[9] for line in keys.stdout.splitlines() if line.startswith("fpr:")]
        primary_keys = [line for line in keys.stdout.splitlines() if line.startswith("pub:")]
        if len(primary_keys) != 1 or not fingerprints or fingerprints[0] != lock["key_fingerprint"]:
            raise ValueError("The Rocky signing key fingerprint does not match the source lock.")
        run(gpg + ["--import", key], capture_output=True)
        run(gpg + ["--verify", signature, sums])
        expected = checksum_entry(sums.read_text(), image["filename"])
        if expected != image["sha256"]:
            raise ValueError("The signed checksum does not match the source lock.")
    iso = cache / image["filename"]
    if not iso.exists():
        download(f'{lock["base_url"]}/{image["filename"]}', iso)
    if sha256(iso) != image["sha256"]:
        raise ValueError("The ISO digest does not match the source lock. Remove the damaged file.")
    print(iso)


def tools_build(args):
    run(["podman", "build", "--build-arg", f'BASE={source_lock()["container"]}',
         "-f", ROOT / "containers/Containerfile", "-t", TOOLS, ROOT])


def container(argv, mounts=(), network="none", capture_output=False):
    command = ["podman", "run", "--rm", "--network", network, "--cap-drop=all",
               "--security-opt=no-new-privileges", "--userns=keep-id", "--user", str(os.getuid())]
    for host, guest, mode in mounts:
        command += ["-v", f"{Path(host).resolve()}:{guest}:{mode}"]
    return run(command + [TOOLS] + list(argv), capture_output=capture_output, text=True)


def validate(args):
    ks = args.kickstart.resolve()
    command = ["python3", "/workspace/tests/container_checks.py", "/input/" + ks.name]
    if getattr(args, "packages", False):
        command += ["--packages"]
    container(command, [(ROOT, "/workspace", "ro"), (ks.parent, "/input", "ro")],
              network="slirp4netns" if getattr(args, "packages", False) else "none")


def iso(args):
    lock = source_lock()
    image = lock["images"][args.kind]
    source = args.cache.resolve() / image["filename"]
    if sha256(source) != image["sha256"]:
        raise ValueError("The source ISO digest does not match the source lock.")
    ks = args.kickstart.resolve()
    metadata = json.loads(ks.with_suffix(".json").read_text())
    if sha256(ks) != metadata["kickstart_sha256"] or metadata["source_kind"] != args.kind:
        raise ValueError("The Kickstart manifest does not match the image request.")
    output = args.output.resolve()
    if output.exists():
        raise ValueError("The output ISO exists. Select a new path.")
    output.parent.mkdir(parents=True, exist_ok=True)
    validate(argparse.Namespace(kickstart=ks, packages=args.kind == "boot"))
    cmdline = "console=tty0 console=ttyS0,115200n8" if metadata["lab"] else ""
    try:
        if args.native:
            run(["mkksiso", "--ks", ks, "--cmdline", cmdline, source, output])
        else:
            container(["mkksiso", "--skip-mkefiboot", "--ks", "/input/" + ks.name,
                       "--cmdline", cmdline, "/source/" + source.name, "/output/" + output.name],
                      [(source.parent, "/source", "ro"), (ks.parent, "/input", "ro"),
                       (output.parent, "/output", "rw")])
        container(["python3", "/workspace/tests/iso_checks.py", "/media/" + output.name, "/input/" + ks.name],
                  [(ROOT, "/workspace", "ro"), (output.parent, "/media", "ro"), (ks.parent, "/input", "ro")])
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    metadata.update({"iso_sha256": sha256(output), "source_sha256": image["sha256"],
                     "usb_uefi": args.native, "tools_base": lock["container"],
                     "source_lock_sha256": sha256(LOCK)})
    metadata["tools_image_id"] = run(["podman", "image", "inspect", TOOLS, "--format", "{{.Id}}"],
                                      capture_output=True, text=True).stdout.strip()
    tool_packages = container(["rpm", "-qa"], capture_output=True).stdout
    output.with_suffix(".packages.txt").write_text(tool_packages)
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(output)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    get = commands.add_parser("fetch", help="Download and authenticate an official ISO.")
    get.add_argument("--kind", choices=("boot", "dvd"), default="boot")
    get.add_argument("--cache", type=Path, default=ROOT / "cache")
    get.set_defaults(func=fetch)
    build = commands.add_parser("tools", help="Build the Rocky Linux tool container.")
    build.set_defaults(func=tools_build)
    generate = commands.add_parser("render", help="Create a Kickstart for one flavor.")
    generate.add_argument("--flavor", choices=("server", "workstation", "laptop"), required=True)
    generate.add_argument("--kind", choices=("boot", "dvd"), default="boot")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--disk", help="The only disk that the installer can erase.")
    auth = generate.add_mutually_exclusive_group(required=True)
    auth.add_argument("--site", type=Path)
    auth.add_argument("--lab", action="store_true", help="Generate disposable VM credentials for vda.")
    generate.set_defaults(func=render)
    syntax = commands.add_parser("validate", help="Do syntax and security-content tests in Podman.")
    syntax.add_argument("kickstart", type=Path)
    syntax.add_argument("--packages", action="store_true", help="Also query official package repositories.")
    syntax.set_defaults(func=validate)
    media = commands.add_parser("iso", help="Embed a Kickstart into official media.")
    media.add_argument("kickstart", type=Path)
    media.add_argument("--kind", choices=("boot", "dvd"), default="boot")
    media.add_argument("--cache", type=Path, default=ROOT / "cache")
    media.add_argument("--output", type=Path, required=True)
    media.add_argument("--native", action="store_true", help="Use host mkksiso, including the UEFI USB image.")
    media.set_defaults(func=iso)
    machine = commands.add_parser("vm", help="Install or boot a VM with isolated storage.")
    machine.add_argument("--iso", type=Path, required=True)
    machine.add_argument("--workdir", type=Path, required=True)
    machine.add_argument("--phase", choices=("install", "boot"), required=True)
    machine.add_argument("--firmware", choices=("bios", "uefi"), default="bios")
    machine.add_argument("--accel", choices=("kvm", "tcg"), default="kvm")
    machine.add_argument("--timeout", type=int, default=7200)
    machine.add_argument("--lab-secrets", type=Path, help="Unlock the disposable VM through its serial console.")
    machine.add_argument("--ovmf-code", type=Path, default=Path("/usr/share/OVMF/OVMF_CODE_4M.fd"))
    machine.add_argument("--ovmf-vars", type=Path, default=Path("/usr/share/OVMF/OVMF_VARS_4M.fd"))
    machine.set_defaults(func=vm)
    return result


def main():
    os.umask(0o077)
    args = parser().parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, subprocess.CalledProcessError, TimeoutError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
