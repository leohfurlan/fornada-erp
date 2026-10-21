"""Fila durável de avisos e leituras por usuário, com filtros de tenant e loja."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import exists, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ifood.notifications import Delivery
from domain.ifood.schemas import AlertFeed, AlertView, ObservedOrder
from infrastructure.database.ifood_models import (
    IfoodAlerta,
    IfoodAlertaLeitura,
    IfoodPedidoObservado,
)


class NotificationRepository:
    def __init__(self, db: AsyncSession, tenant_id: UUID, merchant_id: UUID) -> None:
        self.db, self.tenant_id, self.merchant_id = db, tenant_id, merchant_id

    def scope(self, model: type) -> tuple:
        return (
            model.tenant_id == self.tenant_id,
            model.merchant_id == self.merchant_id,
            model.deleted_at.is_(None),
        )

    def orders(self):
        return (
            select(IfoodAlerta, IfoodPedidoObservado)
            .join(
                IfoodPedidoObservado,
                (IfoodPedidoObservado.order_id == IfoodAlerta.order_id)
                & (IfoodPedidoObservado.tenant_id == IfoodAlerta.tenant_id)
                & (IfoodPedidoObservado.merchant_id == IfoodAlerta.merchant_id),
            )
            .where(*self.scope(IfoodAlerta), *self.scope(IfoodPedidoObservado))
        )

    async def feed(self, user_id: UUID) -> AlertFeed:
        read = exists(
            select(IfoodAlertaLeitura.id).where(
                IfoodAlertaLeitura.tenant_id == self.tenant_id,
                IfoodAlertaLeitura.usuario_id == user_id,
                IfoodAlertaLeitura.alerta_id == IfoodAlerta.id,
                IfoodAlertaLeitura.deleted_at.is_(None),
            )
        )
        rows = (
            await self.db.execute(
                self.orders()
                .where(~read, IfoodPedidoObservado.ultimo_evento.not_in(["CANCELLED", "CAN"]))
                .order_by(IfoodAlerta.created_at, IfoodAlerta.id)
                .limit(20)
            )
        ).all()
        alerts = []
        for alert, row in rows:
            order = ObservedOrder.model_validate(row.snapshot)
            alerts.append(
                AlertView(
                    id=alert.id,
                    order_id=alert.order_id,
                    numero=order.displayId,
                    total=order.total.orderAmount,
                    is_test=order.isTest,
                    recebido_em=alert.created_at,
                    whatsapp_estado=alert.whatsapp_estado,
                )
            )
        return AlertFeed(habilitado=True, alertas=alerts)

    async def read(self, alert_id: UUID, user_id: UUID) -> bool:
        alert = await self.db.scalar(
            select(IfoodAlerta).where(*self.scope(IfoodAlerta), IfoodAlerta.id == alert_id)
        )
        if alert is None:
            return False
        await self.db.execute(
            insert(IfoodAlertaLeitura)
            .values(
                tenant_id=self.tenant_id,
                usuario_id=user_id,
                alerta_id=alert_id,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "usuario_id", "alerta_id"])
        )
        await self.db.commit()
        return True

    async def claim(self) -> Delivery | None:
        now = datetime.now(UTC)
        # Task tem hard limit de 75s; um envio interrompido não é tentado novamente.
        await self.db.execute(
            update(IfoodAlerta)
            .where(
                *self.scope(IfoodAlerta),
                IfoodAlerta.whatsapp_estado == "enviando",
                IfoodAlerta.whatsapp_iniciado_em < now - timedelta(minutes=2),
            )
            .values(whatsapp_estado="incerto", erro="Envio interrompido; conferir no WhatsApp.")
        )
        row = (
            await self.db.execute(
                self.orders()
                .where(
                    IfoodAlerta.whatsapp_estado == "pendente",
                    or_(
                        IfoodAlerta.proxima_tentativa.is_(None),
                        IfoodAlerta.proxima_tentativa <= now,
                    ),
                )
                .order_by(IfoodAlerta.created_at)
                .limit(1)
                .with_for_update(of=IfoodAlerta, skip_locked=True)
            )
        ).first()
        if row is None:
            await self.db.commit()
            return None
        alert, observed = row
        if observed.ultimo_evento in ("CANCELLED", "CAN"):
            alert.whatsapp_estado = "cancelado"
            await self.db.commit()
            return None
        order = ObservedOrder.model_validate(observed.snapshot)
        alert.whatsapp_estado = "enviando"
        alert.whatsapp_tentativas += 1
        alert.whatsapp_iniciado_em = now
        delivery = Delivery(
            alert.id,
            alert.order_id,
            order.displayId,
            order.total.orderAmount,
            order.merchant.name,
            order.isTest,
            alert.whatsapp_tentativas,
        )
        await self.db.commit()  # Antes da chamada externa, incluindo redelivery da task.
        return delivery

    async def finish(self, delivery: Delivery, state: str, error: str | None = None) -> None:
        now = datetime.now(UTC)
        await self.db.execute(
            update(IfoodAlerta)
            .where(
                *self.scope(IfoodAlerta),
                IfoodAlerta.id == delivery.id,
                IfoodAlerta.whatsapp_estado == "enviando",
            )
            .values(
                whatsapp_estado=state,
                erro=error,
                whatsapp_enviado_em=now if state == "enviado" else None,
                proxima_tentativa=now
                + timedelta(seconds=min(300, 30 * 2 ** (delivery.attempts - 1)))
                if state == "pendente"
                else None,
            )
        )
        await self.db.commit()
