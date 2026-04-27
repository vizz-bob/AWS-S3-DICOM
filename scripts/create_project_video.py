#!/usr/bin/env python3
"""
create_project_video.py
Creates a professional project showcase video for the DICOM Migration project.
Generates slides with project highlights, stats, and sample images.

Install:
    pip3 install moviepy Pillow numpy --break-system-packages

Usage:
    python3 scripts/create_project_video.py \
        --images "/Volumes/traininig/data" \
        --output "/Volumes/traininig/data/DICOM_Migration_Showcase.mp4"
"""

import argparse
import textwrap
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip, concatenate_videoclips
)
import os

# ── Video settings ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080
FPS = 24
SLIDE_DURATION = 4   # seconds per slide
TRANSITION = 0.5

# ── Brand colors ───────────────────────────────────────────────────────────
NAVY   = (26,  46,  90)
TEAL   = (13, 126, 160)
WHITE  = (255, 255, 255)
LGRAY  = (240, 245, 248)
ORANGE = (224, 123,  53)


def make_bg(color=NAVY):
    img = Image.new("RGB", (WIDTH, HEIGHT), color)
    return img


def draw_slide(title, subtitle, bullets, color=NAVY, accent=TEAL):
    img = make_bg(color)
    draw = ImageDraw.Draw(img)

    # Accent bar top
    draw.rectangle([(0, 0), (WIDTH, 12)], fill=accent)

    # Try to load a font, fall back to default
    try:
        font_title  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        font_sub    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
        font_bullet = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except Exception:
        font_title = font_sub = font_bullet = ImageFont.load_default()

    # Title
    draw.text((100, 80), title, font=font_title, fill=WHITE)

    # Subtitle
    draw.text((100, 180), subtitle, font=font_sub, fill=(150, 210, 230))

    # Divider
    draw.rectangle([(100, 250), (WIDTH - 100, 255)], fill=accent)

    # Bullets
    y = 290
    for bullet in bullets:
        draw.text((120, y), f"✦  {bullet}", font=font_bullet, fill=WHITE)
        y += 60

    # Footer
    draw.rectangle([(0, HEIGHT - 50), (WIDTH, HEIGHT)], fill=accent)
    try:
        font_footer = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except Exception:
        font_footer = ImageFont.load_default()
    draw.text((100, HEIGHT - 38),
              "TP53 Precursor Lesions  |  AWS S3 DICOM Migration  |  github.com/vizz-bob/AWS-S3-DICOM",
              font=font_footer, fill=WHITE)

    return np.array(img)


def make_image_slide(img_path, caption=""):
    """Create a slide showing a sample DICOM/histopathology image."""
    bg = Image.new("RGB", (WIDTH, HEIGHT), NAVY)

    try:
        sample = Image.open(img_path).convert("RGB")
        # Fit image into right portion of slide
        max_w, max_h = 900, 850
        sample.thumbnail((max_w, max_h), Image.LANCZOS)
        x = WIDTH - sample.width - 80
        y = (HEIGHT - sample.height) // 2
        bg.paste(sample, (x, y))
    except Exception:
        pass

    draw = ImageDraw.Draw(bg)
    draw.rectangle([(0, 0), (WIDTH, 12)], fill=TEAL)
    draw.rectangle([(0, HEIGHT - 50), (WIDTH, HEIGHT)], fill=TEAL)

    try:
        font_title  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 56)
        font_sub    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        font_footer = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except Exception:
        font_title = font_sub = font_footer = ImageFont.load_default()

    draw.text((80, 80),  "Sample Image", font=font_title, fill=WHITE)
    draw.text((80, 160), caption,        font=font_sub,   fill=(150, 210, 230))
    draw.text((100, HEIGHT - 38),
              "TP53 Precursor Lesions  |  AWS S3 DICOM Migration  |  github.com/vizz-bob/AWS-S3-DICOM",
              font=font_footer, fill=WHITE)

    return np.array(bg)


