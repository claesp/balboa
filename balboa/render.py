"""Render constrained site data and common Kickstart fragments."""

import base64
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def valid_site(site):
    patterns = {
        "hostname": r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?",
        "username": r"[a-z_][a-z0-9_-]{0,30}",
        "password_hash": r"\$6\$(?:rounds=[0-9]+\$)?[A-Za-z0-9./]{1,16}\$[A-Za-z0-9./]{86}",
        "bootloader_password_hash": r"grub\.pbkdf2\.sha512\.[0-9]{5,7}\.[0-9A-F]{128}\.[0-9A-F]{128}",
        "ssh_public_key": r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [A-Za-z0-9@._ -]+)?",
        "timezone": r"[A-Za-z_+-]+(?:/[A-Za-z_+-]+){0,2}",
        "keyboard": r"[A-Za-z0-9_-]+",
        "language": r"[a-z]{2}_[A-Z]{2}\.UTF-8",
    }
    if set(site) != set(patterns):
        raise ValueError("The site file must contain exactly the fields in examples/site.json.")
    for key, pattern in patterns.items():
        if not isinstance(site[key], str) or not re.fullmatch(pattern, site[key]):
            raise ValueError(f"The site field {key} is not permitted.")
    if site["username"] in {"root", "nobody"}:
        raise ValueError("The administrator must have a separate account.")
    if not 10000 <= int(site["bootloader_password_hash"].split(".")[3]) <= 1000000:
        raise ValueError("The GRUB digest requires 10000 to 1000000 iterations.")
    blob = base64.b64decode(site["ssh_public_key"].split()[1], validate=True)
    if len(blob) != 51 or blob[:19] != b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20":
        raise ValueError("The SSH key must contain a valid Ed25519 public key.")
    if not (Path("/usr/share/zoneinfo") / site["timezone"]).is_file():
        raise ValueError("The timezone does not exist on the build host.")
    return site


def file_fragment(path, content, executable=False):
    encoded = base64.b64encode(content.encode()).decode()
    mode = "0755" if executable else "0600"
    # Paths are repository constants. Site data never enters a shell command.
    return f"install -d {Path(path).parent}\nprintf '%s' '{encoded}' | base64 -d > {path}\nchmod {mode} {path}\n"


def render_text(flavor, site, disk, kind, lab=False, passphrase=None):
    valid_site(site)
    if not re.fullmatch(r"(?:sd[a-z]+|vd[a-z]+|nvme[0-9]+n[0-9]+|disk/by-id/[A-Za-z0-9_.:+-]+)", disk or ""):
        raise ValueError("Set an explicit whole disk name or disk/by-id identifier.")
    if lab and disk != "vda":
        raise ValueError("A lab installation can erase only vda.")
    if lab and not re.fullmatch(r"[A-Za-z0-9_-]{32,}", passphrase or ""):
        raise ValueError("A lab installation requires a generated encryption secret.")
    definition = json.loads((ROOT / "flavors" / f"{flavor}.json").read_text())
    files = ""
    for name in ("baseline.sh", "harden.sh", "audit.sh", "failure.sh", "export.sh", "result_gate.py"):
        files += file_fragment("/usr/local/libexec/balboa/" + name, (ROOT / "guest" / name).read_text(), True)
    for name in ("balboa-harden.service", "balboa-audit.service"):
        files += file_fragment("/etc/systemd/system/" + name, (ROOT / "guest" / name).read_text())
    conf = (f"FLAVOR={flavor}\nPROFILE={definition['profile']}\nADMIN_USER={site['username']}\n"
            f"DESKTOP={'yes' if definition['desktop'] else 'no'}\nLAB={'yes' if lab else 'no'}\n")
    files += file_fragment("/etc/balboa/image.conf", conf)
    source = ('url --url="https://dl.rockylinux.org/pub/rocky/10/BaseOS/x86_64/os/"\n'
              'repo --name=AppStream --baseurl="https://dl.rockylinux.org/pub/rocky/10/AppStream/x86_64/os/"')
    if kind == "dvd":
        source = "cdrom"
    values = {key.upper(): value for key, value in site.items()}
    values.update({"MODE": "cmdline" if lab else "text", "SOURCE": source, "DISK": disk,
                   "CONSOLE": "console=tty0 console=ttyS0,115200n8" if lab else "",
                   "PASSPHRASE": f' --passphrase="{passphrase}"' if lab else "",
                   "DISPLAY": "xconfig --startxonboot" if definition["desktop"] else "skipx",
                   "PACKAGES": "\n".join(definition["packages"]), "FILES": files})
    text = (ROOT / "kickstarts/base.ks.in").read_text()
    text = re.sub(r"@@([A-Z_]+)@@", lambda match: values[match[1]], text)
    if "@@" in text:
        raise ValueError("The Kickstart contains an unresolved field.")
    return text, definition


def render(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if list(output.iterdir()):
        raise ValueError("The output directory must be empty.")
    output.chmod(0o700)
    passphrase = None
    if args.lab:
        password = secrets.token_urlsafe(32)
        passphrase = secrets.token_urlsafe(32)
        boot_password = secrets.token_urlsafe(32)
        boot_salt = secrets.token_bytes(64)
        boot_digest = hashlib.pbkdf2_hmac("sha512", boot_password.encode(), boot_salt, 100000)
        boot_hash = f"grub.pbkdf2.sha512.100000.{boot_salt.hex().upper()}.{boot_digest.hex().upper()}"
        hashed = subprocess.run(["openssl", "passwd", "-6", "-stdin"], input=password + "\n",
                                capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(output / "id_ed25519")], check=True)
        site = {"hostname": f"{args.flavor}.lab.test", "username": "operator", "password_hash": hashed,
                "bootloader_password_hash": boot_hash,
                "ssh_public_key": (output / "id_ed25519.pub").read_text().strip(),
                "timezone": "UTC", "keyboard": "us", "language": "en_US.UTF-8"}
        (output / "lab-secrets.json").write_text(json.dumps({"password": password, "passphrase": passphrase,
                                                            "boot_password": boot_password}) + "\n")
        disk = args.disk or "vda"
    else:
        site = json.loads(args.site.read_text())
        disk = args.disk
    text, definition = render_text(args.flavor, site, disk, args.kind, args.lab, passphrase)
    path = output / "installation.ks"
    path.write_text(text)
    metadata = {"flavor": args.flavor, "profile": definition["profile"], "lab": args.lab,
                "disk": disk, "source_kind": args.kind,
                "kickstart_sha256": hashlib.sha256(text.encode()).hexdigest()}
    path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(path)
