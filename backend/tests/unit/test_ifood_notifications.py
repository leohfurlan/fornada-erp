from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from core.config import Settings
from domain.ifood.notifications import Delivery, DeliveryFailure, message_for
from infrastructure.ifood.whatsapp import IfoodWhatsAppSender
from infrastructure.whatsapp.evolution import EvolutionAdapter


def test_message_has_test_label_amount_and_order_link():
    delivery = Delivery(uuid4(), uuid4(), "1234", Decimal("123.45"), "Teste - loja\nX", True, 1)
    text = message_for(delivery, "https://fornada.example/")
    assert "(teste)" in text and "R$ 123,45" in text
    assert f"#pedido-{delivery.order_id}" in text
    assert "loja X" in text


@pytest.mark.parametrize(
    "error,state",
    [
        (httpx.ConnectError("secret"), "pendente"),
        (httpx.ConnectTimeout("secret"), "pendente"),
        (httpx.ReadTimeout("secret"), "incerto"),
        (httpx.WriteError("secret"), "incerto"),
        (ValueError("secret"), "incerto"),
    ],
)
async def test_transport_distinguishes_definitive_connection_failure_from_uncertainty(
    monkeypatch, error, state
):
    monkeypatch.setattr(EvolutionAdapter, "send_text", AsyncMock(side_effect=error))
    with pytest.raises(DeliveryFailure) as failure:
        await IfoodWhatsAppSender().send("5534999999999", "Mensagem")
    assert failure.value.state == state
    assert "secret" not in failure.value.message


@pytest.mark.parametrize("status,state", [(429, "pendente"), (401, "erro"), (500, "incerto")])
async def test_http_status_failure_is_sanitized(monkeypatch, status, state):
    error = httpx.HTTPStatusError(
        "secret",
        request=httpx.Request("POST", "https://example.com"),
        response=httpx.Response(status),
    )
    monkeypatch.setattr(EvolutionAdapter, "send_text", AsyncMock(side_effect=error))
    with pytest.raises(DeliveryFailure) as failure:
        await IfoodWhatsAppSender().send("5534999999999", "Mensagem")
    assert failure.value.state == state and "secret" not in failure.value.message


def test_activation_requires_monitor_and_timezone_cutoff():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test",
            secret_key="test",
            ifood_notifications_enabled=True,
            ifood_enabled=False,
        )


def test_empty_cutoff_is_valid_when_disabled():
    config = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test",
        secret_key="test",
        ifood_notifications_enabled=False,
        ifood_notifications_since="",
    )
    assert config.ifood_notifications_since is None
