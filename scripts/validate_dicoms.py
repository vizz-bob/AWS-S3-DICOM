#!/usr/bin/env python3
"""
validate_dicoms.py
Validate DICOM files for required tags and image integrity.

Usage:
    python validate_dicoms.py --input-dir /path/to/dicoms --report-path report.txt
"""

import argparse
import logging
from pathlib import Path
import pydicom

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

REQUIRED_TAGS = [
    ("PatientID",         "0010,0020"),
    ("StudyInstanceUID",  "0020,000D"),
    ("SeriesInstanceUID", "0020,000E"),
    ("SOPInstanceUID",    "0008,0018"),
    ("SOPClassUID",       "0008,0016"),
    ("Modality",          "0008,0060"),
    ("Rows",              "0028,0010"),
    ("Columns",           "0028,0011"),
    ("BitsAllocated",     "0028,0100"),
    ("PixelData",         "7FE0,0010"),
]


def validate_file(dcm_path: Path) -> tuple[bool, list[str]]:
    """Return (passed, list_of_issues)."""
    issues = []
    try:
        ds = pydicom.dcmread(str(dcm_path), stop_before_pixels=False)
    except Exception as exc:
        return False, [f"Cannot read file: {exc}"]

    for tag_name, _ in REQUIRED_TAGS:
        if not hasattr(ds, tag_name):
            issues.append(f"MISSING tag: {tag_name}")

    # Pixel data sanity check
    if hasattr(ds, "PixelData") and hasattr(ds, "Rows") and hasattr(ds, "Columns"):
        expected_bytes = ds.Rows * ds.Columns * getattr(ds, "SamplesPerPixel", 1)
        actual_bytes = len(ds.PixelData)
        if actual_bytes < expected_bytes:
            issues.append(
                f"PixelData too small: expected ~{expected_bytes}, got {actual_bytes}"
            )

    return (len(issues) == 0), issues


def validate_directory(input_dir: Path, report_path: Path) -> None:
    dcm_files = sorted(
        f for f in input_dir.rglob("*")
        if f.suffix.lower() in {".dcm", ".dicom", ""}
    )

    # Also accept files without extension if they look like DICOMs
    if not dcm_files:
        dcm_files = sorted(input_dir.rglob("*.dcm"))

    log.info("Validating %d files in %s", len(dcm_files), input_dir)

    passed = failed = 0
    lines = [f"DICOM Validation Report — {input_dir}\n{'='*60}\n"]

    for fp in dcm_files:
        ok, issues = validate_file(fp)
        if ok:
            lines.append(f"PASS  {fp.name}")
            passed += 1
        else:
            for issue in issues:
                lines.append(f"ERROR {fp.name}: {issue}")
            failed += 1

    summary = f"\n{'='*60}\nSummary: {passed} passed, {failed} failed out of {len(dcm_files)} files\n"
    lines.append(summary)

    report_text = "\n".join(lines)
    report_path.write_text(report_text)
    log.info("Report written to %s", report_path)
    print(report_text)

    if failed:
        import sys
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Validate DICOM files")
    parser.add_argument("--input-dir",   required=True, help="Directory of .dcm files")
    parser.add_argument("--report-path", default="validation_report.txt")
    args = parser.parse_args()
    validate_directory(Path(args.input_dir), Path(args.report_path))


if __name__ == "__main__":
    main()
