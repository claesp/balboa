"""Calculate fixed LVM sizes for production and smaller test disks."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def layout(disk_gb=None, lab=False):
    policy = json.loads((ROOT / "storage/layout.json").read_text())
    if disk_gb is None:
        disk_gb = policy["test_disk_gb"] if lab else policy["production_disk_gb"]
    if type(disk_gb) is not int or not policy["minimum_disk_gb"] <= disk_gb <= 16384:
        raise ValueError("The disk size must be an integer from 24 to 16384 GB.")
    disk_bytes = disk_gb * 1_000_000_000
    # Leave space for either firmware scheme, encryption metadata, and LVM metadata.
    pv_mib = disk_bytes // 1048576 - policy["boot_reserve_mib"]
    budget = pv_mib - policy["lvm_reserve_mib"]
    volumes = policy["volumes"]
    spare = budget - sum(v["minimum_mib"] for v in volumes)
    if spare < 0:
        raise ValueError("The disk cannot contain the required filesystem minimum sizes.")
    result = []
    for volume in volumes:
        result.append({**volume, "size_mib": volume["minimum_mib"] + spare * volume["weight"] // 100})
    result[0]["size_mib"] += budget - sum(v["size_mib"] for v in result)
    return {"disk_gb": disk_gb, "disk_bytes": disk_bytes, "pv_mib": pv_mib,
            "lvm_reserve_mib": policy["lvm_reserve_mib"], "volumes": result}


def kickstart_volumes(plan):
    lines = []
    for volume in plan["volumes"]:
        fstype = "swap" if volume["mount"] == "swap" else "xfs"
        line = (f'logvol {volume["mount"]} --vgname=system --name={volume["name"]} '
                f'--fstype={fstype} --size={volume["size_mib"]}')
        if volume["options"]:
            line += f' --fsoptions="{volume["options"]}"'
        lines.append(line)
    return "\n".join(lines)
