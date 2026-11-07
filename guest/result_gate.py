#!/usr/bin/python3
"""Reject incomplete or noncompliant XCCDF assessment results."""

import argparse
from collections import Counter
import json
import sys
import xml.etree.ElementTree as ET

NS = {"x": "http://checklists.nist.gov/xccdf/1.2"}


def assess(path, profile, minimum=100):
    root = ET.parse(path).getroot()
    results = list(root.iter(f'{{{NS["x"]}}}TestResult'))
    if len(results) != 1:
        raise ValueError("The report must contain exactly one assessment.")
    result = results[0]
    selected = result.find("x:profile", NS)
    if selected is None or selected.get("idref") != profile:
        raise ValueError("The report profile does not match the requested profile.")
    rules = result.findall("x:rule-result", NS)
    identifiers = [r.get("idref") for r in rules]
    if None in identifiers or len(set(identifiers)) != len(identifiers):
        raise ValueError("The report contains missing or duplicate rule identifiers.")
    counts = Counter(r.findtext("x:result", default="missing", namespaces=NS) for r in rules)
    allowed = {"pass", "fail", "error", "unknown", "notchecked", "notapplicable", "notselected", "informational", "fixed"}
    if set(counts) - allowed:
        raise ValueError("The report contains an unknown result value.")
    applicable = sum(counts[k] for k in ("pass", "fail", "error", "unknown", "notchecked", "fixed"))
    if applicable < minimum or counts["pass"] == 0:
        raise ValueError("The report does not contain enough applicable rules.")
    findings = [r.get("idref") for r in rules if r.findtext("x:result", namespaces=NS) in {"fail", "error", "unknown", "notchecked", "fixed"}]
    return {"profile": profile, "counts": dict(counts), "applicable": applicable,
            "passed": not findings, "findings": findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--allow-findings", action="store_true")
    args = parser.parse_args()
    try:
        summary = assess(args.results, args.profile)
        print(json.dumps(summary, indent=2))
        if summary["counts"].get("error", 0):
            return 1
        return 0 if summary["passed"] or args.allow_findings else 1
    except (OSError, ValueError, ET.ParseError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
