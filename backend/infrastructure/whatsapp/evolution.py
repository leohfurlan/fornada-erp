"""Transporte Evolution v2. Nunca baixa URLs fornecidas pelo webhook."""

import base64
import binascii
import json
from urllib.parse import quote

import httpx

from core.config import settings
from domain.exceptions import ValidationError

MAX_IMAGE = 8 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def decode_image(encoded: str, mime: str) -> bytes:
    if mime not in IMAGE_TYPES:
        raise ValidationError("Envie uma foto em JPG, PNG ou WebP, de até 8 MB.")
    encoded = encoded.split(",", 1)[-1] if encoded.startswith("data:") else encoded
    if len(encoded) > ((MAX_IMAGE + 2) // 3) * 4:
        raise ValidationError("A foto excede 8 MB.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValidationError("Não conseguimos ler a foto. Envie novamente.") from exc
    if not content or len(content) > MAX_IMAGE:
        raise ValidationError("Envie uma foto de até 8 MB.")
    return content


class EvolutionAdapter:
    async def _post(self, route: str, payload: dict) -> dict:
        instance = quote(settings.evolution_instance, safe="")
        url = f"{settings.evolution_api_url.rstrip('/')}/{route}/{instance}"
        async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
            # Limita também a resposta codificada antes de fazer parse do JSON.
            async with client.stream(
                "POST", url, json=payload, headers={"apikey": settings.evolution_api_key}
            ) as response:
                response.raise_for_status()
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > 12 * 1024 * 1024:
                        raise ValidationError("A foto excede 8 MB.")
                return json.loads(chunks)

    async def send_text(self, phone: str, text: str) -> None:
        await self._post("message/sendText", {"number": phone, "text": text})

    async def image(self, message: dict) -> tuple[bytes, str]:
        media = await self._post(
            "chat/getBase64FromMediaMessage", {"message": message, "convertToMp4": False}
        )
        mime = media.get("mimetype", "")
        return decode_image(media.get("base64", ""), mime), mime


class EvolutionSender:
    """Porta de envio de OTP compartilhada com a autenticação por telefone."""

    def __init__(self, url: str, api_key: str, instance: str) -> None:
        self.url, self.api_key, self.instance = url, api_key, instance

    async def enviar_codigo(self, telefone: str, codigo: str) -> None:
        url = f"{self.url.rstrip('/')}/message/sendText/{quote(self.instance, safe='')}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(
                url,
                headers={"apikey": self.api_key},
                json={
                    "number": telefone.lstrip("+"),
                    "text": (
                        f"Seu código Fornada é {codigo}. Válido por 5 minutos. Não compartilhe."
                    ),
                },
            )
            response.raise_for_status()
