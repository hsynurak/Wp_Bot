"""
WhatsApp Stil Asistanı — CLIP tabanlı benzer ürün arama API'si.

Sunucu ayağa kalkarken CLIP modeli ve ChromaDB belleğe yüklenir.
WhatsApp botundan gelen görseller POST /search ile işlenir.
"""

from __future__ import annotations

import asyncio
import collections
import httpx  # pip install httpx
import io
import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile, Response
from PIL import Image
from pydantic import BaseModel, Field

from src.config import (
    ASSETS_DIR,
    CHROMA_PERSIST_DIR,
    CLIP_TOP_K,
    DEFAULT_COMPANY_ID,
    LIVE_CLIP_COLLECTION_NAME,
    PHOTOS_DIR,
    TEMP_UPLOADS_DIR,
)
from src.preprocessor import ImagePreprocessor
from src.models import get_extractor
from src.models.feature_extractor import CLIPExtractor
from src.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

# Meta retry / spam koruması: son 1000 mesaj id'si ve aktif işlem gören kullanıcılar
PROCESSED_MESSAGE_IDS: collections.deque[str] = collections.deque(maxlen=1000)
ACTIVE_USERS: set[str] = set()

# Kullanıcı durumu (state) ve temsilci kataloğu
USER_STATES: dict[str, str] = {}

# Test için örnek temsilci veritabanı (ileride DB'den gelecek)
AGENTS: dict[str, dict[str, str]] = {
    "0": {"name": "Yeni Müşteri Destek", "phone": "905550000000"},
    "1": {"name": "Ali Bey", "phone": "905551112233"},
    "2": {"name": "Ayşe Hanım", "phone": "905554445566"},
    "3": {"name": "Mehmet Bey", "phone": "905557778899"},
    "4": {"name": "Zeynep Hanım", "phone": "905551234567"},
    "5": {"name": "Can Bey", "phone": "905552345678"},
    "6": {"name": "Elif Hanım", "phone": "905553456789"},
    "7": {"name": "Burak Bey", "phone": "905554567890"},
    "8": {"name": "Selin Hanım", "phone": "905555678901"},
    "9": {"name": "Emre Bey", "phone": "905556789012"},
    "10": {"name": "Deniz Hanım", "phone": "905557890123"},
    "11": {"name": "Kerem Bey", "phone": "905558901234"},
    "12": {"name": "Merve Hanım", "phone": "905559012345"},
}

# Meta WhatsApp Cloud API webhook doğrulama token'ı
VERIFY_TOKEN = "WpBot_Gizli_Token_2026"

# Meta WhatsApp Cloud API — mesaj gönderme kimlik bilgileri
WHATSAPP_TOKEN = "EAAVjpkLJEU4BSGAwnYaDZAxqc7dtpnDkeU3am4xJ5cVKZC3kKeXxYWuJoeBygZCL35DYwIySZAXPPfIBYxvA80eq77gK7fAPZBPIzmq4CKngPdQztZB6TrJ5SGgXanl9RjH4giwZAuBL93IqUtYMSVk8xg370eEeEZAt3kyDCCAJrj9CWZAgPkUPLmerAMMSzRYXWNtcJsKapK2ezjRzfFSZA7Lj5NZA8ZClyy8cin7phcnrROTRAYPMFxo6I1fyhr1I27nLncnF5L6oGj9VB9ZAcwt8q"
PHONE_NUMBER_ID = "1344797608707625"

# WhatsApp'a gönderilecek ürün görselleri için dışa açık taban URL (ngrok vb.)
# Boş bırakılırsa webhook isteğindeki request.base_url kullanılır.
NGROK_URL = "https://epiphany-pager-twentieth.ngrok-free.dev"

WHATSAPP_GRAPH_API = "https://graph.facebook.com/v17.0"
MIME_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Notebook ile aynı desteklenen görsel formatları
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/octet-stream",  # curl / bazı bot istemcileri
}


