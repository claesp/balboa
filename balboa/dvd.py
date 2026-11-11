"""Read the package inventory of the locked Rocky installation DVD."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data/dvd-packages.json"


def dvd_device():
    label = json.loads((ROOT / "sources.lock.json").read_text())["images"]["dvd"]["volume_label"]
    return f"/dev/disk/by-label/{label}"


def catalog():
    record = json.loads(CATALOG.read_text())
    locked = json.loads((ROOT / "sources.lock.json").read_text())["images"]["dvd"]
    if record["dvd_sha256"] != locked["sha256"] or record["dvd_filename"] != locked["filename"]:
        raise ValueError("The DVD inventory differs from the source lock. Review and regenerate the inventory.")
    return record


def source_policy(flavor=None):
    later_updates = "official-rocky-and-epel-repositories" if flavor == "laptop" else "official-rocky-repositories"
    return {"installation": "locked-dvd-only", "initial_hardening": "installed-dvd-packages-only",
            "later_updates": later_updates, "dvd_sha256": catalog()["dvd_sha256"],
            "catalog_sha256": hashlib.sha256(CATALOG.read_bytes()).hexdigest()}


def extract_metadata(source, destination):
    for repository in ("BaseOS", "AppStream"):
        target = destination / repository / "repodata"
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["xorriso", "-osirrox", "on", "-indev", str(source), "-extract",
                        f"/{repository}/repodata", str(target)], check=True, capture_output=True)


def inventory(directory):
    namespace = {"r": "http://linux.duke.edu/metadata/repo", "p": "http://linux.duke.edu/metadata/common"}
    packages = set()
    for repository in ("BaseOS", "AppStream"):
        base = directory / repository
        metadata = ET.parse(base / "repodata/repomd.xml").getroot()
        primary = metadata.find("r:data[@type='primary']", namespace)
        relative = Path(primary.find("r:location", namespace).get("href"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("The DVD primary metadata path is not permitted.")
        path = base / relative
        checksum = primary.find("r:checksum", namespace)
        if checksum.get("type") != "sha256" or hashlib.sha256(path.read_bytes()).hexdigest() != checksum.text:
            raise ValueError("The DVD primary metadata digest does not match its repository record.")
        if path.suffix != ".gz":
            raise ValueError("Review the new DVD metadata compression before use.")
        with gzip.open(path, "rb") as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                if element.tag != "{http://linux.duke.edu/metadata/common}package":
                    continue
                version = element.find("p:version", namespace)
                packages.add("|".join((element.findtext("p:name", namespaces=namespace), version.get("epoch", "0"),
                                       version.get("ver"), version.get("rel"),
                                       element.findtext("p:arch", namespaces=namespace))))
                element.clear()
    return sorted(packages)
