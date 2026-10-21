from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers import ifood as router
from core.security import create_access_token
from domain.ifood.errors import IfoodAPIError
from domain.ifood.schemas import EventEnvelope, ObservedOrder
from domain.ifood.service import IfoodObservationService
from infrastructure.database.ifood_models import IfoodEvento, IfoodPedidoObservado
from infrastructure.database.models import MovimentacaoEstoquePA, Pedido, Tenant, Usuario, Venda
from infrastructure.ifood.repository import IfoodRepository
from tests.unit.test_ifood_client import order_payload


async def setup(db):
    tenant = Tenant(nome="Teste iFood isolado")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id, nome="Teste", email=f"{uuid4()}@example.com", senha_hash="unused"
    )
    db.add(user)
    await db.commit()
    merchant, oid = uuid4(), uuid4()
    repo = IfoodRepository(db, tenant.id, merchant)
    event = EventEnvelope(
        id=uuid4(),
        merchantId=merchant,
        orderId=oid,
        code="PLC",
        fullCode="PLACED",
        createdAt=datetime.now(UTC),
    )
    remote = AsyncMock()
    remote.poll.return_value = [event]
    remote.order.return_value = ObservedOrder.model_validate(order_payload(merchant, oid))
    return user, repo, event, remote


async def again(repo):
    monitor = await repo.monitor()
    monitor.proxima_consulta = datetime.now(UTC) - timedelta(seconds=1)
    await repo.db.commit()


async def test_ack_only_after_durable_commit_and_retry_no_duplicate_or_commercial_effect(db):
    _, repo, event, remote = await setup(db)

    async def ack(ids):
        assert ids == [event.id]
        # Outra conexão só pode enxergar o evento se já houve commit durável.
        async with AsyncSession(bind=db.bind) as observer:
            count = await observer.scalar(
                select(func.count())
                .select_from(IfoodEvento)
                .where(IfoodEvento.tenant_id == repo.tenant_id)
            )
        assert count == 1

    remote.acknowledge.side_effect = ack
    service = IfoodObservationService(repo, remote, "Teste - loja")
    await service.tick()
    await again(repo)
    await service.tick()
    view = await repo.view(True, 30)
    assert len(view.pedidos) == len(view.eventos) == 1
    assert view.pedidos[0].snapshot.id == event.orderId
    assert view.eventos[0].ack_em is not None
    assert remote.order.await_count == 1
    for model in (Pedido, Venda, MovimentacaoEstoquePA):
        assert (
            await db.scalar(
                select(func.count()).select_from(model).where(model.tenant_id == repo.tenant_id)
            )
            == 0
        )


async def test_failure_to_persist_never_acknowledges(db, monkeypatch):
    _, repo, _, remote = await setup(db)
    monkeypatch.setattr(repo, "save_events", AsyncMock(side_effect=RuntimeError("DB offline")))
    with pytest.raises(RuntimeError):
        await IfoodObservationService(repo, remote, "Teste - loja").tick()
    remote.acknowledge.assert_not_awaited()


async def test_ack_failure_recovered_from_inbox_even_without_redelivery(db):
    _, repo, _, remote = await setup(db)
    service = IfoodObservationService(repo, remote, "Teste - loja")
    remote.acknowledge.side_effect = IfoodAPIError(500)
    await service.tick()
    assert (await repo.view(True, 30)).eventos[0].ack_em is None
    assert len((await repo.view(True, 30)).pedidos) == 1
    await again(repo)
    remote.poll.return_value = []
    remote.acknowledge.side_effect = None
    await service.tick()
    assert (await repo.view(True, 30)).eventos[0].ack_em is not None


async def test_404_order_details_remain_pending_after_ack_and_can_recover(db):
    _, repo, _, remote = await setup(db)
    service = IfoodObservationService(repo, remote, "Teste - loja")
    remote.order.side_effect = IfoodAPIError(404)
    await service.tick()
    view = await repo.view(True, 30)
    assert view.eventos_pendentes == 1
    assert view.eventos[0].ack_em is not None
    assert not view.pedidos
    row = await db.scalar(select(IfoodEvento).where(IfoodEvento.tenant_id == repo.tenant_id))
    row.proxima_tentativa = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()
    await again(repo)
    remote.order.side_effect = None
    remote.poll.return_value = []
    await service.tick()
    assert len((await repo.view(True, 30)).pedidos) == 1


async def test_out_of_order_event_does_not_regress_observed_state(db):
    _, repo, event, remote = await setup(db)
    service = IfoodObservationService(repo, remote, "Teste - loja")
    event.fullCode = "CANCELLED"
    await service.tick()
    await again(repo)
    late = event.model_copy(
        update={
            "id": uuid4(),
            "fullCode": "PLACED",
            "createdAt": event.createdAt - timedelta(minutes=1),
        }
    )
    remote.poll.return_value = [late]
    await service.tick()
    assert (await repo.view(True, 30)).pedidos[0].ultimo_evento == "CANCELLED"


async def test_polling_interval_cannot_be_bypassed_by_restart(db):
    _, repo, _, remote = await setup(db)
    await IfoodObservationService(repo, remote, "Teste - loja").tick()
    await IfoodObservationService(repo, remote, "Teste - loja").tick()
    assert remote.poll.await_count == 1


async def test_merchant_leak_is_not_persisted_or_acknowledged(db):
    _, repo, event, remote = await setup(db)
    event.merchantId = uuid4()
    with pytest.raises(ValueError):
        await IfoodObservationService(repo, remote, "Teste - loja").tick()
    remote.acknowledge.assert_not_awaited()
    assert not (await repo.view(True, 30)).eventos


async def test_authenticated_monitor_is_scoped_and_has_no_network_side_effects(
    client, db, monkeypatch
):
    user, repo, _, remote = await setup(db)
    await IfoodObservationService(repo, remote, "Teste - loja").tick()
    other, other_repo, _, _ = await setup(db)
    monkeypatch.setattr(router.settings, "ifood_enabled", True)
    monkeypatch.setattr(router.settings, "ifood_tenant_id", repo.tenant_id)
    monkeypatch.setattr(router.settings, "ifood_test_merchant_id", repo.merchant_id)
    path = "/api/v1/integracoes/ifood/monitor"
    assert (await client.get(path)).status_code in (401, 403)
    a = await client.get(
        path, headers={"Authorization": f"Bearer {create_access_token(user.id, user.tenant_id)}"}
    )
    b = await client.get(
        path, headers={"Authorization": f"Bearer {create_access_token(other.id, other.tenant_id)}"}
    )
    assert len(a.json()["pedidos"]) == 1
    assert b.json()["pedidos"] == []
    assert b.json()["merchant_id"] is None
    assert "secret" not in a.text.lower()
    assert remote.poll.await_count == 1
    assert (
        await db.scalar(
            select(func.count())
            .select_from(IfoodPedidoObservado)
            .where(IfoodPedidoObservado.tenant_id == other_repo.tenant_id)
        )
        == 0
    )