# ---------------------------------------------------------------------------
# Pydantic şemaları
# ---------------------------------------------------------------------------


class SearchResultItem(BaseModel):
    """Tek bir benzer ürün sonucu."""

    product_id: str = Field(..., description="Ürün dosya adı / benzersiz kimlik")
    product_url: str = Field(..., description="Ürün görseline erişim URL'i")
    distance: float = Field(..., description="Cosine mesafesi (0 = özdeş, 2 = zıt)")
    similarity_percent: float = Field(
        ..., description="Yaklaşık benzerlik yüzdesi (1 - distance) * 100"
    )


class SearchResponse(BaseModel):
    """Benzerlik arama yanıtı."""

    query_filename: str
    company_id: str
    collection: str
    results: List[SearchResultItem]
    total_results: int


class HealthResponse(BaseModel):
    """Sunucu ve model durumu."""

    status: str
    company_id: str
    collection: str
    indexed_products: int
    model: str


class WebhookAckResponse(BaseModel):
    """Meta webhook POST yanıtı — her zaman 200 OK dönmek zorunlu."""

    status: str = "ok"


# ---------------------------------------------------------------------------
# Lifespan — model ve vektör deposu önyükleme
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Sunucu başlarken CLIP + ChromaDB yükler; kapanırken bellekten temizler.
    Notebook: sprint1_embedding_pipeline_clip.ipynb ile aynı mantık.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("CLIP modeli belleğe yükleniyor...")

    extractor = get_extractor("clip")
    store = ChromaVectorStore(
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name=LIVE_CLIP_COLLECTION_NAME,
        company_id=DEFAULT_COMPANY_ID,
    )

    app.state.extractor = extractor
    app.state.store = store
    app.state.preprocessor = ImagePreprocessor()
    app.state.company_id = DEFAULT_COMPANY_ID
    app.state.collection = LIVE_CLIP_COLLECTION_NAME

    logger.info(
        "API hazır | koleksiyon=%s | kayıt=%d",
        LIVE_CLIP_COLLECTION_NAME,
        store.count_for_tenant(),
    )

    yield

    # Kapanış — referansları bırak, GC bellekten alsın
    logger.info("Sunucu kapanıyor, model ve vektör deposu temizleniyor...")
    app.state.extractor = None
    app.state.store = None
    app.state.preprocessor = None


# ---------------------------------------------------------------------------
# FastAPI uygulaması
# ---------------------------------------------------------------------------

app = FastAPI(
    title="WhatsApp Stil Asistanı API",
    description="CLIP embedding ile benzer tekstil ürünü arama",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/webhook")
async def verify_webhook(request: Request):
    """ Meta'nın Webhook doğrulama ucudur. """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Meta Webhook Başarıyla Doğrulandı!")
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Yetkisiz Erişim (Token Hatalı)")


@app.get("/images/{filename}")
async def serve_image_as_jpeg(filename: str) -> Response:
    """
    Ürün görselini dinamik olarak JPEG formatında sunar.

    WhatsApp API webp/png desteklemediği için tüm formatlar RGB JPEG'e çevrilir.
    """
    # Path traversal saldırılarını engelle
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Geçersiz dosya adı.")

    file_path = PHOTOS_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Görsel bulunamadı.")

    try:
        with Image.open(file_path) as img:
            rgb = img.convert("RGB")
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=90)
            buffer.seek(0)
            return Response(content=buffer.getvalue(), media_type="image/jpeg")
    except Exception as exc:
        logger.exception("Görsel JPEG'e dönüştürülemedi [%s]: %s", filename, exc)
        raise HTTPException(status_code=500, detail="Görsel işlenemedi.") from exc


