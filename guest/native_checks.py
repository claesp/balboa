#!/usr/bin/python3
"""Assess the Rocky trust anchor and minimal package boundaries."""

import json
from pathlib import Path
import subprocess
import sys
import re


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


def main():
    policy = json.loads(Path("/etc/balboa/native-policy.json").read_text())
    key = Path("/etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-10")
    file_keys = fingerprints(key.read_text())
    validate_fingerprints(file_keys, policy)
    text = subprocess.run(["rpm", "-q", "--qf", "%{DESCRIPTION}\n", "gpg-pubkey"],
                          check=True, capture_output=True, text=True).stdout
    rpm_keys = fingerprints(text)
    validate_fingerprints(rpm_keys, policy)
    names = set(subprocess.run(["rpm", "-qa", "--qf", "%{NAME}\n"], check=True,
                               capture_output=True, text=True).stdout.splitlines())
    forbidden = names.intersection(policy["excluded_packages"])
    if forbidden:
        raise ValueError("The system contains excluded packages: " + ", ".join(sorted(forbidden)))
    print(json.dumps({"passed": True, "rocky_key_fingerprint": policy["key_fingerprint"],
                      "observed_file_fingerprints": sorted(file_keys), "observed_rpm_fingerprints": sorted(rpm_keys),
                      "excluded_packages_absent": True}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        sys.exit(1)
