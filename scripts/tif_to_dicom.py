#!/usr/bin/env python3
"""
tif_to_dicom.py
Convert TIF/PNG histopathology images to DICOM format.
Parses OCP filename convention to populate DICOM tags.

Usage:
    python tif_to_dicom.py --input /path/to/tif_files --output /path/to/dicom_output
"""

import argparse
import datetime
import logging
import re
import sys
from pathlib import Path

import numpy as np
import pydicom
from PIL import Image
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

# DICOM UID for VL Microscopic Image Storage
VL_MICROSCOPIC_IMAGE_UID = "1.2.840.10008.5.1.4.1.1.77.1.2"
EXPLICIT_VR_LITTLE_ENDIAN = "1.2.840.10008.1.2.1"

# Study UID shared across all conversions in this run
STUDY_INSTANCE_UID = generate_uid()


def parse_filename(stem: str) -> dict:
    """
    Parse OCP filename into metadata fields.
    Example: OCP107_3_top_30_count90-100_Ki67_10x
    """
    meta = {
        "patient_id": "UNKNOWN",
        "section": "",
        "slide_num": "",
        "cell_count": "",
        "stain": "UNKNOWN",
        "magnification": "",
        "description": stem,
    }

    # Extract patient ID (OCP followed by digits, optionally _N for biopsy)
    patient_match = re.search(r"(OCP\d+(?:_\d+)?)", stem)
    if patient_match:
        meta["patient_id"] = patient_match.group(1)

    # Section (top/bottom)
    if "top" in stem.lower():
        meta["section"] = "top"
    elif "bottom" in stem.lower():
        meta["section"] = "bottom"

    # Slide number
    slide_match = re.search(r"(?:top|bottom)_(\d+)", stem, re.IGNORECASE)
    if slide_match:
        meta["slide_num"] = slide_match.group(1)

    # Cell count
    count_match = re.search(r"count([\d+,-]+)", stem, re.IGNORECASE)
    if count_match:
        meta["cell_count"] = count_match.group(1)

    # Stain type
    if "Ki67" in stem:
        meta["stain"] = "Ki67"
    elif "_HE_" in stem or stem.endswith("_HE"):
        meta["stain"] = "HE"

    # Magnification
    mag_match = re.search(r"(\d+x)", stem, re.IGNORECASE)
    if mag_match:
        meta["magnification"] = mag_match.group(1)

    return meta


def image_to_dicom(input_path: Path, output_path: Path) -> None:
    """Convert a single TIF/PNG to a DICOM file."""
    # Load image and convert to RGB
    img = Image.open(input_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    rows, cols = arr.shape[:2]

    meta = parse_filename(input_path.stem)
    today = datetime.date.today().strftime("%Y%m%d")
    sop_uid = generate_uid()

    # ── File meta ──────────────────────────────────────────────────────────────
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = VL_MICROSCOPIC_IMAGE_UID
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = EXPLICIT_VR_LITTLE_ENDIAN

    ds = FileDataset(str(output_path), {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_implicit_VR = False
    ds.is_little_endian = True

    # ── Patient module ─────────────────────────────────────────────────────────
    ds.PatientName = meta["patient_id"]
    ds.PatientID = meta["patient_id"]
    ds.PatientBirthDate = ""
    ds.PatientSex = ""

    # ── General study module ───────────────────────────────────────────────────
    ds.StudyInstanceUID = STUDY_INSTANCE_UID
    ds.StudyDate = today
    ds.StudyTime = ""
    ds.ReferringPhysicianName = ""
    ds.StudyID = "TP53_PRECURSOR"
    ds.AccessionNumber = ""
    ds.StudyDescription = "TP53 Precursor Lesions - Cancer Imaging Archive"

    # ── General series module ──────────────────────────────────────────────────
    ds.SeriesInstanceUID = generate_uid()
    ds.SeriesNumber = meta["slide_num"] or "1"
    ds.Modality = "SM"  # Slide Microscopy
    ds.SeriesDescription = f"{meta['section']} {meta['stain']} {meta['magnification']}"

    # ── General image module ───────────────────────────────────────────────────
    ds.SOPClassUID = VL_MICROSCOPIC_IMAGE_UID
    ds.SOPInstanceUID = sop_uid
    ds.InstanceNumber = "1"
    ds.ContentDate = today
    ds.ContentTime = ""
    ds.ImageComments = meta["description"]

    # ── Image pixel module ─────────────────────────────────────────────────────
    ds.SamplesPerPixel = 3
    ds.PhotometricInterpretation = "RGB"
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PlanarConfiguration = 0
    ds.PixelData = arr.tobytes()

    pydicom.dcmwrite(str(output_path), ds, write_like_original=False)


def convert_directory(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        f for f in input_dir.rglob("*")
        if f.suffix.lower() in {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    )

    if not files:
        log.warning("No image files found in %s", input_dir)
        return

    log.info("Converting %d files…", len(files))
    ok = errors = 0
    for fp in files:
        out = output_dir / (fp.stem + ".dcm")
        try:
            image_to_dicom(fp, out)
            log.info("✓  %s → %s", fp.name, out.name)
            ok += 1
        except Exception as exc:
            log.error("✗  %s — %s", fp.name, exc)
            errors += 1

    log.info("Conversion complete — OK: %d  Errors: %d", ok, errors)
    if errors:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Convert TIF/PNG to DICOM")
    parser.add_argument("--input",  required=True, help="Input directory with TIF/PNG files")
    parser.add_argument("--output", required=True, help="Output directory for .dcm files")
    args = parser.parse_args()
    convert_directory(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
