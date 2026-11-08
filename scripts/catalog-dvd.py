#!/usr/bin/env python3
"""Regenerate the reviewed package inventory from the locked DVD."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from balboa.dvd import extract_metadata, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dvd", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/dvd-packages.json")
    args = parser.parse_args()
    locked = json.loads((ROOT / "sources.lock.json").read_text())["images"]["dvd"]
    digest = hashlib.sha256()
    with args.dvd.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != locked["sha256"]:
        raise ValueError("The DVD digest does not match the source lock.")
    with tempfile.TemporaryDirectory(prefix="balboa-dvd-catalog-") as temporary:
        directory = Path(temporary)
        extract_metadata(args.dvd, directory)
        record = {"dvd_filename": locked["filename"], "dvd_sha256": locked["sha256"],
                  "format": "name|epoch|version|release|architecture", "packages": inventory(directory)}
        args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Recorded {len(record['packages'])} DVD package identities in {args.output}.")


if __name__ == "__main__":
    main()
