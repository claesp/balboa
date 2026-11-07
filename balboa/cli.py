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

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "sources.lock.json"


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
        if not fingerprints or fingerprints[0] != lock["key_fingerprint"]:
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


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    get = commands.add_parser("fetch", help="Download and authenticate an official ISO.")
    get.add_argument("--kind", choices=("boot", "dvd"), default="boot")
    get.add_argument("--cache", type=Path, default=ROOT / "cache")
    get.set_defaults(func=fetch)
    return result


def main():
    os.umask(0o077)
    args = parser().parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
