# TP53 Precursor Lesions — DICOM Migration

Migration pipeline for the **TP53 Precursor Lesions** histopathology dataset  
(Cancer Imaging Archive) from OnePACS → AWS S3 → Postdicom.

**Dataset:** 105 GB | 78 patients | TIF/PNG histopathology images  
**Stains:** Ki67 immunohistochemistry + H&E  
**Magnifications:** 4x, 10x, 20x, 40x

---

## Quick Start

```bash
# 1. Install dependencies
pip install boto3 pydicom Pillow tqdm requests

# 2. Configure AWS
aws configure

# 3. Generate file manifest from your downloaded images
python scripts/generate_checksums.py \
  --source /Volumes/DICOM_DATA/TP53_Dataset/OCP_images \
  --output data/file_manifest.csv

# 4. Upload to S3 (dry run first!)
python scripts/upload_to_s3.py \
  --bucket tp53-dicom-migration-2026 \
  --prefix ocp-images/ \
  --source /Volumes/DICOM_DATA/TP53_Dataset/OCP_images \
  --dry-run

# 5. Real upload (remove --dry-run)
python scripts/upload_to_s3.py \
  --bucket tp53-dicom-migration-2026 \
  --prefix ocp-images/ \
  --source /Volumes/DICOM_DATA/TP53_Dataset/OCP_images

# 6. Optional: Convert TIF → DICOM
python scripts/tif_to_dicom.py \
  --input /Volumes/DICOM_DATA/TP53_Dataset/OCP_images \
  --output /Volumes/DICOM_DATA/TP53_Dataset/DICOM_converted

# 7. Upload to Postdicom
export POSTDICOM_API_KEY=your_key
export POSTDICOM_WORKSPACE_ID=your_workspace_id
python scripts/postdicom_upload.py \
  --input-dir /Volumes/DICOM_DATA/TP53_Dataset/OCP_images
```

## Scripts

| Script | Purpose |
|---|---|
| `generate_checksums.py` | Create MD5 manifest of all image files |
| `upload_to_s3.py` | Upload TIF/PNG/DCM files to AWS S3 |
| `tif_to_dicom.py` | Convert TIF/PNG to DICOM format |
| `validate_dicoms.py` | Validate DICOM tags and pixel data |
| `postdicom_upload.py` | Bulk upload to Postdicom PACS API |

## GitHub Actions

| Workflow | Trigger | Purpose |
|---|---|---|
| `s3-sync.yml` | Push / Manual | Sync manifest; manual image upload |
| `validate-dicom.yml` | Manual | Sample and validate DICOM files |
| `postdicom-upload.yml` | Manual | Bulk upload to Postdicom |

## Required GitHub Secrets

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
POSTDICOM_API_KEY
POSTDICOM_WORKSPACE_ID
```

## Full Documentation

See `docs/DICOM_Migration_Guide.pdf` for the complete step-by-step guide.

## Data Source

[TP53 Precursor Lesions — Cancer Imaging Archive](https://www.cancerimagingarchive.net/collection/tp53-precursor-lesions/)

> **Note:** TCIA data is for research use only. Review the [TCIA Data Usage Policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/) before uploading to any third-party service.
