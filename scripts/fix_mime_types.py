"""
MinIO photos bucket'ındaki .jpg dosyalarının Content-Type metadata'sını düzeltir.
Operasyonel kurtarma betiği — scripts/ klasöründen çalıştırın.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio
from minio.commonconfig import CopySource

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "photos")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() in {"1", "true", "yes"}


def _get_minio_client() -> Minio:
    if not MINIO_ENDPOINT or not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
        raise RuntimeError(
            "MINIO_ENDPOINT, MINIO_ACCESS_KEY ve MINIO_SECRET_KEY .env dosyasında tanımlı olmalı."
        )

    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL,
    )


def fix_mime_types() -> None:
    client = _get_minio_client()
    fixed = 0

    for obj in client.list_objects(MINIO_BUCKET, recursive=True):
        object_name = obj.object_name
        suffix = Path(object_name).suffix.lower()
        if suffix not in {".jpg", ".jpeg"}:
            continue

        stat = client.stat_object(MINIO_BUCKET, object_name)
        if stat.content_type == "image/jpeg":
            continue

        client.copy_object(
            MINIO_BUCKET,
            object_name,
            CopySource(MINIO_BUCKET, object_name),
            metadata={"Content-Type": "image/jpeg"},
            metadata_directive="REPLACE",
        )
        fixed += 1
        print(f"MIME düzeltildi: {object_name}")

    print(f"✅ Toplam {fixed} dosyanın Content-Type değeri image/jpeg olarak ayarlandı.")


if __name__ == "__main__":
    fix_mime_types()
