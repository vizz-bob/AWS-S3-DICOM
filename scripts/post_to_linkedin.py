#!/usr/bin/env python3
"""
post_to_linkedin.py
Post a project update to LinkedIn via the LinkedIn API.

Setup (one-time):
    1. Go to https://www.linkedin.com/developers/apps/new
    2. Create an app → add product 'Share on LinkedIn' + 'Sign In with LinkedIn'
    3. Copy Client ID and Client Secret
    4. Set Redirect URL to: http://localhost:8080/callback
    5. pip3 install requests --break-system-packages

Usage:
    export LINKEDIN_CLIENT_ID=your_client_id
    export LINKEDIN_CLIENT_SECRET=your_client_secret
    python3 scripts/post_to_linkedin.py
    python3 scripts/post_to_linkedin.py --youtube-url https://youtu.be/YOUR_VIDEO_ID
"""

import argparse
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs
import requests

TOKEN_FILE = "linkedin_token.json"

# ── Post content ───────────────────────────────────────────────────────────
def build_post_text(youtube_url: str = "") -> str:
    video_line = f"\n\n🎥 Watch the full walkthrough: {youtube_url}" if youtube_url else ""
    return f"""🏥 Excited to share my latest project: DICOM Image Migration Pipeline!

Migrated the TP53 Precursor Lesions dataset (105 GB of histopathology images) from the Cancer Imaging Archive to AWS S3 — fully automated with Python and GitHub Actions.

🔬 What I built:
✅ Automated download via IBM Aspera Connect
✅ TIF/PNG → DICOM conversion using pydicom & Pillow
✅ Multipart upload to AWS S3 with checksum verification
✅ DICOM validation & verification in Horos viewer
✅ Full CI/CD pipeline with 3 GitHub Actions workflows

📊 Dataset stats:
• 297 files | 5.1 GB (first batch)
• 78 OCP patients | Ki67 & H&E staining
• 4x, 10x, 20x, 40x magnifications{video_line}

📂 Full source code (open source):
https://github.com/vizz-bob/AWS-S3-DICOM

This project bridges medical imaging research and modern cloud infrastructure — making DICOM datasets more accessible for AI/ML research.

Next up: migrating the remaining 100 GB and integrating with a cloud PACS viewer.

#MedicalImaging #DICOM #AWS #Python #DataEngineering #HealthcareIT
#GitHubActions #CloudMigration #OpenSource #MachineLearning #Oncology"""


# ── OAuth flow ─────────────────────────────────────────────────────────────
class OAuthHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        OAuthHandler.auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authentication successful! You can close this window.</h2>")

    def log_message(self, format, *args):
        pass  # Suppress server logs


def get_access_token(client_id: str, client_secret: str) -> str:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return json.load(f).get("access_token", "")

    REDIRECT_URI = "http://localhost:8080/callback"
    SCOPE = "openid profile email w_member_social"

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urlencode({
            "response_type": "code",
            "client_id":     client_id,
            "redirect_uri":  REDIRECT_URI,
            "scope":         SCOPE,
        })
    )

    print("Opening browser for LinkedIn authorization...")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), OAuthHandler)
    server.handle_request()

    if not OAuthHandler.auth_code:
        print("❌ No auth code received")
        sys.exit(1)

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          OAuthHandler.auth_code,
            "redirect_uri":  REDIRECT_URI,
            "client_id":     client_id,
            "client_secret": client_secret,
        },
    )
    token_data = resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        print(f"❌ Token error: {token_data}")
        sys.exit(1)

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)
    print("✅ LinkedIn authenticated and token saved")
    return access_token


def get_profile_id(access_token: str) -> str:
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    data = resp.json()
    return data.get("sub", "")


def post_to_linkedin(access_token: str, author_id: str, text: str) -> None:
    payload = {
        "author":          f"urn:li:person:{author_id}",
        "lifecycleState":  "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization":  f"Bearer {access_token}",
            "Content-Type":   "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
    )

    if resp.status_code in (200, 201):
        post_id = resp.headers.get("x-restli-id", "")
        print(f"✅ LinkedIn post published!")
        print(f"   Post ID: {post_id}")
        print(f"   View at: https://www.linkedin.com/feed/")
    else:
        print(f"❌ LinkedIn post failed: {resp.status_code}")
        print(resp.text)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--youtube-url", default="",
                        help="YouTube video URL to include in the post")
    parser.add_argument("--preview", action="store_true",
                        help="Print the post text without posting")
    args = parser.parse_args()

    post_text = build_post_text(args.youtube_url)

    if args.preview:
        print("─" * 60)
        print(post_text)
        print("─" * 60)
        print(f"\nCharacter count: {len(post_text)}/3000")
        return

    client_id     = os.environ.get("LINKEDIN_CLIENT_ID")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("""
❌ LinkedIn credentials not set.

Steps to get them:
  1. Go to https://www.linkedin.com/developers/apps/new
  2. Create app → add 'Share on LinkedIn' product
  3. Copy Client ID and Client Secret from Auth tab
  4. Set redirect URL: http://localhost:8080/callback

Then run:
  export LINKEDIN_CLIENT_ID=your_client_id
  export LINKEDIN_CLIENT_SECRET=your_client_secret
  python3 scripts/post_to_linkedin.py --youtube-url https://youtu.be/YOUR_ID
""")
        sys.exit(1)

    token     = get_access_token(client_id, client_secret)
    author_id = get_profile_id(token)
    post_to_linkedin(token, author_id, post_text)


if __name__ == "__main__":
    main()
