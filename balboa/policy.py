"""Adapt vendor-specific SCAP content without suppressing unrelated findings."""

import xml.etree.ElementTree as ET

NS = "http://checklists.nist.gov/xccdf/1.2"
EXCLUSIONS = {
    "ensure_redhat_gpgkey_installed": "Replaced by the pinned Rocky Linux signing-key test.",
    "package_postfix_installed": "The requested minimal flavors exclude a local mail agent.",
}


def tailoring(flavor, base_profile):
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}Tailoring", id="xccdf_org.balboa_tailoring_rocky10")
    ET.SubElement(root, f"{{{NS}}}benchmark", href="/usr/share/xml/scap/ssg/content/ssg-rl10-ds.xml")
    ET.SubElement(root, f"{{{NS}}}version", time="2026-11-07T00:00:00Z").text = "1"
    profile_id = f"xccdf_org.balboa_profile_cis_{flavor}_rocky10"
    profile = ET.SubElement(root, f"{{{NS}}}Profile", id=profile_id, extends=base_profile)
    ET.SubElement(profile, f"{{{NS}}}title").text = f"Balboa Rocky Linux 10 CIS Level 2 based {flavor}"
    for rule in EXCLUSIONS:
        ET.SubElement(profile, f"{{{NS}}}select", idref="xccdf_org.ssgproject.content_rule_" + rule, selected="false")
    return profile_id, ET.tostring(root, encoding="unicode") + "\n"
