from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers import ifood as router
from core.security import create_access_token
from domain.ifood.notifications import DeliveryFailure, NotificationService
from domain.ifood.service import IfoodObservationService
from infrastructure.database.ifood_models import IfoodAlerta
from infrastructure.ifood.notifications import NotificationRepository
from tests.integration.test_ifood_monitor import again, setup


async def prepare(db):
    user, repo, event, remote = await setup(db)
    repo.notifications_since = datetime.now(UTC) - timedelta(seconds=1)
    repo.whatsapp = True
    await IfoodObservationService(repo, remote, "Teste - loja").tick()
    store = NotificationRepository(db, repo.tenant_id, repo.merchant_id)
    return user, repo, event, remote, store


async def test_new_only_duplicate_events_and_no_status_alerts(db):
    user, repo, event, remote, store = await prepare(db)
    await again(repo)
    remote.poll.return_value = [event.model_copy(update={"id": uuid4()})]
    await IfoodObservationService(repo, remote, "Teste - loja").tick()
    assert len((await store.feed(user.id)).alertas) == 1
    await again(repo)
    remote.poll.return_value = [
        event.model_copy(
            update={
                "id": uuid4(),
                "fullCode": "CANCELLED",
                "createdAt": event.createdAt + timedelta(seconds=2),
            }
        )
    ]
    await IfoodObservationService(repo, remote, "Teste - loja").tick()
    assert not (await store.feed(user.id)).alertas
    assert await store.claim() is None
    row = await db.scalar(select(IfoodAlerta).where(IfoodAlerta.tenant_id == user.tenant_id))
    assert row.whatsapp_estado == "cancelado"
    assert (
        await db.scalar(
            select(func.count())
            .select_from(IfoodAlerta)
            .where(IfoodAlerta.tenant_id == user.tenant_id)
        )
        == 1
    )


async def test_historical_orders_do_not_alert(db):
    user, repo, event, remote = await setup(db)
    repo.notifications_since = event.createdAt + timedelta(seconds=1)
    await IfoodObservationService(repo, remote, "Teste - loja").tick()
    assert not (
        await NotificationRepository(db, repo.tenant_id, repo.merchant_id).feed(user.id)
    ).alertas


async def test_read_is_durable_idempotent_and_tenant_scoped(client, db, monkeypatch):
    user, repo, _, _, store = await prepare(db)
    other, _, _, _ = await setup(db)
    for key, value in dict(
        ifood_enabled=True,
        ifood_notifications_enabled=True,
        ifood_tenant_id=repo.tenant_id,
        ifood_test_merchant_id=repo.merchant_id,
    ).items():
        monkeypatch.setattr(router.settings, key, value)
    path = "/api/v1/integracoes/ifood/alertas"
    auth = {"Authorization": f"Bearer {create_access_token(user.id, user.tenant_id)}"}
    foreign = {"Authorization": f"Bearer {create_access_token(other.id, other.tenant_id)}"}
    assert (await client.get(path)).status_code in (401, 403)
    feed = await client.get(path, headers=auth)
    assert feed.headers["Cache-Control"] == "no-store"
    alert = feed.json()["alertas"][0]
    assert (await client.get(path, headers=foreign)).json() == {"habilitado": False, "alertas": []}
    url = f"{path}/{alert['id']}/lido"
    assert (await client.post(url, headers=foreign)).status_code == 404
    assert (await client.post(url, headers=auth)).status_code == 204
    assert (await client.post(url, headers=auth)).status_code == 204
    assert not (await client.get(path, headers=auth)).json()["alertas"]
    # Outro usuário da mesma empresa ainda pode observar seu próprio aviso.
    assert len((await store.feed(uuid4())).alertas) == 1


async def test_claim_committed_before_send_and_only_one_sender(db):
    _, repo, _, _, store = await prepare(db)
    sender = AsyncMock()

    async def send(phone, message):
        assert phone == "5534999999999"
        assert "(teste)" in message and "R$ 27,00" in message
        async with AsyncSession(bind=db.bind, expire_on_commit=False) as observer:
            competing = NotificationRepository(observer, repo.tenant_id, repo.merchant_id)
            assert await competing.claim() is None
            row = await observer.scalar(
                select(IfoodAlerta).where(IfoodAlerta.tenant_id == repo.tenant_id)
            )
            assert row.whatsapp_estado == "enviando"

    sender.send.side_effect = send
    service = NotificationService(store, sender, "5534999999999", "https://example.com")
    await service.deliver_one()
    await service.deliver_one()
    sender.send.assert_awaited_once()
    row = await db.scalar(select(IfoodAlerta).where(IfoodAlerta.tenant_id == repo.tenant_id))
    assert row.whatsapp_estado == "enviado" and row.whatsapp_enviado_em is not None


@pytest.mark.parametrize(
    "failure,state",
    [
        (DeliveryFailure("pendente", "Conexão"), "pendente"),
        (DeliveryFailure("incerto", "Resposta perdida"), "incerto"),
        (RuntimeError("segredo que não pode ser registrado"), "incerto"),
    ],
)
async def test_send_failure_is_durable_and_does_not_blindly_repeat(db, failure, state):
    _, repo, _, _, store = await prepare(db)
    sender = AsyncMock()
    sender.send.side_effect = failure
    service = NotificationService(store, sender, "5534999999999", "https://example.com")
    await service.deliver_one()
    await service.deliver_one()
    sender.send.assert_awaited_once()
    row = await db.scalar(select(IfoodAlerta).where(IfoodAlerta.tenant_id == repo.tenant_id))
    assert row.whatsapp_estado == state
    assert "segredo" not in row.erro
    assert bool(row.proxima_tentativa) == (state == "pendente")


async def test_stale_inflight_delivery_becomes_uncertain_without_resending(db):
    _, repo, _, _, store = await prepare(db)
    delivery = await store.claim()
    row = await db.get(IfoodAlerta, delivery.id)
    row.whatsapp_iniciado_em = datetime.now(UTC) - timedelta(minutes=3)
    await db.commit()
    assert await store.claim() is None
    await db.refresh(row)
    assert row.whatsapp_estado == "incerto"
