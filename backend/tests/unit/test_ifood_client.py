from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from core.config import Settings
from domain.ifood.errors import IfoodAPIError
from domain.ifood.schemas import ObservedOrder
from infrastructure.ifood.client import IfoodClient


def order_payload(merchant, order=None):
    return {
        "id": str(order or uuid4()),
        "displayId": "1975",
        "isTest": True,
        "merchant": {"id": str(merchant), "name": "Teste - loja"},
        "createdAt": datetime.now(UTC).isoformat(),
        "orderType": "DELIVERY",
        "orderTiming": "IMMEDIATE",
        "category": "FOOD",
        "salesChannel": "IFOOD",
        "customer": {"name": "NÃO PERSISTIR", "documentNumber": "123"},
        "total": {
            "subTotal": 21,
            "deliveryFee": 5,
            "additionalFees": 1,
            "benefits": 0,
            "orderAmount": 27,
        },
        "items": [
            {
                "name": "Combo",
                "quantity": 1,
                "unitPrice": 5,
                "totalPrice": 16,
                "options": [
                    {
                        "name": "Adicional",
                        "quantity": 1,
                        "price": 8,
                        "options": [{"name": "Subadicional", "quantity": 1, "price": 3}],
                    }
                ],
            }
        ],
    }


def test_snapshot_preserves_nested_combo_and_decimal_without_consumer():
    order = ObservedOrder.model_validate(order_payload(uuid4()))
    snapshot = order.model_dump(mode="json")
    assert "customer" not in snapshot
    assert snapshot["total"]["orderAmount"] == "27"
    assert snapshot["items"][0]["options"][0]["options"][0]["name"] == "Subadicional"


async def test_token_reuse_401_refresh_keeps_merchant_filter_and_204_is_empty():
    merchant = uuid4()
    calls = []
    auth_count = 0
    poll_count = 0

    def handler(request):
        nonlocal auth_count, poll_count
        calls.append(request.url.path)
        if request.url.path.endswith("/oauth/token"):
            auth_count += 1
            return httpx.Response(
                200, json={"accessToken": f"token-{auth_count}", "expiresIn": 3600}
            )
        if request.url.path.endswith(str(merchant)):
            return httpx.Response(200, json={"id": str(merchant), "name": "Teste - loja"})
        assert request.headers["x-polling-merchants"] == str(merchant)
        assert request.url.params["categories"] == "FOOD"
        poll_count += 1
        return httpx.Response(401 if poll_count == 1 else 204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        remote = IfoodClient(http, uuid4(), "secret", merchant, "Teste - loja")
        assert await remote.poll() == []
        assert await remote.poll() == []
    assert auth_count == 2
    assert poll_count == 3


async def test_wrong_shop_rejected_before_presence_poll():
    calls = []
    merchant = uuid4()

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        return httpx.Response(200, json={"id": str(merchant), "name": "Loja real"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        remote = IfoodClient(http, uuid4(), "secret", merchant, "Teste - loja")
        with pytest.raises(IfoodAPIError):
            await remote.poll()
    assert not any("events:polling" in path for path in calls)


async def test_429_does_not_leak_body_and_respects_retry_after():
    def handler(request):
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        return httpx.Response(429, headers={"Retry-After": "180"}, text="secret must stay hidden")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        remote = IfoodClient(http, uuid4(), "secret", uuid4(), "Teste - loja")
        with pytest.raises(IfoodAPIError) as error:
            await remote.poll()
    assert error.value.retry_after == 180
    assert "secret" not in str(error.value)


async def test_order_of_other_merchant_or_real_order_is_rejected():
    merchant, oid = uuid4(), uuid4()
    payload = order_payload(merchant, oid)
    payload["isTest"] = False

    def handler(request):
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        remote = IfoodClient(http, uuid4(), "secret", merchant, "Teste - loja")
        with pytest.raises(IfoodAPIError):
            await remote.order(oid)
        payload["isTest"] = True
        payload["merchant"]["id"] = str(uuid4())
        with pytest.raises(IfoodAPIError):
            await remote.order(oid)


def test_monitor_configuration_requires_explicit_shop_and_only_supports_test_mode():
    kwargs = dict(database_url="postgresql+asyncpg://u:p@localhost/test", secret_key="x" * 48)
    assert (
        Settings(_env_file=None, **kwargs, ifood_test_merchant_id="").ifood_test_merchant_id is None
    )
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs, ifood_enabled=True)
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs, ifood_poll_interval_seconds=5)
    configured = dict(
        ifood_enabled=True,
        ifood_client_id=uuid4(),
        ifood_client_secret="test-secret",
        ifood_tenant_id=uuid4(),
        ifood_test_merchant_id=uuid4(),
        ifood_test_merchant_name="Teste - loja",
    )
    assert Settings(_env_file=None, **kwargs, **configured, environment="production").is_production
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs, **configured, ifood_mode="production")
    configured["ifood_test_merchant_name"] = "Loja real"
    with pytest.raises(ValueError):
        Settings(_env_file=None, **kwargs, **configured, environment="production")
