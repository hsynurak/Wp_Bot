"""Meta (WhatsApp Cloud API) webhook uç noktaları."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/webhook", tags=["Webhook"])

WEBHOOK_VERIFY_TOKEN = "humer_wp_verify_123"


async def process_whatsapp_message(payload: dict) -> None:
    print("Webhook log:", payload)


@router.get("/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
) -> PlainTextResponse:
    if hub_verify_token != WEBHOOK_VERIFY_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return PlainTextResponse(content=hub_challenge)


@router.post("/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    # TODO: Meta App Secret ile HMAC imza doğrulaması ekle (X-Hub-Signature-256).

    payload = await request.json()
    background_tasks.add_task(process_whatsapp_message, payload)
    return {"status": "ok"}
