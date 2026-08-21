"""
PostgreSQL base_products tablosundaki görsel URL'lerini .webp -> .jpg formatına günceller.
Operasyonel kurtarma betiği — scripts/ klasöründen çalıştırın.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import engine
from src.models.db_models import Base_Products

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "photos")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() in {"1", "true", "yes"}


def _build_minio_base_url() -> str | None:
    if not MINIO_ENDPOINT:
        return None

    scheme = "https" if MINIO_USE_SSL else "http"
    return f"{scheme}://{MINIO_ENDPOINT.strip('/')}/{MINIO_BUCKET}"


def _normalize_image_url(image_url: str | None, minio_base: str | None) -> str | None:
    if not image_url:
        return image_url

    updated = image_url.replace(".webp", ".jpg")

    if minio_base and "/photos/" in updated:
        filename = updated.rsplit("/", 1)[-1]
        updated = f"{minio_base}/{filename}"

    return updated


def fix_db_smart() -> None:
    minio_base = _build_minio_base_url()
    updated_count = 0

    with Session(engine) as session:
        products = session.exec(select(Base_Products)).all()

        for product in products:
            new_url = _normalize_image_url(product.image_url, minio_base)
            if new_url != product.image_url:
                product.image_url = new_url
                session.add(product)
                updated_count += 1

        session.commit()

    print(f"✅ {updated_count} ürünün image_url alanı güncellendi.")


if __name__ == "__main__":
    fix_db_smart()
