"""Set the static hostname in the installed system."""

from pathlib import Path
import re
import secrets
import string
import subprocess
import sys


SERIAL_FIELDS = ("system-serial-number", "chassis-serial-number")
PLACEHOLDERS = {
    "default", "default-string", "n-a", "na", "no-asset-information", "none", "not-applicable",
    "not-available", "not-defined", "not-present", "not-specified", "serial-number", "system-serial-number",
    "to-be-filled-by-o-e-m", "to-be-filled-by-oem", "unknown", "unspecified",
}


def machine_hostname(flavor):
    prefix = "srv-" if flavor == "server" else "pc-"
    for field in SERIAL_FIELDS:
        result = subprocess.run(["dmidecode", "--string", field], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, encoding="ascii", errors="replace", check=False)
        lines = result.stdout.strip().splitlines()
        if result.returncode or len(lines) != 1:
            continue
        serial = re.sub(r"[^a-z0-9]+", "-", lines[0].lower()).strip("-")
        if serial and serial not in PLACEHOLDERS and not re.fullmatch(r"0+", serial):
            return prefix + serial[:63 - len(prefix)].rstrip("-")
    return prefix + "".join(secrets.choice(string.ascii_lowercase) for _ in range(9))


if __name__ == "__main__":
    hostname = Path("/etc/hostname")
    hostname.write_text(machine_hostname(sys.argv[1]) + "\n", encoding="ascii")
    hostname.chmod(0o644)