@app.get("/assets/{filename}")
async def serve_static_asset(filename: str) -> Response:
    """
    Sistem görsellerini (logo, ekip fotoları vb.) sunar.
    Bu klasör yapay zeka tarafından taranmaz.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Geçersiz dosya adı.")

    file_path = ASSETS_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Statik görsel bulunamadı.")

    try:
        content = file_path.read_bytes()
        mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        return Response(content=content, media_type=mime_type)
    except Exception as exc:
        logger.exception("Statik dosya okunamadı: %s", exc)
        raise HTTPException(status_code=500, detail="Dosya sunulamadı.") from exc


def _get_extractor(request: Request) -> CLIPExtractor:
    """Lifespan sırasında yüklenen CLIP extractor'ı döner."""
    extractor = getattr(request.app.state, "extractor", None)
    if extractor is None:
        raise HTTPException(
            status_code=503,
            detail="CLIP modeli henüz yüklenmedi. Sunucu başlatılıyor olabilir.",
        )
    return extractor


def _get_store(request: Request) -> ChromaVectorStore:
    """Lifespan sırasında yüklenen ChromaDB deposunu döner."""
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Vektör deposu henüz yüklenmedi. Sunucu başlatılıyor olabilir.",
        )
    return store


def _get_preprocessor(request: Request) -> ImagePreprocessor:
    """Lifespan sırasında yüklenen görsel ön işleyiciyi döner."""
    preprocessor = getattr(request.app.state, "preprocessor", None)
    if preprocessor is None:
        raise HTTPException(
            status_code=503,
            detail="Görsel ön işleyici henüz yüklenmedi. Sunucu başlatılıyor olabilir.",
        )
    return preprocessor


def _whatsapp_headers() -> dict[str, str]:
    """Meta Graph API istekleri için ortak Authorization header'ı."""
    return {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}


def _resolve_public_base_url(request: Request) -> str:
    """
    WhatsApp'ın erişebileceği genel taban URL'i döner.
    NGROK_URL tanımlıysa onu kullanır; aksi halde request.base_url.
    """
    if NGROK_URL.strip():
        base = NGROK_URL.strip()
        return base if base.endswith("/") else f"{base}/"
    return str(request.base_url)


