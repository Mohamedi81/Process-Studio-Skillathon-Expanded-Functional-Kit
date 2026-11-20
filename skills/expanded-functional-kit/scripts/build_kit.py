#!/usr/bin/env python3
"""Render the whole Expanded Functional Kit in ONE call, best effort.

The runtime may allow a single script run per request and may hide stderr when a
script exits non-zero. So this script never fails on spec problems. It:
  1. writes every deliverable it can build, even from a spec with cross-reference issues;
  2. writes validation-report.md listing every spec issue and the status of each deliverable;
  3. prints the same report on stdout and packs everything into the --output zip.
It exits 1 only when it cannot write its own output.

Usage: python3 build_kit.py --input kit-spec.json --output functional-kit.zip
"""
import argparse
import sys
import zipfile
from pathlib import Path

import kit_common as kc
import build_data_dictionary
import build_wireframes
import build_figma_svg
import build_bpmn
import build_integration_mapping
import build_reporting

DEFAULT_OUTPUT_NAME = "functional-kit.zip"
REPORT_NAME = "validation-report.md"

DELIVERABLES = [
    ("data-dictionary.xlsx", build_data_dictionary),
    ("wireframes.html", build_wireframes),
    ("figma-wireframes.svg", build_figma_svg),
    ("process.bpmn", build_bpmn),
    ("integration-mapping.xlsx", build_integration_mapping),
    ("reporting-requirements.html", build_reporting),
]


def report_text(issues, status, structural):
    lines = ["# Kit build report", ""]
    if not issues:
        lines.append("Spec validation: PASS (no issues).")
    elif structural:
        lines.append("Spec validation: FAIL. The spec has wrong JSON types, so nothing could be built.")
        lines.append("Fix these in kit-spec.json and build again.")
    else:
        lines.append("Spec validation: %d issue(s). Deliverables were built where possible, but they may be" % len(issues))
        lines.append("incomplete or inconsistent until these are fixed in kit-spec.json.")
    if issues:
        lines.append("")
        lines.append("## Issues")
        lines.extend("- " + i for i in issues)
    lines += ["", "## Deliverables"]
    lines.extend("- %s: %s" % (name, state) for name, state in status)
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    out_zip = Path(args.output)
    folder = out_zip.parent
    issues, structural, spec = [], False, None

    spec, err = kc.load_spec(args.input)
    if err:
        issues, structural = [err], True
    elif not isinstance(spec, dict):
        issues, structural = ["spec must be a JSON object"], True
    else:
        issues = kc.check_shapes(spec)
        structural = bool(issues)
        if not structural:
            issues = kc.validate_spec(spec)

    status, written = [], []
    for name, module in DELIVERABLES:
        if structural:
            status.append((name, "not built (fix the structure problems first)"))
            continue
        target = folder / name
        try:
            module.build(spec, target)
            written.append(target)
            status.append((name, "built" if not issues else "built despite spec issues, check it"))
        except Exception as exc:  # keep going so the other deliverables still arrive
            status.append((name, "NOT built: %s: %s" % (type(exc).__name__, exc)))

    text = report_text(issues, status, structural)
    report = folder / REPORT_NAME
    try:
        report.write_text(text, encoding="utf-8")
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for target in written + [report]:
                z.write(target, target.name)
    except OSError as exc:
        print("FAIL: cannot write output: %s" % exc, file=sys.stderr)
        return 1
    print(text)
    print("DONE: %d of %d deliverables built; report in %s; bundle %s"
          % (len(written), len(DELIVERABLES), REPORT_NAME, out_zip.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
