#!/usr/bin/env python3
"""
generate_checksums.py
Generate MD5 checksums and a file manifest CSV for all images.

Usage:
    python generate_checksums.py --source /path/to/images --output file_manifest.csv
"""

import argparse
import csv
import hashlib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

SUPPORTED = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".dcm", ".dicom"}


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ocp_name(stem: str) -> dict:
    import re
    patient = re.search(r"OCP\d+(?:_\d+)?", stem)
    stain = "Ki67" if "Ki67" in stem else ("HE" if "_HE_" in stem else "unknown")
    mag = re.search(r"\d+x", stem, re.IGNORECASE)
    section = "top" if "top" in stem.lower() else ("bottom" if "bottom" in stem.lower() else "")
    return {
        "patient_id": patient.group(0) if patient else "",
        "section": section,
        "stain": stain,
        "magnification": mag.group(0) if mag else "",
    }


def generate_manifest(source: Path, output: Path) -> None:
    files = sorted(f for f in source.rglob("*") if f.suffix.lower() in SUPPORTED)
    log.info("Processing %d files…", len(files))

    fieldnames = ["filename", "relative_path", "size_bytes", "md5", "patient_id",
                  "section", "stain", "magnification"]

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for fp in files:
            m = parse_ocp_name(fp.stem)
            writer.writerow({
                "filename": fp.name,
                "relative_path": str(fp.relative_to(source)),
                "size_bytes": fp.stat().st_size,
                "md5": md5_file(fp),
                **m,
            })
            log.info("  %s", fp.name)

    log.info("Manifest saved to %s (%d entries)", output, len(files))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", default="data/file_manifest.csv")
    args = parser.parse_args()
    generate_manifest(Path(args.source), Path(args.output))


if __name__ == "__main__":
    main()