def _validate_upload(file: UploadFile) -> str:
    """
    Yüklenen dosyanın uzantı ve içerik tipini doğrular.
    Geçerli uzantıyı döner (ör. '.jpg').
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş olamaz.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Desteklenmeyen dosya formatı: {suffix}. "
                f"İzin verilenler: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Desteklenmeyen içerik tipi: {file.content_type}. "
                f"İzin verilenler: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
            ),
        )

    return suffix


async def _save_temp_file(file: UploadFile, suffix: str) -> Path:
    """Yüklenen görseli temp_uploads/ altına benzersiz isimle kaydeder."""
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    dest = TEMP_UPLOADS_DIR / unique_name

    try:
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except OSError as exc:
        logger.exception("Geçici dosya yazılamadı: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Görsel geçici klasöre kaydedilemedi.",
        ) from exc

    return dest


async def find_similar_products(
    image_path: str,
    extractor: CLIPExtractor,
    store: ChromaVectorStore,
    top_k: int = 5,
) -> List[dict[str, Any]]:
    """
    CLIP ile görsel vektörü çıkarır ve ChromaDB'de benzer ürünleri arar.

    Returns:
        Ürün id, mesafe ve benzerlik yüzdesi içeren sözlük listesi.
    """
    path = Path(image_path)
    batch, _ = extractor.preprocess_paths([path])
    if batch.numel() == 0:
        raise ValueError(f"Görsel işlenemedi: {image_path}")

    query_vector = extractor.extract(batch)[0].tolist()
    hits = store.query_similar(query_vector, n_results=top_k)

    results: List[dict[str, Any]] = []
    ids = hits.get("ids", [[]])[0]
    distances = hits.get("distances", [[]])[0]

    for doc_id, dist in zip(ids, distances):
        results.append(
            {
                "product_id": doc_id,
                "distance": round(dist, 6),
                "similarity_percent": round(max(0.0, (1.0 - dist)) * 100.0, 2),
            }
        )

    return results


async def search_and_send_results(
    image_path: str,
    sender: str,
    request: Request,
    *,
    exclude_product_id: Optional[str] = None,
) -> None:
    """
    Verilen görsel yolu ile benzer ürünleri arar ve WhatsApp'a interaktif kartlarla gönderir.

    WhatsApp'tan gelen yeni fotoğraflar ve SIMILAR_* buton tıklamaları bu fonksiyonu kullanır.
    """
    preprocessor = _get_preprocessor(request)
    processed_image_path: Optional[Path] = None

    try:
        processed_image_path = preprocessor.process_image(image_path)

        extractor = _get_extractor(request)
        store = _get_store(request)

        fetch_k = CLIP_TOP_K + 1 if exclude_product_id else CLIP_TOP_K
        similar_products = await find_similar_products(
            str(processed_image_path),
            extractor,
            store,
            top_k=fetch_k,
        )

        if exclude_product_id:
            similar_products = [
                p for p in similar_products if p["product_id"] != exclude_product_id
            ]
        similar_products = similar_products[:CLIP_TOP_K]

        if not similar_products:
            await send_whatsapp_message(sender, "Benzer ürün bulamadım.")
            return

        public_base_url = _resolve_public_base_url(request)

        for product in similar_products:
            product_id = product["product_id"]
            similarity = product["similarity_percent"]
            image_url = f"{public_base_url}images/{product_id}"

            await send_whatsapp_interactive_product_card(
                sender,
                image_url=image_url,
                product_name=product_id,
                similarity_percent=similarity,
            )
            logger.info(
                "Etkileşimli ürün kartı gönderildi | alıcı=%s | ürün=%s | url=%s",
                sender,
                product_id,
                image_url,
            )
            await asyncio.sleep(1.0)

        await send_whatsapp_summary_action_menu(sender)
        logger.info("Özet aksiyon menüsü gönderildi | alıcı=%s", sender)
    finally:
        if processed_image_path is not None:
            try:
                processed_image_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning(
                    "Ön işlenmiş görsel silinemedi [%s]: %s",
                    processed_image_path,
                    exc,
                )


def _similar_results_to_hits(results: List[dict[str, Any]]) -> dict[str, list]:
    """find_similar_products çıktısını ChromaDB hits formatına çevirir."""
    return {
        "ids": [[item["product_id"] for item in results]],
        "distances": [[item["distance"] for item in results]],
    }


def _build_search_response(
    query_filename: str,
    company_id: str,
    collection: str,
    hits: dict,
    base_url: str,
) -> SearchResponse:
    """ChromaDB ham sonucunu Pydantic yanıtına dönüştürür."""
    items: List[SearchResultItem] = []

    ids = hits.get("ids", [[]])[0]
    distances = hits.get("distances", [[]])[0]

    for doc_id, dist in zip(ids, distances):
        similarity_pct = max(0.0, (1.0 - dist)) * 100.0
        items.append(
            SearchResultItem(
                product_id=doc_id,
                product_url=f"{base_url}images/{doc_id}",
                distance=round(dist, 6),
                similarity_percent=round(similarity_pct, 2),
            )
        )

    return SearchResponse(
        query_filename=query_filename,
        company_id=company_id,
        collection=collection,
        results=items,
        total_results=len(items),
    )


def _extract_whatsapp_messages(payload: dict[str, Any]) -> List[dict[str, Any]]:
    """
    Meta webhook payload'undan mesaj listesini güvenli şekilde çıkarır.

    Yol: entry[] -> changes[] -> value -> messages[]
    """
    messages: List[dict[str, Any]] = []

    for entry in payload.get("entry", []) or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []) or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            batch = value.get("messages")
            if not isinstance(batch, list):
                continue
            for message in batch:
                if isinstance(message, dict):
                    messages.append(message)

    return messages


def _log_whatsapp_message(message: dict[str, Any]) -> None:
    """Gelen WhatsApp mesajını terminale yazar; görsel mesajlara öncelik verir."""
    message_id = message.get("id", "bilinmiyor")
    sender = message.get("from", "bilinmiyor")
    msg_type = message.get("type", "bilinmiyor")

    if msg_type == "image":
        image_meta = message.get("image", {})
        mime_type = image_meta.get("mime_type", "bilinmiyor") if isinstance(image_meta, dict) else "bilinmiyor"
        logger.info(
            "WhatsApp görsel mesajı | id=%s | gönderen=%s | mime=%s",
            message_id,
            sender,
            mime_type,
        )
    else:
        logger.info(
            "WhatsApp mesajı | id=%s | gönderen=%s | tür=%s",
            message_id,
            sender,
            msg_type,
        )


def _extract_text_body(message: dict[str, Any]) -> Optional[str]:
    """Metin mesajının gövdesini güvenli şekilde çıkarır."""
    if message.get("type") != "text":
        return None

    text_payload = message.get("text")
    if not isinstance(text_payload, dict):
        return None

    body = text_payload.get("body")
    return body if isinstance(body, str) and body.strip() else None


def _whatsapp_button_title(title: str, max_len: int = 20) -> str:
    """WhatsApp buton başlığı en fazla 20 karakter olmalıdır."""
    if len(title) <= max_len:
        return title
    return title[: max_len - 1] + "…"


async def _post_whatsapp_message(to_number: str, payload: dict[str, Any]) -> None:
    """Meta WhatsApp Cloud API'ye mesaj payload'u gönderir."""
    url = f"{WHATSAPP_GRAPH_API}/{PHONE_NUMBER_ID}/messages"
    headers = {
        **_whatsapp_headers(),
        "Content-Type": "application/json",
    }
    body = {"messaging_product": "whatsapp", "to": to_number, **payload}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=body)
        print(
            f"WhatsApp API yanıtı | alıcı={to_number} | "
            f"type={payload.get('type')} | status={response.status_code} | body={response.text}"
        )


async def send_whatsapp_message(to_number: str, text: str) -> None:
    """
    Meta WhatsApp Cloud API üzerinden metin mesajı gönderir.

    Args:
        to_number: Alıcı WhatsApp numarası (ülke kodu ile, örn. 905551234567)
        text: Gönderilecek mesaj metni
    """
    await _post_whatsapp_message(
        to_number,
        {"type": "text", "text": {"body": text}},
    )


async def send_whatsapp_image(
    to_number: str,
    image_url: str,
    caption: str = "",
) -> None:
    """Meta WhatsApp Cloud API üzerinden görsel mesajı gönderir."""
    image_payload: dict[str, Any] = {"link": image_url}
    if caption:
        image_payload["caption"] = caption

    await _post_whatsapp_message(
        to_number,
        {"type": "image", "image": image_payload},
    )


async def send_whatsapp_interactive_product_card(
    to_number: str,
    image_url: str,
    product_name: str,
    similarity_percent: float,
) -> None:
    """
    Etkileşimli ürün kartı gönderir: görsel header + açıklama + 'Benzerini Bul' butonu.
    """
    body_text = (
        f"🌟 Ürün: {product_name}\n"
        f"📊 Benzerlik: ~{similarity_percent:.0f}%\n"
        f"🔗 Sitede İncele: https://seninsiten.com/urun/{product_name}"
    )
    button_id = f"SIMILAR_{product_name}"[:256]

    await _post_whatsapp_message(
        to_number,
        {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {
                    "type": "image",
                    "image": {"link": image_url},
                },
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": button_id,
                                "title": _whatsapp_button_title("🔄 Benzerini Bul"),
                            },
                        }
                    ]
                },
            },
        },
    )


async def send_whatsapp_summary_action_menu(to_number: str) -> None:
    """Top-5 listesi sonrası kullanıcıya özet aksiyon menüsü gönderir."""
    await _post_whatsapp_message(
        to_number,
        {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": (
                        "Sizin için en uygun 5 ürünü listeledim. "
                        "Nasıl devam etmek istersiniz?"
                    )
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "NEW_SEARCH",
                                "title": _whatsapp_button_title("📸 Yeni Fotoğraf"),
                            },
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "CONNECT_AGENT",
                                "title": _whatsapp_button_title("💬 Temsilciye Bağlan"),
                            },
                        },
                    ]
                },
            },
        },
    )


async def download_whatsapp_image(media_id: str) -> str:
    """
    WhatsApp medya id'si ile görseli indirir ve geçici dosya yolunu döner.

    1. Graph API'den medya metadata (url, mime_type) alınır
    2. Medya binary içeriği indirilir
    3. PHOTOS_DIR altına downloaded_{media_id}.{ext} olarak kaydedilir
    """
    headers = _whatsapp_headers()

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        meta_response = await client.get(
            f"{WHATSAPP_GRAPH_API}/{media_id}",
            headers=headers,
        )
        meta_response.raise_for_status()
        meta = meta_response.json()

        media_url = meta.get("url")
        if not media_url:
            raise ValueError(f"Medya URL bulunamadı | media_id={media_id}")

        mime_type = meta.get("mime_type", "image/jpeg")
        extension = MIME_TO_EXTENSION.get(mime_type, ".jpg")

        image_response = await client.get(media_url, headers=headers)
        image_response.raise_for_status()

        PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = PHOTOS_DIR / f"downloaded_{media_id}{extension}"
        dest_path.write_bytes(image_response.content)

        logger.info("WhatsApp görseli indirildi | path=%s", dest_path)
        return str(dest_path)


async def _handle_image_message(message: dict[str, Any], sender: str, request: Request) -> None:
    """Gelen görsel mesajı indirir, benzer ürünleri arar ve WhatsApp'tan gönderir."""
    downloaded_path: Optional[str] = None

    try:
        image_meta = message.get("image")
        if not isinstance(image_meta, dict):
            logger.warning("Görsel metadata bulunamadı | gönderen=%s", sender)
            return

        media_id = image_meta.get("id")
        if not isinstance(media_id, str) or not media_id:
            logger.warning("Görsel media_id bulunamadı | gönderen=%s", sender)
            return

        await send_whatsapp_message(
            sender,
            "Görselini aldım, benzer ürünleri arıyorum... 🔍",
        )

        downloaded_path = await download_whatsapp_image(media_id)
        await search_and_send_results(downloaded_path, sender, request)

    except Exception as exc:
        logger.exception("Görsel arama akışı hatası | gönderen=%s | hata=%s", sender, exc)
        try:
            await send_whatsapp_message(
                sender,
                "Görsel araması sırasında bir hata oluştu. Lütfen tekrar deneyin.",
            )
        except Exception as notify_exc:
            logger.exception("Hata bildirimi gönderilemedi: %s", notify_exc)
    finally:
        if downloaded_path:
            try:
                Path(downloaded_path).unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("İndirilen görsel silinemedi [%s]: %s", downloaded_path, exc)


