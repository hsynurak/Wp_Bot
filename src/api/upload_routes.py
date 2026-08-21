"""Admin panelleri için MinIO görsel yükleme uç noktaları."""

from __future__ import annotations

import io
import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from minio import Minio
from PIL import Image
from pydantic import BaseModel

router = APIRouter()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "photos")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() in {"1", "true", "yes"}


class UploadResponse(BaseModel):
    url: str
    filename: str


def _get_minio_client() -> Minio:
    if not MINIO_ENDPOINT or not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="MinIO yapılandırması eksik. MINIO_* değişkenlerini .env dosyasında tanımlayın.",
        )

    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL,
    )


def _build_public_url(object_name: str) -> str:
    scheme = "https" if MINIO_USE_SSL else "http"
    return f"{scheme}://{MINIO_ENDPOINT.strip('/')}/{MINIO_BUCKET}/{object_name}"


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Yalnızca görsel dosyaları yüklenebilir.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Boş dosya yüklenemez.")

    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            rgb = img.convert("RGB")
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=90)
            buffer.seek(0)
            jpeg_bytes = buffer.getvalue()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Görsel işlenemedi.") from exc

    original_stem = os.path.splitext(file.filename or "upload")[0]
    safe_stem = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in original_stem)
    object_name = f"{safe_stem}-{uuid.uuid4().hex[:8]}.jpg"

    client = _get_minio_client()

    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)

    client.put_object(
        MINIO_BUCKET,
        object_name,
        io.BytesIO(jpeg_bytes),
        length=len(jpeg_bytes),
        content_type="image/jpeg",
    )

    return UploadResponse(
        url=_build_public_url(object_name),
        filename=object_name,
    )
