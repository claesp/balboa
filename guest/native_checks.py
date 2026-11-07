#!/usr/bin/python3
"""Assess the Rocky trust anchor and minimal package boundaries."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def fingerprints(path, home):
    text = subprocess.run(["gpg", "--homedir", home, "--batch", "--with-colons", "--show-keys", str(path)],
                          check=True, capture_output=True, text=True).stdout
    return {line.split(":")[9] for line in text.splitlines() if line.startswith("fpr:")}


def main():
    policy = json.loads(Path("/etc/balboa/native-policy.json").read_text())
    with tempfile.TemporaryDirectory() as home:
        key = Path("/etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-10")
        if fingerprints(key, home) != {policy["key_fingerprint"]}:
            raise ValueError("The installed Rocky signing key does not match the source lock.")
        imported = Path(home) / "rpm-keys.asc"
        text = subprocess.run(["rpm", "-q", "--qf", "%{DESCRIPTION}\n", "gpg-pubkey"],
                              check=True, capture_output=True, text=True).stdout
        imported.write_text(text)
        if policy["key_fingerprint"] not in fingerprints(imported, home):
            raise ValueError("The Rocky signing key is absent from the RPM database.")
    names = set(subprocess.run(["rpm", "-qa", "--qf", "%{NAME}\n"], check=True,
                               capture_output=True, text=True).stdout.splitlines())
    forbidden = names.intersection(policy["excluded_packages"])
    if forbidden:
        raise ValueError("The system contains excluded packages: " + ", ".join(sorted(forbidden)))
    print(json.dumps({"passed": True, "rocky_key_fingerprint": policy["key_fingerprint"],
                      "excluded_packages_absent": True}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        sys.exit(1)