async def _handle_interactive_button_reply(
    sender: str,
    button_id: str,
    request: Request,
) -> None:
    """Faz 2: Interaktif buton tıklamalarına göre aksiyon alır."""
    try:
        if button_id == "NEW_SEARCH":
            await send_whatsapp_message(
                sender,
                "Lütfen aramak istediğiniz yeni kıyafetin fotoğrafını gönderin 👗📸",
            )
            return

        if button_id == "CONNECT_AGENT":
            USER_STATES[sender] = "WAITING_AGENT_SELECTION"

            public_base_url = _resolve_public_base_url(request)
            image_url = f"{public_base_url}assets/ekibimiz.png"

            caption_text = (
                "Size yardımcı olmaktan mutluluk duyarız! 🤝\n\n"
                "Lütfen görselden temsilcinizi bulup *numarasını yazın* (Örn: 1).\n"
                "Daha önce kimseyle çalışmadıysanız *0* yazabilirsiniz."
            )

            await send_whatsapp_image(sender, image_url, caption=caption_text)
            return

        if button_id.startswith("SIMILAR_"):
            product_name = button_id.replace("SIMILAR_", "", 1)
            product_path = PHOTOS_DIR / product_name

            if not product_path.is_file():
                logger.warning(
                    "SIMILAR butonu için görsel bulunamadı | ürün=%s | yol=%s",
                    product_name,
                    product_path,
                )
                await send_whatsapp_message(
                    sender,
                    "Ürün görseli bulunamadı. Lütfen tekrar deneyin.",
                )
                return

            await send_whatsapp_message(
                sender,
                "Modeller taranıyor, harika alternatifler buluyorum... 🔍",
            )
            await search_and_send_results(
                str(product_path),
                sender,
                request,
                exclude_product_id=product_name,
            )
            return

        logger.warning("Bilinmeyen buton id | gönderen=%s | id=%s", sender, button_id)

    except Exception as exc:
        logger.exception(
            "Buton aksiyonu hatası | gönderen=%s | id=%s | hata=%s",
            sender,
            button_id,
            exc,
        )
        try:
            await send_whatsapp_message(
                sender,
                "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin.",
            )
        except Exception as notify_exc:
            logger.exception("Hata bildirimi gönderilemedi: %s", notify_exc)


