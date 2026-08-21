"""
MinIO photos bucket'ındaki .webp dosyalarını .jpg formatına dönüştürür.
Operasyonel kurtarma betiği — scripts/ klasöründen çalıştırın.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio
from PIL import Image

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


def convert_webp_to_jpg() -> None:
    client = _get_minio_client()
    converted = 0

    for obj in client.list_objects(MINIO_BUCKET, recursive=True):
        if not obj.object_name.lower().endswith(".webp"):
            continue

        response = client.get_object(MINIO_BUCKET, obj.object_name)
        try:
            image_bytes = response.read()
        finally:
            response.close()
            response.release_conn()

        with Image.open(io.BytesIO(image_bytes)) as img:
            rgb = img.convert("RGB")
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=90)
            buffer.seek(0)

        jpg_name = str(Path(obj.object_name).with_suffix(".jpg"))

        client.put_object(
            MINIO_BUCKET,
            jpg_name,
            buffer,
            length=buffer.getbuffer().nbytes,
            content_type="image/jpeg",
        )
        client.remove_object(MINIO_BUCKET, obj.object_name)
        converted += 1
        print(f"Dönüştürüldü: {obj.object_name} -> {jpg_name}")

    print(f"✅ Toplam {converted} dosya .jpg formatına dönüştürüldü.")


if __name__ == "__main__":
    convert_webp_to_jpg()
