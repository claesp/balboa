#!/usr/bin/python3
"""Configure the approved laptop package and firmware sources."""

import argparse
import configparser
import json
import os
from pathlib import Path
import subprocess
import tempfile

from libdnf.conf import ConfigParser

from native_checks import fingerprints
from package_source import CONFIGURATION, GUARD, STATE

ASSETS = Path(__file__).resolve().parent
REPOSITORIES = Path("/etc/yum.repos.d")
POLICY = Path("/etc/balboa/native-policy.json")
EPEL_KEY = Path("/etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-10")
EPEL_FINGERPRINT = "7D8D15CBFC4E62688591FB2633D98517E37ED158"
LVFS = Path("/etc/fwupd/remotes.d/lvfs.conf")
ROCKY_REPOSITORIES = {
    "rocky.repo": ("crb",),
    "rocky-addons.repo": ("rt",),
    "rocky-extras.repo": ("extras", "plus"),
    "rocky-security.repo": ("security",),
}


def replace_file(path, content, mode):
    if path.is_file() and path.read_bytes() == content:
        return
    with tempfile.TemporaryDirectory(dir=path.parent) as temporary:
        staged = Path(temporary) / path.name
        staged.write_bytes(content)
        staged.chmod(mode)
        staged.replace(path)
    subprocess.run(["restorecon", str(path)], check=True)


def enable(parser, path, *sections, option="enabled", value="1"):
    for section in sections:
        parser.setValue(section, option, value)
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / path.name
        parser.write(str(output), False)
        replace_file(path, output.read_bytes(), 0o644)


def configure(stage):
    if os.geteuid() != 0:
        raise ValueError("Operate this command as root on the laptop.")
    if "FLAVOR=laptop" not in Path("/etc/balboa/image.conf").read_text().splitlines():
        raise ValueError("This repository configuration requires the Balboa laptop flavor.")
    configuration = configparser.ConfigParser(interpolation=None)
    configuration.read(CONFIGURATION)
    guarded = configuration.get("main", "reposdir", fallback=None) == GUARD
    if stage:
        if not (guarded and STATE.is_file()):
            raise ValueError("Stage repositories only while the DVD restriction is active.")
    elif guarded or STATE.exists() or not (STATE.parent / "remediated").is_file():
        raise ValueError("Complete initial hardening before you enable the laptop repositories.")

    key = (ASSETS / EPEL_KEY.name).read_text()
    if fingerprints(key) != {EPEL_FINGERPRINT}:
        raise ValueError("The EPEL signing key does not match the approved fingerprint.")
    if EPEL_KEY.exists() and fingerprints(EPEL_KEY.read_text()) != {EPEL_FINGERPRINT}:
        raise ValueError("The existing EPEL signing key requires review.")

    rocky = {}
    for name, sections in ROCKY_REPOSITORIES.items():
        parser = ConfigParser()
        parser.read(str(REPOSITORIES / name))
        for section in sections:
            if parser.getValue(section, "gpgcheck") != "1" or parser.getValue(section, "gpgkey") != (
                "file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-10"
            ):
                raise ValueError(f"The Rocky signing configuration for {section} requires review.")
        rocky[name] = parser

    epel_file = REPOSITORIES / "epel.repo"
    epel_template = (ASSETS / epel_file.name).read_bytes()
    epel = ConfigParser()
    if epel_file.exists():
        expected = ConfigParser()
        expected.readString(epel_template.decode())
        epel.read(str(epel_file))
        for option in ("metalink", "gpgkey", "gpgcheck"):
            if epel.getValue("epel", option) != expected.getValue("epel", option):
                raise ValueError("The existing EPEL repository configuration requires review.")

    firmware = ConfigParser()
    firmware.read(str(LVFS))
    if not firmware.getValue("fwupd Remote", "MetadataURI").startswith("https://cdn.fwupd.org/downloads/"):
        raise ValueError("The stable LVFS metadata source requires review.")

    policy = json.loads(POLICY.read_text())
    policy.setdefault("dvd_key_fingerprints", policy["key_fingerprints"])
    policy["key_fingerprints"] = sorted(set(policy["key_fingerprints"]) | {EPEL_FINGERPRINT})
    replace_file(POLICY, (json.dumps(policy) + "\n").encode(), 0o600)
    if not EPEL_KEY.exists():
        replace_file(EPEL_KEY, key.encode(), 0o644)
    for name, sections in ROCKY_REPOSITORIES.items():
        enable(rocky[name], REPOSITORIES / name, *sections)
    if epel_file.exists():
        enable(epel, epel_file, "epel")
    else:
        replace_file(epel_file, epel_template, 0o644)
    enable(firmware, LVFS, "fwupd Remote", option="Enabled", value="true")
    print("The laptop package and firmware sources are ready.")


if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--stage", action="store_true", help="Prepare the repositories behind the DVD restriction.")
    try:
        configure(arguments.parse_args().stage)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        arguments.exit(1, f"Error: {error}\n")
