#!/usr/bin/env python3
"""
upload_to_s3.py
Upload TIF/PNG/DCM files to AWS S3 with multipart support and checksum tracking.

Usage:
    python upload_to_s3.py --bucket BUCKET_NAME --prefix ocp-images/ --source /path/to/images
    python upload_to_s3.py --bucket BUCKET_NAME --prefix ocp-images/ --source /path/to/images --dry-run
"""

import argparse
import boto3
import csv
import hashlib
import logging
import sys
from pathlib import Path
from boto3.s3.transfer import TransferConfig
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".dcm", ".dicom"}

TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=100 * 1024 * 1024,   # 100 MB
    max_concurrency=10,
    multipart_chunksize=50 * 1024 * 1024,    # 50 MB per chunk
    use_threads=True,
)


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def already_uploaded(s3_client, bucket: str, key: str, local_md5: str) -> bool:
    """Return True if the S3 object exists and its md5 metadata matches."""
    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
        return head.get("Metadata", {}).get("md5", "") == local_md5
    except s3_client.exceptions.ClientError:
        return False


def upload_files(source: Path, bucket: str, prefix: str, dry_run: bool = False):
    s3 = boto3.client("s3")
    files = sorted(f for f in source.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS)

    if not files:
        log.warning("No supported files found in %s", source)
        sys.exit(0)

    log.info("Found %d files to upload", len(files))
    results = []
    skipped = uploaded = errors = 0

    for fp in tqdm(files, unit="file"):
        key = prefix + fp.relative_to(source).as_posix()
        local_md5 = md5_file(fp)

        if dry_run:
            log.info("[DRY RUN] Would upload: %s → s3://%s/%s", fp.name, bucket, key)
            results.append({"file": fp.name, "key": key, "status": "dry_run", "md5": local_md5})
            continue

        if already_uploaded(s3, bucket, key, local_md5):
            log.debug("Skipping (already uploaded): %s", fp.name)
            results.append({"file": fp.name, "key": key, "status": "skipped", "md5": local_md5})
            skipped += 1
            continue

        try:
            s3.upload_file(
                str(fp),
                bucket,
                key,
                Config=TRANSFER_CONFIG,
                ExtraArgs={
                    "Metadata": {"md5": local_md5},
                    "ServerSideEncryption": "AES256",
                },
            )
            results.append({"file": fp.name, "key": key, "status": "uploaded", "md5": local_md5})
            uploaded += 1
        except Exception as exc:
            log.error("Failed to upload %s: %s", fp.name, exc)
            results.append({"file": fp.name, "key": key, "status": "error", "md5": local_md5})
            errors += 1

    # Write report
    report_path = Path("upload_report.csv")
    with open(report_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "key", "status", "md5"])
        writer.writeheader()
        writer.writerows(results)

    log.info("Done — uploaded: %d  skipped: %d  errors: %d", uploaded, skipped, errors)
    log.info("Report saved to %s", report_path)

    if errors:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Upload images to AWS S3")
    parser.add_argument("--bucket",  required=True, help="S3 bucket name")
    parser.add_argument("--prefix",  default="ocp-images/", help="S3 key prefix")
    parser.add_argument("--source",  required=True, help="Local source directory")
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        log.error("Source path does not exist: %s", source)
        sys.exit(1)

    upload_files(source, args.bucket, args.prefix, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