async def _handle_incoming_whatsapp_message(
    message: dict[str, Any],
    request: Request,
) -> None:
    """Gelen mesajı türüne göre işler: metin echo veya görsel arama."""
    sender = message.get("from")
    if not isinstance(sender, str) or not sender:
        return

    message_id = message.get("id")
    if message_id and message_id in PROCESSED_MESSAGE_IDS:
        logger.info("Çift mesaj engellendi")
        return
    if message_id:
        PROCESSED_MESSAGE_IDS.append(message_id)

    if sender in ACTIVE_USERS:
        logger.warning("Kullanıcı şu an işlemde, yeni istek reddedildi")
        return

    ACTIVE_USERS.add(sender)
    try:
        _log_whatsapp_message(message)

        msg_type = message.get("type")
        print(f"👀 İşlenen Mesaj Türü: {msg_type} | Gönderen: {sender}")

        if msg_type == "text":
            text_body = _extract_text_body(message)
            if text_body is None:
                return

            text_body = text_body.strip()

            if USER_STATES.get(sender) == "WAITING_AGENT_SELECTION":
                if text_body in AGENTS:
                    agent = AGENTS[text_body]
                    USER_STATES.pop(sender, None)

                    link = (
                        f"https://wa.me/{agent['phone']}?text="
                        f"Merhaba%20{agent['name'].replace(' ', '%20')},%20"
                        f"ürünler%20hakkında%20bilgi%20almak%20istiyorum."
                    )

                    await send_whatsapp_message(
                        sender,
                        f"Sizi {agent['name']} ile görüşmeye yönlendiriyorum.\n\n"
                        f"Aşağıdaki linke tıklayarak doğrudan kendisine yazabilirsiniz:\n🔗 {link}",
                    )
                else:
                    await send_whatsapp_message(
                        sender,
                        "Lütfen listeden geçerli bir temsilci numarası girin (0 ile 12 arası).",
                    )
                return

            logger.info("Metin mesajı alındı | gönderen=%s | içerik=%s", sender, text_body)
            await send_whatsapp_message(sender, f"Mesajını aldım: {text_body}")
            return

        if msg_type == "interactive":
            interactive_payload = message.get("interactive")
            if not isinstance(interactive_payload, dict):
                return

            button_reply = interactive_payload.get("button_reply")
            if not isinstance(button_reply, dict):
                return

            button_id = button_reply.get("id")
            if not isinstance(button_id, str) or not button_id:
                logger.warning("Interactive mesajda button id yok | gönderen=%s", sender)
                return

            button_title = button_reply.get("title", "")
            logger.info(
                "Butona tıklandı | gönderen=%s | id=%s | title=%s",
                sender,
                button_id,
                button_title,
            )
            await _handle_interactive_button_reply(sender, button_id, request)
            return

        if msg_type == "image":
            await _handle_image_message(message, sender, request)
            return

        # Bilinmeyen veya desteklenmeyen mesaj türleri
        await send_whatsapp_message(
            sender,
            f"Şu an sadece metin ve fotoğraf (galeriden) destekliyorum. Gönderdiğin tür: {msg_type}",
        )
    finally:
        ACTIVE_USERS.discard(sender)


