import base64
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.config import settings
from domain.exceptions import ValidationError
from domain.whatsapp.messages import IncomingMessage, manual_item, parse_message
from domain.whatsapp.service import WhatsAppService
from infrastructure.database.whatsapp_models import WhatsAppCompra, WhatsAppEvento
from infrastructure.whatsapp.evolution import decode_image


def payload(**key):
    return {
        "event": "messages.upsert",
        "instance": "test",
        "data": {
            "key": {
                "id": "msg1",
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                **key,
            },
            "message": {"conversation": "COMPRAR"},
        },
    }


@pytest.mark.parametrize(
    "key",
    [
        {"fromMe": True},
        {"remoteJid": "123@g.us"},
        {"remoteJid": "123@lid"},
        {"remoteJid": "status@broadcast"},
        {"id": ""},
    ],
)
def test_ignore_unsafe_envelopes(key):
    assert parse_message(payload(**key), "test") is None


def test_reject_other_instance():
    assert parse_message(payload(), "other") is None
    assert parse_message(payload(), "test").phone == "5511999999999"


def test_manual_decimal_and_positive_values():
    item = manual_item("ITEM Açúcar; 2,5; kg; 5,90")
    assert str(item.quantidade) == "2.5"
    assert str(item.custo_unitario) == "5.90"
    with pytest.raises(ValidationError):
        manual_item("ITEM Açúcar; 0; kg; 5")


@pytest.mark.parametrize(
    "data,mime", [("bad!", "image/png"), ("", "image/png"), ("YQ==", "text/html")]
)
def test_media_rejects_invalid(data, mime):
    with pytest.raises(ValidationError):
        decode_image(data, mime)


def test_media_decodes_and_bounds():
    assert decode_image(base64.b64encode(b"image").decode(), "image/png") == b"image"
    with pytest.raises(ValidationError):
        decode_image("a" * (12 * 1024 * 1024), "image/png")


def service_with(*rows):
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=list(rows))
    db.commit = AsyncMock()
    compras = SimpleNamespace(confirmar=AsyncMock(), processar_ocr=AsyncMock())
    adapter = SimpleNamespace(
        send_text=AsyncMock(), image=AsyncMock(return_value=(b"image", "image/png"))
    )
    return WhatsAppService(db, adapter, compras)


def incoming(text, image=False):
    return IncomingMessage("5511999999999", "msg1", text, image, {})


def user():
    return SimpleNamespace(id=uuid4(), tenant_id=uuid4())


@pytest.mark.asyncio
async def test_unlinked_user_cannot_access_purchase():
    service = service_with(None, None, None)
    result = await service.handle(incoming("CONFIRMAR"))
    assert "Vamos criar sua conta" in result
    service.compras.confirmar.assert_not_awaited()


@pytest.mark.asyncio
async def test_manual_purchase_creates_preview_only():
    account = user()
    service = service_with(account, None)
    result = await service.handle(incoming("ITEM Açúcar; 2; kg; 5,90"))
    draft = service.db.add.call_args.args[0]
    assert draft.tenant_id == account.tenant_id
    assert "CONFIRMAR" in result
    service.compras.confirmar.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmation_uses_resolved_tenant():
    account = user()
    draft = WhatsAppCompra(
        itens=[manual_item("ITEM Açúcar; 2; kg; 5").model_dump(mode="json")],
        expira_em=datetime.now(UTC) + timedelta(hours=1),
    )
    service = service_with(account, draft)
    await service.handle(incoming("CONFIRMAR"))
    assert draft.status == "confirmada"
    assert service.compras.confirmar.call_args.args[0] == account.tenant_id
    query = str(service.db.scalar.call_args.args[0])
    assert "whatsapp_compras.tenant_id" in query and "whatsapp_compras.usuario_id" in query


@pytest.mark.asyncio
async def test_expired_draft_cannot_be_confirmed():
    draft = WhatsAppCompra(expira_em=datetime.now(UTC) - timedelta(seconds=1))
    service = service_with(user(), draft)
    await service.handle(incoming("CONFIRMAR"))
    service.compras.confirmar.assert_not_awaited()
    assert draft.status == "expirada"


@pytest.mark.asyncio
async def test_duplicate_event_does_not_repeat_stock_effects():
    event = WhatsAppEvento(chave="test:msg1", resposta="Compra salva", enviado=True)
    service = service_with(event)
    service.handle = AsyncMock()
    await service.process(incoming("CONFIRMAR"))
    service.handle.assert_not_awaited()
    service.adapter.send_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_retry_replays_only_outbox():
    event = WhatsAppEvento(chave="test:msg1", resposta="Compra salva", enviado=False)
    service = service_with(event)
    service.handle = AsyncMock()
    await service.process(incoming("CONFIRMAR"))
    service.handle.assert_not_awaited()
    service.adapter.send_text.assert_awaited_once()
    assert event.enviado


@pytest.mark.asyncio
async def test_unit_mismatch_does_not_create_draft():
    service = service_with(user(), None)
    service.compras.processar_ocr.return_value = SimpleNamespace(
        fonte="gemma4",
        itens=[SimpleNamespace(unidade="kg", unidade_sugerida="g")],
    )
    result = await service.handle(incoming("", image=True))
    assert "unidades diferentes" in result
    service.db.add.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_auth_and_queue(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from infrastructure.celery.whatsapp_tasks import process_whatsapp
    from main import app

    monkeypatch.setattr(settings, "evolution_enabled", True)
    monkeypatch.setattr(settings, "evolution_instance", "test")
    monkeypatch.setattr(settings, "evolution_webhook_secret", "s" * 32)
    queue = MagicMock()
    monkeypatch.setattr(process_whatsapp, "delay", queue)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/whatsapp/webhook", json=payload())
        assert response.status_code == 401
        queue.assert_not_called()
        response = await client.post(
            "/api/v1/whatsapp/webhook", json=payload(), headers={"X-Webhook-Secret": "s" * 32}
        )
        assert response.status_code == 202
        queue.assert_called_once()
