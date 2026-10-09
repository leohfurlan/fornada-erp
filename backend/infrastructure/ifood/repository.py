"""Persistência durável antes do ACK, sempre limitada ao tenant e merchant configurados."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ifood.schemas import EventEnvelope, EventView, MonitorView, ObservedOrder, OrderView
from infrastructure.database.ifood_models import (
    IfoodAlerta,
    IfoodEvento,
    IfoodMonitor,
    IfoodPedidoObservado,
)


class IfoodRepository:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        merchant_id: UUID,
        notifications_since: datetime | None = None,
        whatsapp: bool = False,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.merchant_id = merchant_id
        self.notifications_since = notifications_since
        self.whatsapp = whatsapp

    def scope(self, model: type) -> tuple:
        """Filtro obrigatório para todas as consultas da integração."""
        return (
            model.tenant_id == self.tenant_id,
            model.merchant_id == self.merchant_id,
            model.deleted_at.is_(None),
        )

    async def monitor(self) -> IfoodMonitor | None:
        return await self.db.scalar(select(IfoodMonitor).where(*self.scope(IfoodMonitor)))

    async def begin(self, name: str, interval: int) -> bool:
        """Persiste o agendamento: reiniciar o processo não acelera o polling."""
        monitor = await self.monitor()
        now = datetime.now(UTC)
        if monitor is None:
            monitor = IfoodMonitor(
                tenant_id=self.tenant_id, merchant_id=self.merchant_id, loja_nome=name
            )
            self.db.add(monitor)
        if monitor.proxima_consulta and monitor.proxima_consulta > now:
            return False
        monitor.proxima_consulta = now + timedelta(seconds=interval)
        await self.db.commit()
        return True

    async def save_events(self, events: list[EventEnvelope]) -> None:
        """Commit é concluído antes que o service possa enviar ACK."""
        for event in events:
            if event.merchantId != self.merchant_id:
                raise ValueError("Merchant divergente")
            await self.db.execute(
                insert(IfoodEvento)
                .values(
                    tenant_id=self.tenant_id,
                    merchant_id=self.merchant_id,
                    event_id=event.id,
                    order_id=event.orderId,
                    codigo=event.fullCode or event.code,
                    ocorrido_em=event.createdAt,
                )
                .on_conflict_do_nothing(index_elements=["tenant_id", "event_id"])
            )
        monitor = await self.monitor()
        if monitor:
            monitor.ultima_consulta = datetime.now(UTC)
            monitor.erro = None
            if events:
                monitor.ultima_recepcao = datetime.now(UTC)
        await self.db.commit()

    async def pending_ack(self) -> list[UUID]:
        query = (
            select(IfoodEvento.event_id)
            .where(
                *self.scope(IfoodEvento),
                IfoodEvento.ack_em.is_(None),
            )
            .order_by(IfoodEvento.created_at)
            .limit(2000)
        )
        return list((await self.db.scalars(query)).all())

    async def mark_ack(self, ids: list[UUID]) -> None:
        events = (
            await self.db.scalars(
                select(IfoodEvento).where(
                    *self.scope(IfoodEvento),
                    IfoodEvento.event_id.in_(ids),
                )
            )
        ).all()
        for event in events:
            event.ack_em = datetime.now(UTC)
        await self.db.commit()

    async def pending(self) -> list[IfoodEvento]:
        query = (
            select(IfoodEvento)
            .where(
                *self.scope(IfoodEvento),
                IfoodEvento.processado_em.is_(None),
                or_(
                    IfoodEvento.proxima_tentativa.is_(None),
                    IfoodEvento.proxima_tentativa <= datetime.now(UTC),
                ),
            )
            .order_by(IfoodEvento.ocorrido_em)
            .limit(5)
        )
        return list((await self.db.scalars(query)).all())

    async def cached_order(self, order_id: UUID) -> dict | None:
        row = await self.db.scalar(
            select(IfoodPedidoObservado).where(
                *self.scope(IfoodPedidoObservado),
                IfoodPedidoObservado.order_id == order_id,
            )
        )
        return row.snapshot if row else None

    async def complete(self, event: IfoodEvento, order: ObservedOrder | None) -> None:
        if order is not None:
            stmt = insert(IfoodPedidoObservado).values(
                tenant_id=self.tenant_id,
                merchant_id=self.merchant_id,
                order_id=order.id,
                ultimo_evento=event.codigo,
                evento_em=event.ocorrido_em,
                snapshot=order.model_dump(mode="json"),
            )
            await self.db.execute(
                stmt.on_conflict_do_update(
                    index_elements=["tenant_id", "order_id"],
                    set_={
                        "ultimo_evento": event.codigo,
                        "evento_em": event.ocorrido_em,
                        "snapshot": order.model_dump(mode="json"),
                        "updated_at": datetime.now(UTC),
                    },
                    where=IfoodPedidoObservado.evento_em <= event.ocorrido_em,
                )
            )
            if (
                self.notifications_since
                and event.ocorrido_em >= self.notifications_since
                and event.codigo in ("PLACED", "PLC")
                and order.isTest
            ):
                # Mesmo commit do snapshot: um crash nunca deixa pedido sem aviso durável.
                await self.db.execute(
                    insert(IfoodAlerta)
                    .values(
                        tenant_id=self.tenant_id,
                        merchant_id=self.merchant_id,
                        order_id=order.id,
                        whatsapp_estado="pendente" if self.whatsapp else "desabilitado",
                    )
                    .on_conflict_do_nothing(index_elements=["tenant_id", "order_id"])
                )
        event.processado_em = datetime.now(UTC)
        event.erro = None
        await self.db.commit()

    async def fail_event(self, event: IfoodEvento, status: int, delay: int) -> None:
        event.tentativas += 1
        event.erro = f"Detalhes indisponíveis (HTTP {status}); nova tentativa agendada."
        event.proxima_tentativa = datetime.now(UTC) + timedelta(
            seconds=max(delay, min(300, 30 * 2 ** min(event.tentativas - 1, 4))),
        )
        # 404 transitório é tentado por até 10 minutos desde a recepção.
        if status in (403, 502) or (
            status == 404 and datetime.now(UTC) - event.created_at >= timedelta(minutes=10)
        ):
            event.processado_em = datetime.now(UTC)
            event.erro = f"Detalhes não validados (HTTP {status}). Evento preservado para revisão."
        await self.db.commit()

    async def fail_poll(self, status: int, delay: int) -> None:
        monitor = await self.monitor()
        if monitor:
            monitor.erro = f"Falha na comunicação iFood (HTTP {status}). Tentaremos novamente."
            monitor.proxima_consulta = datetime.now(UTC) + timedelta(seconds=max(30, delay))
        await self.db.commit()

    async def view(self, enabled: bool, interval: int) -> MonitorView:
        monitor = await self.monitor()
        orders = (
            await self.db.scalars(
                select(IfoodPedidoObservado)
                .where(
                    *self.scope(IfoodPedidoObservado),
                )
                .order_by(IfoodPedidoObservado.created_at.desc())
                .limit(50)
            )
        ).all()
        events = (
            await self.db.scalars(
                select(IfoodEvento)
                .where(
                    *self.scope(IfoodEvento),
                )
                .order_by(IfoodEvento.created_at.desc())
                .limit(30)
            )
        ).all()
        pending = await self.db.scalar(
            select(func.count())
            .select_from(IfoodEvento)
            .where(
                *self.scope(IfoodEvento),
                IfoodEvento.processado_em.is_(None),
            )
        )
        alerts = (
            await self.db.scalars(
                select(IfoodAlerta).where(
                    *self.scope(IfoodAlerta),
                    IfoodAlerta.order_id.in_([o.order_id for o in orders]),
                )
            )
        ).all()
        delivery_states = {a.order_id: a.whatsapp_estado for a in alerts}
        return MonitorView(
            habilitado=enabled,
            intervalo_segundos=interval,
            loja_nome=monitor.loja_nome if monitor else None,
            merchant_id=self.merchant_id,
            ultima_consulta=monitor.ultima_consulta if monitor else None,
            ultima_recepcao=monitor.ultima_recepcao if monitor else None,
            erro=monitor.erro if monitor else None,
            eventos_pendentes=pending or 0,
            pedidos=[
                OrderView(
                    id=o.id,
                    ultimo_evento=o.ultimo_evento,
                    evento_em=o.evento_em,
                    snapshot=o.snapshot,
                    aviso_whatsapp=delivery_states.get(o.order_id),
                )
                for o in orders
            ],
            eventos=[EventView.model_validate(event) for event in events],
        )
