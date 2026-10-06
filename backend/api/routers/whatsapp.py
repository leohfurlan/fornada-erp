"""Webhook autenticado: valida envelope e entrega processamento à fila."""

import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request

from core.config import settings
from core.rate_limit import limiter
from domain.whatsapp.messages import parse_message

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


@router.post("/webhook", status_code=202)
@limiter.limit("120/minute")
async def webhook(request: Request, x_webhook_secret: str = Header(default="")) -> dict:
    if not settings.evolution_enabled:
        raise HTTPException(503, "WhatsApp indisponível.")
    if not hmac.compare_digest(x_webhook_secret, settings.evolution_webhook_secret):
        raise HTTPException(401, "Webhook não autorizado.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 256 * 1024:
            raise HTTPException(413, "Mensagem muito grande.")
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError
        incoming = parse_message(payload, settings.evolution_instance)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "Mensagem inválida.") from None
    if incoming is None:
        return {"status": "ignorado"}
    from infrastructure.celery.whatsapp_tasks import process_whatsapp

    try:
        process_whatsapp.delay(payload)
    except Exception:
        raise HTTPException(503, "Não foi possível receber a mensagem. Tente novamente.") from None
    return {"status": "recebido"}
