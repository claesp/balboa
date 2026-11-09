#!/usr/bin/python3
"""Assess the Rocky trust anchor and minimal package boundaries."""

import json
from pathlib import Path
import subprocess
import sys
import re
import argparse
import grp
import stat


def fingerprints(data):
    result = subprocess.run(["sq", "inspect"], input=data, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Cannot read the signing key: {result.stderr.strip()}")
    return {value.replace(" ", "").upper() for value in re.findall(r"Fingerprint:\s*([A-Fa-f0-9 ]+)", result.stdout)}


def validate_fingerprints(observed, policy):
    if policy["key_fingerprint"] not in observed:
        raise ValueError("The required Rocky signing key is absent.")
    if observed - set(policy["key_fingerprints"]):
        raise ValueError("The system contains a signing key outside the source lock.")


def validate_key_access(metadata, expected_gid):
    if metadata.st_uid != 0 or metadata.st_gid != expected_gid or stat.S_IMODE(metadata.st_mode) != 0o640:
        raise ValueError("The journal private key requires root ownership, group balboa-logs, and mode 0640.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-keys", action="store_true")
    parser.add_argument("--dvd-only", action="store_true")
    args = parser.parse_args()
    policy = json.loads(Path("/etc/balboa/native-policy.json").read_text())
    dvd_policy = {**policy, "key_fingerprints": policy.get("dvd_key_fingerprints", policy["key_fingerprints"])}
    key = Path("/etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-10")
    file_keys = fingerprints(key.read_text())
    validate_fingerprints(file_keys, dvd_policy)
    if args.install_keys:
        subprocess.run(["rpm", "--import", str(key)], check=True, capture_output=True, text=True)
    text = subprocess.run(["rpm", "-q", "--qf", "%{DESCRIPTION}\n", "gpg-pubkey"],
                          check=True, capture_output=True, text=True).stdout
    rpm_keys = fingerprints(text)
    validate_fingerprints(rpm_keys, dvd_policy if args.dvd_only else policy)
    names = set(subprocess.run(["rpm", "-qa", "--qf", "%{NAME}\n"], check=True,
                               capture_output=True, text=True).stdout.splitlines())
    forbidden = names.intersection(policy["excluded_packages"])
    if forbidden:
        raise ValueError("The system contains excluded packages: " + ", ".join(sorted(forbidden)))
    if policy.get("journal_client_key"):
        validate_key_access(Path(policy["journal_client_key"]).stat(), grp.getgrnam("balboa-logs").gr_gid)
    if args.dvd_only:
        from package_source import validate_installed
        inventory = json.loads(Path('/etc/balboa/dvd-packages.json').read_text())
        if inventory['dvd_sha256'] != policy['dvd_sha256']:
            raise ValueError('The installed DVD inventory does not match the source policy.')
        installed = subprocess.run(['rpm', '-qa', '--qf', '%{NAME}|%{EPOCHNUM}|%{VERSION}|%{RELEASE}|%{ARCH}\n'],
                                   check=True, capture_output=True, text=True).stdout.splitlines()
        validate_installed(installed, inventory)
    print(json.dumps({"passed": True, "rocky_key_fingerprint": policy["key_fingerprint"],
                      "observed_file_fingerprints": sorted(file_keys), "observed_rpm_fingerprints": sorted(rpm_keys),
                      "excluded_packages_absent": True,
                      "dvd_package_versions": "passed" if args.dvd_only else "not assessed after initial hardening",
                      "journal_private_key_permissions": "passed" if policy.get("journal_client_key") else "not configured"}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        sys.exit(1)