def build_video(images_dir: Path, output_path: Path):
    print("Building project showcase video...")
    clips = []

    # ── Slide 1: Title ──────────────────────────────────────────────────────
    frame = draw_slide(
        "DICOM Image Migration",
        "OnePACS  →  AWS S3  →  Postdicom",
        [
            "Dataset: TP53 Precursor Lesions (Cancer Imaging Archive)",
            "105 GB histopathology images",
            "78 OCP patients | Ki67 & H&E staining",
            "4x, 10x, 20x, 40x magnifications",
        ],
        color=NAVY, accent=TEAL
    )
    clips.append(ImageClip(frame).with_duration(SLIDE_DURATION))

    # ── Slide 2: The Problem ────────────────────────────────────────────────
    frame = draw_slide(
        "The Challenge",
        "Migrating 105 GB of medical imaging data to the cloud",
        [
            "Source: OnePACS / Cancer Imaging Archive (TCIA)",
            "Files in TIF/PNG format — not standard DICOM",
            "Needed: cloud storage + DICOM compatibility",
            "Goal: reproducible, automated pipeline",
        ],
        color=(20, 40, 80), accent=ORANGE
    )
    clips.append(ImageClip(frame).with_duration(SLIDE_DURATION))

    # ── Slide 3: Solution Architecture ─────────────────────────────────────
    frame = draw_slide(
        "Solution Architecture",
        "4-stage automated migration pipeline",
        [
            "① Download via IBM Aspera Connect (high-speed FASP protocol)",
            "② Convert TIF/PNG → DICOM using pydicom + Pillow",
            "③ Upload to AWS S3 with multipart + checksum verification",
            "④ View & verify in Horos DICOM viewer",
        ],
        color=NAVY, accent=TEAL
    )
    clips.append(ImageClip(frame).with_duration(SLIDE_DURATION))

    # ── Slide 4: Tech Stack ─────────────────────────────────────────────────
    frame = draw_slide(
        "Technology Stack",
        "Python · AWS · GitHub Actions · DICOM",
        [
            "Python 3  |  boto3  |  pydicom  |  Pillow  |  NumPy",
            "AWS S3 — encrypted bucket with versioning",
            "GitHub Actions — automated CI/CD workflows",
            "Horos — free DICOM viewer for verification",
        ],
        color=(15, 35, 75), accent=TEAL
    )
    clips.append(ImageClip(frame).with_duration(SLIDE_DURATION))

    # ── Slide 5: Sample image ───────────────────────────────────────────────
    sample_files = list(images_dir.glob("*.tif"))
    if sample_files:
        ki67_files = [f for f in sample_files if "Ki67" in f.name and "20x" in f.name]
        sample = ki67_files[0] if ki67_files else sample_files[0]
        frame = make_image_slide(sample, f"Ki67 Immunohistochemistry  |  {sample.stem}")
        clips.append(ImageClip(frame).with_duration(SLIDE_DURATION + 2))

    # ── Slide 6: Results ────────────────────────────────────────────────────
    frame = draw_slide(
        "Results",
        "Migration completed successfully",
        [
            "✅  297 files downloaded (5.1 GB) via IBM Aspera",
            "✅  297 TIF/PNG → DICOM files converted (0 errors)",
            "✅  594 files uploaded to AWS S3 (originals + DICOM)",
            "✅  All images verified in Horos DICOM viewer",
            "✅  Scripts & workflows live on GitHub",
        ],
        color=(10, 60, 40), accent=(0, 180, 120)
    )
    clips.append(ImageClip(frame).with_duration(SLIDE_DURATION))

    # ── Slide 7: GitHub ─────────────────────────────────────────────────────
    frame = draw_slide(
        "Open Source on GitHub",
        "github.com/vizz-bob/AWS-S3-DICOM",
        [
            "upload_to_s3.py    — multipart S3 upload with checksums",
            "tif_to_dicom.py    — TIF/PNG to DICOM converter",
            "validate_dicoms.py — DICOM tag validation",
            "postdicom_upload.py — bulk PACS upload",
            "3 GitHub Actions workflows for full automation",
        ],
        color=NAVY, accent=ORANGE
    )
    clips.append(ImageClip(frame).with_duration(SLIDE_DURATION))

    # ── Slide 8: End card ───────────────────────────────────────────────────
    frame = draw_slide(
        "Thank You",
        "Connect on LinkedIn | Star on GitHub",
        [
            "🔗  github.com/vizz-bob/AWS-S3-DICOM",
            "📧  nami.nimmi@gmail.com",
            "",
            "Next: Download & migrate remaining 100 GB",
        ],
        color=NAVY, accent=TEAL
    )
    clips.append(ImageClip(frame).with_duration(SLIDE_DURATION))

    # ── Concatenate & export ────────────────────────────────────────────────
    final = concatenate_videoclips(clips, method="compose")
    print(f"Exporting to {output_path} ...")
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio=False,
        threads=4,
        preset="medium",
        ffmpeg_params=["-crf", "23"],
    )
    print(f"\n✅ Video saved: {output_path}")
    print(f"   Duration: {final.duration:.1f}s  |  Resolution: {WIDTH}x{HEIGHT}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", default="/Volumes/traininig/data",
                        help="Path to image folder (for sample frame)")
    parser.add_argument("--output", default="/Volumes/traininig/data/DICOM_Migration_Showcase.mp4")
    args = parser.parse_args()
    build_video(Path(args.images), Path(args.output))


if __name__ == "__main__":
    main()
