"""Render constrained site data and common Kickstart fragments."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import subprocess
from urllib.parse import urlsplit

from . import branding
from .dvd import catalog, CATALOG, source_policy
from .storage import kickstart_volumes, layout
from .policy import EXCLUSIONS, tailoring

ROOT = Path(__file__).resolve().parent.parent


def validate_luks_passphrase(value):
    if not isinstance(value, str) or not 5 <= len(value) <= 128 or not value.isprintable():
        raise ValueError("The LUKS passphrase requires 5 to 128 printable characters without line breaks.")
    if value == "REPLACE_WITH_A_PLAINTEXT_LUKS_PASSPHRASE":
        raise ValueError("Replace the example LUKS passphrase with the actual passphrase, or omit the field for interactive installation.")


def read_site(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "r", encoding="utf-8") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("The site file must be a regular file.")
        site = json.load(source)
    if not isinstance(site, dict):
        raise ValueError("The site file must contain a JSON object.")
    if site.get("luks_passphrase") is not None and metadata.st_mode & 0o077:
        raise ValueError("A site file with a LUKS passphrase must deny all group and other access. Use mode 0600.")
    return valid_site(site)


def validate_keyboard(layout):
    supported = json.loads((ROOT / "data/keyboards.json").read_text())["layouts"]
    if layout not in supported:
        raise ValueError("The keyboard field requires a supported XKB layout. Use se for Swedish or us for US English. See data/keyboards.json.")


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
    required = set(patterns) | {"root_password_hash"}
    if not required <= set(site) or set(site) - required - {"journal_upload", "luks_passphrase", "branding_text", "boot_splash"}:
        raise ValueError("The site file contains missing or unknown fields.")
    for key, pattern in patterns.items():
        if not isinstance(site[key], str) or not re.fullmatch(pattern, site[key]):
            raise ValueError(f"The site field {key} is not permitted.")
    validate_keyboard(site["keyboard"])
    branding.validate_text(site.get("branding_text", "Balboa"))
    if "boot_splash" in site and type(site["boot_splash"]) is not bool:
        raise ValueError("The boot_splash field requires true or false.")
    root_hash = site["root_password_hash"]
    if not isinstance(root_hash, str) or not re.fullmatch(patterns["password_hash"], root_hash):
        raise ValueError("The root console password requires a SHA512 crypt digest.")
    if site.get("luks_passphrase") is not None:
        validate_luks_passphrase(site["luks_passphrase"])
    upload = site.get("journal_upload")
    if upload is not None:
        allowed = {"url", "trusted_certificate_file", "client_certificate_file", "client_key_file"}
        if not isinstance(upload, dict) or "url" not in upload or set(upload) - allowed:
            raise ValueError("The journal upload configuration contains missing or unknown fields.")
        url = upload["url"]
        if not isinstance(url, str) or not re.fullmatch(r"https://[A-Za-z0-9:/._\[\]-]+", url):
            raise ValueError("The journal receiver requires an HTTPS URL without credentials.")
        parsed = urlsplit(url)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("The journal receiver URL is not permitted.")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("The journal receiver port is not permitted.")
        for field, value in upload.items():
            if field == "url":
                continue
            if not isinstance(value, str) or not re.fullmatch(r"/etc/pki/[A-Za-z0-9/_.+-]+", value) or ".." in Path(value).parts:
                raise ValueError("Journal TLS files must use paths under /etc/pki/.")
        if ("client_certificate_file" in upload) != ("client_key_file" in upload):
            raise ValueError("Journal client authentication requires both certificate and key paths.")
    reserved = {"root", "bin", "daemon", "adm", "lp", "sync", "shutdown", "halt", "mail", "operator",
                "games", "ftp", "nobody", "dbus", "sshd", "chrony", "polkitd", "systemd-network",
                "systemd-resolve", "tss", "unbound", "rpc", "rpcuser", "nfsnobody", "cockpit-ws"}
    if site["username"] in reserved:
        raise ValueError("The administrator must have a separate account.")
    if not 10000 <= int(site["bootloader_password_hash"].split(".")[3]) <= 1000000:
        raise ValueError("The GRUB digest requires 10000 to 1000000 iterations.")
    blob = base64.b64decode(site["ssh_public_key"].split()[1], validate=True)
    if len(blob) != 51 or blob[:19] != b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20":
        raise ValueError("The SSH key must contain a valid Ed25519 public key.")
    if not (Path("/usr/share/zoneinfo") / site["timezone"]).is_file():
        raise ValueError("The timezone does not exist on the build host.")
    return site


def file_fragment(path, content, executable=False, mode=None):
    encoded = base64.b64encode(content.encode() if isinstance(content, str) else content).decode()
    mode = mode or ("0755" if executable else "0600")
    # Paths are repository constants. Site data never enters a shell command.
    return f"install -d {Path(path).parent}\nprintf '%s' '{encoded}' | base64 -d > {path}\nchmod {mode} {path}\n"


def render_text(flavor, site, disk, kind, lab=False, passphrase=None, disk_gb=None, lab_tls=None):
    if kind != "dvd":
        raise ValueError("Installation packages must come from the locked DVD. Use --kind dvd.")
    valid_site(site)
    if not lab:
        if passphrase is not None:
            raise ValueError("Supply the production LUKS passphrase in the site luks_passphrase field.")
        passphrase = site.get("luks_passphrase")
    if not re.fullmatch(r"(?:sd[a-z]+|vd[a-z]+|nvme[0-9]+n[0-9]+|disk/by-id/[A-Za-z0-9_.:+-]+)", disk or ""):
        raise ValueError("Set an explicit whole disk name or disk/by-id identifier.")
    if lab and disk != "vda":
        raise ValueError("A lab installation can erase only vda.")
    if lab and not re.fullmatch(r"[A-Za-z0-9_-]{32,}", passphrase or ""):
        raise ValueError("A lab installation requires a generated encryption secret.")
    if passphrase is not None:
        validate_luks_passphrase(passphrase)
    definition = json.loads((ROOT / "flavors" / f"{flavor}.json").read_text())
    splash = site.get("boot_splash", not lab)
    storage = layout(disk_gb, lab)
    files = ""
    for name in ("baseline.sh", "branding.sh", "plymouth.sh", "harden.sh", "audit.sh", "failure.sh", "export.sh", "result_gate.py", "native_checks.py", "package_source.py"):
        files += file_fragment("/usr/local/libexec/balboa/" + name, (ROOT / "guest" / name).read_text(), True)
    assets = branding.images(site.get("branding_text", "Balboa"))
    files += f"install -d -m 0755 {branding.BOOT_DIR}\n"
    files += file_fragment(branding.BOOT_DIR + "/boot.png", assets["boot.png"], mode="0644")
    files += file_fragment(branding.BOOT_DIR + "/theme.txt", branding.GRUB_THEME, mode="0644")
    files += file_fragment(branding.BOOT_DIR + "/inter.pf2", branding.grub_font(), mode="0644")
    files += "install -d -m 0755 /usr/share/licenses/balboa-inter\n"
    files += file_fragment("/usr/share/licenses/balboa-inter/OFL.txt",
                           (ROOT / "assets/fonts/OFL.txt").read_bytes(), mode="0644")
    if splash or definition["desktop"]:
        files += "install -d -m 0755 /usr/share/fonts/balboa\n"
        files += file_fragment("/usr/share/fonts/balboa/Inter-Regular.ttf", branding.FONT.read_bytes(), mode="0644")
        files += file_fragment("/etc/fonts/conf.d/55-balboa-inter.conf",
                               (ROOT / "guest/Inter.conf").read_text(), mode="0644")
    if splash:
        files += "install -d -m 0755 /usr/share/plymouth/themes/balboa\n"
        for name in ("balboa.plymouth", "balboa.script"):
            files += file_fragment("/usr/share/plymouth/themes/balboa/" + name,
                                   (ROOT / "guest/plymouth" / name).read_text(), mode="0644")
    if definition["desktop"]:
        files += "install -d -m 0755 /etc/firefox /etc/firefox/policies\n"
        files += file_fragment("/etc/firefox/policies/policies.json",
                               (ROOT / "guest/firefox-policies.json").read_text(), mode="0644")
        files += f"install -d -m 0755 {branding.DESKTOP_DIR}\n"
        for name in ("wallpaper.png", "login.png"):
            files += file_fragment(branding.DESKTOP_DIR + "/" + name, assets[name], mode="0644")
    for name in ("balboa-harden.service", "balboa-audit.service"):
        files += file_fragment("/etc/systemd/system/" + name, (ROOT / "guest" / name).read_text())
    files += "install -d -m 0755 /etc/systemd/system/NetworkManager-wait-online.service.d\n"
    files += file_fragment("/etc/systemd/system/NetworkManager-wait-online.service.d/60-balboa-timeout.conf",
                           (ROOT / "guest/network-wait.conf").read_text(), mode="0644")
    profile_id, tailoring_xml = tailoring(flavor, definition["profile"])
    files += file_fragment("/etc/balboa/tailoring.xml", tailoring_xml)
    native = {"key_fingerprint": json.loads((ROOT / "sources.lock.json").read_text())["key_fingerprint"],
              "key_fingerprints": json.loads((ROOT / "sources.lock.json").read_text())["rpm_key_fingerprints"],
              "excluded_packages": definition["exclude"], "dvd_sha256": catalog()["dvd_sha256"]}
    if site.get("journal_upload", {}).get("client_key_file"):
        native["journal_client_key"] = site["journal_upload"]["client_key_file"]
    files += file_fragment("/etc/balboa/native-policy.json", json.dumps(native))
    catalog()
    files += file_fragment("/etc/balboa/dvd-packages.json", CATALOG.read_bytes())
    if lab_tls:
        if not lab:
            raise ValueError("Disposable TLS material requires lab mode.")
        if set(lab_tls) != {"ca.pem", "client.pem", "client.key"}:
            raise ValueError("Disposable TLS material requires the expected certificate and key files.")
        files += "install -d -m 0755 /etc/pki/balboa\n"
        for name, content in lab_tls.items():
            files += file_fragment("/etc/pki/balboa/" + name, content, mode="0600" if name.endswith(".key") else "0644")
    upload = site.get("journal_upload")
    if upload:
        files += "install -d -m 0755 /etc/systemd/journal-upload.conf.d\n"
        files += file_fragment("/etc/systemd/system/systemd-journal-upload.service.d/40-balboa-network.conf",
                               (ROOT / "guest/journal-upload-network.conf").read_text(), mode="0644")
        lines = ["[Upload]", "URL=" + upload["url"]]
        names = {"trusted_certificate_file": "TrustedCertificateFile", "client_certificate_file": "ServerCertificateFile"}
        for field, name in names.items():
            if field in upload:
                lines.append(name + "=" + upload[field])
        if "trusted_certificate_file" not in upload:
            lines.append("TrustedCertificateFile=/etc/pki/tls/certs/ca-bundle.crt")
        if "client_key_file" in upload:
            lines.append("ServerKeyFile=" + upload["client_key_file"])
            files += "getent group balboa-logs >/dev/null || groupadd --system balboa-logs\n"
            files += file_fragment("/etc/systemd/system/systemd-journal-upload.service.d/60-balboa-credentials.conf",
                                   "[Service]\nSupplementaryGroups=balboa-logs\n", mode="0644")
            if lab_tls:
                files += "chgrp balboa-logs " + upload["client_key_file"] + "\nchmod 0640 " + upload["client_key_file"] + "\n"
        else:
            lines += ["ServerKeyFile=-", "ServerCertificateFile=-"]
        files += file_fragment("/etc/systemd/journal-upload.conf.d/60-balboa.conf", "\n".join(lines) + "\n", mode="0644")
    conf = (f"FLAVOR={flavor}\nBASE_PROFILE={definition['profile']}\nPROFILE={profile_id}\nADMIN_USER={site['username']}\n"
            f"BOOT_SPLASH={'yes' if splash else 'no'}\nDESKTOP={'yes' if definition['desktop'] else 'no'}\nLAB={'yes' if lab else 'no'}\n"
            f"ROOT_PASSWORD_CONFIGURED={'yes' if site.get('root_password_hash') else 'no'}\n")
    files += file_fragment("/etc/balboa/image.conf", conf)
    source = "cdrom"
    values = {key.upper(): value for key, value in site.items()}
    values.update({"MODE": "cmdline" if lab else "text", "SOURCE": source, "DISK": disk,
                   "ROOTPW": "rootpw --iscrypted " + site["root_password_hash"],
                   "CONSOLE": ("console=ttyS0,115200n8 console=tty0" if splash else
                               "console=tty0 console=ttyS0,115200n8") if lab else "",
                   "BOOT_APPEARANCE": ("rhgb quiet loglevel=3 systemd.show_status=auto rd.systemd.show_status=auto "
                                       "plymouth.ignore-serial-consoles" if splash else "plymouth.enable=0"),
                   "PASSPHRASE": (f' --passphrase="{passphrase}"' if lab else
                                  " --passphrase=" + shlex.quote(passphrase) if passphrase is not None else ""),
                   "DISPLAY": "xconfig --startxonboot" if definition["desktop"] else "skipx",
                   "PV_MIB": str(storage["pv_mib"]), "BOOT_MIB": str(storage["boot_mib"]),
                   "VOLUMES": kickstart_volumes(storage),
                   "PACKAGES": "\n".join(definition["packages"] + (["plymouth-theme-script", "plymouth-plugin-label", "plymouth-scripts", "fontconfig"] if splash else []) + ["-" + p for p in definition["exclude"]]), "FILES": files})
    template = (ROOT / "kickstarts/base.ks.in").read_text()
    field = r"@@([A-Z_]+)@@"
    if set(re.findall(field, template)) - set(values) or "@@" in re.sub(field, "", template):
        raise ValueError("The Kickstart contains an unresolved field.")
    text = re.sub(field, lambda match: values[match[1]], template)
    return text, definition


def render(args):
    if args.lab_logging_dir and not args.lab:
        raise ValueError("Disposable logging credentials require --lab.")
    site = None if args.lab else read_site(args.site)
    branding_text = args.branding_text if args.branding_text is not None else (site or {}).get("branding_text", "Balboa")
    assets = branding.images(branding_text)
    passphrase = None
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if list(output.iterdir()):
        raise ValueError("The output directory must be empty.")
    output.chmod(0o700)
    lab_tls = None
    if args.lab:
        password = secrets.token_urlsafe(32)
        root_password = secrets.token_urlsafe(32)
        passphrase = secrets.token_urlsafe(32)
        boot_password = secrets.token_urlsafe(32)
        boot_salt = secrets.token_bytes(64)
        boot_digest = hashlib.pbkdf2_hmac("sha512", boot_password.encode(), boot_salt, 100000)
        boot_hash = f"grub.pbkdf2.sha512.100000.{boot_salt.hex().upper()}.{boot_digest.hex().upper()}"
        hashed = subprocess.run(["openssl", "passwd", "-6", "-stdin"], input=password + "\n",
                                capture_output=True, text=True, check=True).stdout.strip()
        root_hashed = subprocess.run(["openssl", "passwd", "-6", "-stdin"], input=root_password + "\n",
                                     capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(output / "id_ed25519")], check=True)
        site = {"hostname": f"{args.flavor}.lab.test", "username": "balboa", "password_hash": hashed,
                "bootloader_password_hash": boot_hash,
                "root_password_hash": root_hashed,
                "ssh_public_key": (output / "id_ed25519.pub").read_text().strip(),
                "timezone": "UTC", "keyboard": "us", "language": "en_US.UTF-8"}
        (output / "lab-secrets.json").write_text(json.dumps({"password": password, "passphrase": passphrase,
                                                            "root_password": root_password,
                                                            "boot_password": boot_password}) + "\n")
        disk = args.disk or "vda"
        if args.lab_logging_dir:
            lab_tls = {name: (args.lab_logging_dir / name).read_text() for name in ("ca.pem", "client.pem", "client.key")}
            site["journal_upload"] = {"url": args.lab_logging_url,
                                      "trusted_certificate_file": "/etc/pki/balboa/ca.pem",
                                      "client_certificate_file": "/etc/pki/balboa/client.pem",
                                      "client_key_file": "/etc/pki/balboa/client.key"}
    else:
        disk = args.disk
    site = {**site, "branding_text": branding_text,
            "boot_splash": args.boot_splash if args.boot_splash is not None else (site or {}).get("boot_splash", not args.lab)}
    (output / "branding").mkdir()
    for name, data in assets.items():
        (output / "branding" / name).write_bytes(data)
    (output / "branding" / "inter.pf2").write_bytes(branding.grub_font())
    text, definition = render_text(args.flavor, site, disk, args.kind, args.lab, passphrase, args.disk_size_gb, lab_tls)
    if not args.lab:
        passphrase = site.get("luks_passphrase")
    path = output / "installation.ks"
    path.write_text(text)
    metadata = {"flavor": args.flavor, "profile": tailoring(args.flavor, definition["profile"])[0],
                "base_profile": definition["profile"], "lab": args.lab,
                "luks_passphrase_embedded": passphrase is not None,
                "luks_passphrase_source": "generated-lab" if args.lab else "site" if passphrase is not None else "interactive",
                "root_console_password_configured": bool(site.get("root_password_hash")),
                "journal_upload_configured": bool(site.get("journal_upload")),
                "branding": branding.record(branding_text),
                "boot_splash": site["boot_splash"],
                "policy_deviations": EXCLUSIONS,
                "disk": disk, "source_kind": args.kind,
                "package_source_policy": source_policy(),
                "storage": layout(args.disk_size_gb, args.lab),
                "kickstart_sha256": hashlib.sha256(text.encode()).hexdigest()}
    path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(path)
