#!/usr/bin/env python3
"""
postdicom_upload.py
Bulk upload images to Postdicom PACS via REST API.

Usage:
    export POSTDICOM_API_KEY=your_api_key
    export POSTDICOM_WORKSPACE_ID=your_workspace_id
    python postdicom_upload.py --input-dir /path/to/images --batch-size 20
"""

import argparse
import csv
import logging
import os
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://app.postdicom.com/api/v1"
SUPPORTED = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".dcm", ".dicom"}


def get_credentials() -> tuple[str, str]:
    api_key = os.environ.get("POSTDICOM_API_KEY")
    workspace_id = os.environ.get("POSTDICOM_WORKSPACE_ID")
    if not api_key or not workspace_id:
        log.error("Set POSTDICOM_API_KEY and POSTDICOM_WORKSPACE_ID environment variables")
        sys.exit(1)
    return api_key, workspace_id


def upload_file(session: requests.Session, workspace_id: str, filepath: Path) -> dict:
    url = f"{BASE_URL}/workspaces/{workspace_id}/upload"
    with open(filepath, "rb") as f:
        resp = session.post(url, files={"file": (filepath.name, f)}, timeout=120)

    if resp.status_code in (200, 201):
        return {"status": "success", "response": resp.json()}
    else:
        return {"status": "error", "code": resp.status_code, "detail": resp.text[:200]}


def batch_upload(input_dir: Path, batch_size: int, report_path: Path) -> None:
    api_key, workspace_id = get_credentials()

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {api_key}"})

    files = sorted(f for f in input_dir.rglob("*") if f.suffix.lower() in SUPPORTED)
    if not files:
        log.warning("No supported files found in %s", input_dir)
        return

    log.info("Uploading %d files in batches of %d", len(files), batch_size)
    results = []
    ok = errors = 0

    for i, fp in enumerate(tqdm(files, unit="file")):
        result = upload_file(session, workspace_id, fp)
        results.append({"file": fp.name, **result})

        if result["status"] == "success":
            ok += 1
        else:
            log.error("Failed: %s — %s", fp.name, result.get("detail", ""))
            errors += 1

        # Rate limiting: small pause every batch_size files
        if (i + 1) % batch_size == 0:
            time.sleep(1)

    # Save report
    with open(report_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "status", "response", "code", "detail"])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})

    log.info("Upload complete — OK: %d  Errors: %d", ok, errors)
    log.info("Report saved to %s", report_path)

    if errors:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Upload images to Postdicom")
    parser.add_argument("--input-dir",   required=True, help="Directory of files to upload")
    parser.add_argument("--batch-size",  type=int, default=20)
    parser.add_argument("--report",      default="postdicom_upload_report.csv")
    args = parser.parse_args()
    batch_upload(Path(args.input_dir), args.batch_size, Path(args.report))


if __name__ == "__main__":
    main()
