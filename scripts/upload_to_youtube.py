#!/usr/bin/env python3
"""
upload_to_youtube.py
Upload the project showcase video to YouTube via YouTube Data API v3.

Setup (one-time):
    1. Go to https://console.cloud.google.com
    2. Create a project → Enable "YouTube Data API v3"
    3. Create OAuth 2.0 credentials → Desktop App
    4. Download client_secret.json → put in same folder as this script
    5. pip3 install google-api-python-client google-auth-oauthlib --break-system-packages

Usage:
    python3 scripts/upload_to_youtube.py \
        --video "/Volumes/traininig/data/DICOM_Migration_Showcase.mp4" \
        --secrets client_secret.json
"""

import argparse
import os
import pickle
import sys
from pathlib import Path

# ── Video metadata ─────────────────────────────────────────────────────────
VIDEO_TITLE = (
    "DICOM Image Migration: OnePACS → AWS S3 | "
    "TP53 Precursor Lesions | Python + GitHub Actions"
)

VIDEO_DESCRIPTION = """
🏥 Complete DICOM image migration project walkthrough!

In this video I walk through migrating 105 GB of histopathology images
from the Cancer Imaging Archive (TCIA) TP53 Precursor Lesions dataset
to AWS S3, with full DICOM conversion and verification.

📌 What's covered:
• Downloading medical imaging data via IBM Aspera Connect
• Converting TIF/PNG histopathology images to DICOM format
• Uploading to AWS S3 with encryption & checksum verification
• Verifying DICOM files in Horos viewer
• Automated CI/CD with GitHub Actions

🛠 Tech Stack:
Python • boto3 • pydicom • Pillow • AWS S3 • GitHub Actions • Horos

📂 Full source code on GitHub:
https://github.com/vizz-bob/AWS-S3-DICOM

📊 Dataset:
TP53 Precursor Lesions – Cancer Imaging Archive
https://www.cancerimagingarchive.net/collection/tp53-precursor-lesions/

#DICOM #AWS #MedicalImaging #Python #DataEngineering #CloudMigration
#HealthcareIT #GitHubActions #MachineLearning #OpenSource
"""

VIDEO_TAGS = [
    "DICOM", "AWS S3", "medical imaging", "Python", "data migration",
    "boto3", "pydicom", "GitHub Actions", "healthcare IT", "cloud storage",
    "TP53", "histopathology", "oncology", "PACS", "cancer imaging archive",
    "data engineering", "open source"
]

CATEGORY_ID = "28"   # Science & Technology
PRIVACY     = "public"   # "public", "private", or "unlisted"


def get_authenticated_service(secrets_file: str):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    token_file = "youtube_token.pickle"

    if os.path.exists(token_file):
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)
        print("✅ Authenticated and token saved")

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path: Path):
    from googleapiclient.http import MediaFileUpload

    print(f"Uploading: {video_path.name} ({video_path.stat().st_size / 1e6:.1f} MB)")

    body = {
        "snippet": {
            "title":       VIDEO_TITLE,
            "description": VIDEO_DESCRIPTION,
            "tags":        VIDEO_TAGS,
            "categoryId":  CATEGORY_ID,
        },
        "status": {
            "privacyStatus": PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=50 * 1024 * 1024,   # 50 MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  Uploading... {pct}%", end="\r")

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\n✅ Upload complete!")
    print(f"   Video ID : {video_id}")
    print(f"   URL      : {url}")
    return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",   required=True, help="Path to .mp4 video file")
    parser.add_argument("--secrets", default="client_secret.json",
                        help="Path to Google OAuth client_secret.json")
    parser.add_argument("--privacy", default=PRIVACY,
                        choices=["public", "private", "unlisted"])
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        sys.exit(1)

    if not Path(args.secrets).exists():
        print(f"""
❌ client_secret.json not found.

Steps to get it:
  1. Go to https://console.cloud.google.com
  2. Create or select a project
  3. APIs & Services → Enable APIs → search 'YouTube Data API v3' → Enable
  4. APIs & Services → Credentials → Create Credentials → OAuth client ID
  5. Application type: Desktop App → Create
  6. Download JSON → rename to client_secret.json
  7. Place it in the same folder as this script
""")
        sys.exit(1)

    try:
        youtube = get_authenticated_service(args.secrets)
        upload_video(youtube, video_path)
    except ImportError:
        print("❌ Missing packages. Run:")
        print("   pip3 install google-api-python-client google-auth-oauthlib --break-system-packages")
        sys.exit(1)


if __name__ == "__main__":
    main()
