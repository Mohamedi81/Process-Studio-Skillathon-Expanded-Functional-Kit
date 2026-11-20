#!/usr/bin/env python3
"""Render the whole Expanded Functional Kit in ONE call.

Validates the spec once, writes the six deliverables next to --output and also
packs them into the --output zip bundle. Use this when only one script run is allowed.

Usage: python3 build_kit.py --input kit-spec.json --output functional-kit.zip
Exit 0: all six files and the zip written. Exit 1: every spec problem on stderr.
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

DELIVERABLES = [
    ("data-dictionary.xlsx", build_data_dictionary),
    ("wireframes.html", build_wireframes),
    ("figma-wireframes.svg", build_figma_svg),
    ("process.bpmn", build_bpmn),
    ("integration-mapping.xlsx", build_integration_mapping),
    ("reporting-requirements.html", build_reporting),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    spec, err = kc.load_spec(args.input)
    if err:
        print("FAIL: " + err, file=sys.stderr)
        return 1
    errors = kc.validate_spec(spec)
    if errors:
        print("FAIL: %d issue(s) in the kit spec" % len(errors), file=sys.stderr)
        for e in errors:
            print(" - " + e, file=sys.stderr)
        return 1

    out_zip = Path(args.output)
    folder = out_zip.parent
    written = []
    for name, module in DELIVERABLES:
        target = folder / name
        try:
            module.build(spec, target)
        except Exception as exc:  # report which deliverable failed and why
            print("FAIL: %s could not be built: %s: %s" % (name, type(exc).__name__, exc), file=sys.stderr)
            return 1
        written.append(target)

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for target in written:
            z.write(target, target.name)
    print("PASS: wrote %s and %s" % (", ".join(t.name for t in written), out_zip.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
