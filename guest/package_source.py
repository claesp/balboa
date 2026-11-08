#!/usr/bin/python3
"""Keep initial hardening on the installed DVD packages."""

import argparse
import configparser
import json
from pathlib import Path

GUARD = "/etc/balboa/initial-repos.d"
STATE = Path("/var/lib/balboa/package-source-state.json")
CONFIGURATION = Path("/etc/dnf/dnf.conf")


def guard(enable):
    configuration = configparser.ConfigParser(interpolation=None)
    configuration.read(CONFIGURATION)
    if not configuration.has_section("main"):
        configuration.add_section("main")
    if enable:
        if not STATE.exists():
            STATE.write_text(json.dumps({"reposdir": configuration["main"].get("reposdir")}) + "\n")
            STATE.chmod(0o600)
        Path(GUARD).mkdir(parents=True, exist_ok=True, mode=0o755)
        if list(Path(GUARD).iterdir()):
            raise ValueError("The initial repository directory must remain empty.")
        configuration["main"]["reposdir"] = GUARD
    else:
        previous = json.loads(STATE.read_text())["reposdir"]
        if previous is None:
            configuration["main"].pop("reposdir", None)
        else:
            configuration["main"]["reposdir"] = previous
    with CONFIGURATION.open("w") as output:
        configuration.write(output)
    CONFIGURATION.chmod(0o644)
    if not enable:
        STATE.unlink()


def validate_installed(packages, record):
    if not packages:
        raise ValueError("The installed package inventory is empty.")
    permitted = set(record["packages"])
    unexpected = sorted(package for package in packages
                        if not package.startswith("gpg-pubkey|") and package not in permitted)
    if unexpected:
        raise ValueError("Packages outside the locked DVD require review: " + ", ".join(unexpected))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("guard", "release"))
    guard(parser.parse_args().action == "guard")
