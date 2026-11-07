"""Do tests that require Rocky Linux tooling."""

from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def main():
    subprocess.run(["ksvalidator", "-v", "RHEL10", sys.argv[1]], check=True)
    for script in Path("/workspace/guest").glob("*.sh"):
        subprocess.run(["bash", "-n", str(script)], check=True)
    ds = Path("/usr/share/xml/scap/ssg/content/ssg-rl10-ds.xml")
    root = ET.parse(ds).getroot()
    ns = {"x": "http://checklists.nist.gov/xccdf/1.2"}
    for suffix, title in (("cis", "Level 2 - Server"), ("cis_workstation_l2", "Level 2 - Workstation")):
        profile = root.find(f".//x:Profile[@id='xccdf_org.ssgproject.content_profile_{suffix}']", ns)
        if profile is None or title not in profile.findtext("x:title", namespaces=ns):
            raise ValueError(f"The Rocky datastream does not contain {title}.")
    print("Kickstart syntax, shell syntax, and Rocky CIS Level 2 profile tests passed.")


if __name__ == "__main__":
    main()