@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Model ve veritabanı durumunu kontrol eder."""
    extractor = _get_extractor(request)
    store = _get_store(request)

    return HealthResponse(
        status="ok",
        company_id=request.app.state.company_id,
        collection=request.app.state.collection,
        indexed_products=store.count_for_tenant(),
        model=extractor.model_name,
    )


@app.post("/search", response_model=SearchResponse)
async def search_similar_products(
    request: Request,
    file: UploadFile = File(..., description="WhatsApp'tan gelen sorgu görseli"),
    top_k: Optional[int] = None,
) -> SearchResponse:
    """
    Yüklenen görselin CLIP vektörünü çıkarır ve ChromaDB'de benzer ürünleri arar.

    - Görsel geçici olarak temp_uploads/ altına kaydedilir
    - İşlem bitince geçici dosya silinir
    - Varsayılan top-k: config.CLIP_TOP_K (5)
    """
    suffix = _validate_upload(file)
    temp_path: Path | None = None

    try:
        temp_path = await _save_temp_file(file, suffix)

        extractor = _get_extractor(request)
        store = _get_store(request)

        n_results = top_k if top_k is not None else CLIP_TOP_K
        if n_results < 1 or n_results > 50:
            raise HTTPException(
                status_code=400,
                detail="top_k değeri 1 ile 50 arasında olmalıdır.",
            )

        try:
            similar_products = await find_similar_products(
                str(temp_path),
                extractor,
                store,
                top_k=n_results,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Benzerlik araması hatası: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="Benzerlik araması sırasında bir hata oluştu.",
            ) from exc

        return _build_search_response(
            query_filename=file.filename or temp_path.name,
            company_id=request.app.state.company_id,
            collection=request.app.state.collection,
            hits=_similar_results_to_hits(similar_products),
            base_url=str(request.base_url),
        )

    finally:
        # Geçici dosyayı her durumda temizle
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as exc:
                logger.warning("Geçici dosya silinemedi [%s]: %s", temp_path, exc)


@app.post("/webhook", response_model=WebhookAckResponse)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> WebhookAckResponse:
    """
    WhatsApp'tan gelen webhook bildirimlerini alır.

    Ağır işlemler (görsel arama, mesaj gönderme) arka planda çalıştırılır;
    Meta webhook timeout/retry almaz.
    """
    try:
        payload = await request.json()
        print("\n📦 GELEN WEBHOOK JSON PAYLOAD'U:\n", payload, "\n")
        if not isinstance(payload, dict):
            logger.warning("Webhook payload dict değil: %s", type(payload))
            return WebhookAckResponse(status="ok")

        messages = _extract_whatsapp_messages(payload)
        for message in messages:
            background_tasks.add_task(_handle_incoming_whatsapp_message, message, request)
    except Exception as exc:
        # İşleme hatası olsa bile Meta'ya 200 dön; aksi halde sonsuz yeniden deneme olur
        logger.exception("Webhook payload işlenirken hata: %s", exc)

    return WebhookAckResponse(status="ok")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
