"""Inbox e snapshots de teste, sem efeitos sobre pedidos comerciais ou estoque."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models import TenantMixin, TimestampMixin
from infrastructure.database.session import Base


class IfoodMonitor(TenantMixin, TimestampMixin, Base):
    __tablename__ = "ifood_monitores"
    __table_args__ = (UniqueConstraint("tenant_id"), UniqueConstraint("merchant_id"))
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    loja_nome: Mapped[str] = mapped_column(String(200), nullable=False)
    ultima_consulta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultima_recepcao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proxima_consulta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    erro: Mapped[str | None] = mapped_column(String(200))


class IfoodEvento(TenantMixin, TimestampMixin, Base):
    __tablename__ = "ifood_eventos"
    __table_args__ = (UniqueConstraint("tenant_id", "event_id"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)
    codigo: Mapped[str] = mapped_column(String(80), nullable=False)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ack_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tentativas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    proxima_tentativa: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    erro: Mapped[str | None] = mapped_column(String(200))


class IfoodPedidoObservado(TenantMixin, TimestampMixin, Base):
    __tablename__ = "ifood_pedidos_observados"
    __table_args__ = (UniqueConstraint("tenant_id", "order_id"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    ultimo_evento: Mapped[str] = mapped_column(String(80), nullable=False)
    evento_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)


class IfoodAlerta(TenantMixin, TimestampMixin, Base):
    """Um aviso por pedido; envio WhatsApp controlado antes da chamada externa."""

    __tablename__ = "ifood_alertas"
    __table_args__ = (UniqueConstraint("tenant_id", "order_id"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    whatsapp_estado: Mapped[str] = mapped_column(String(20), nullable=False, default="desabilitado")
    whatsapp_tentativas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    whatsapp_iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    whatsapp_enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proxima_tentativa: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    erro: Mapped[str | None] = mapped_column(String(200))


class IfoodAlertaLeitura(TenantMixin, TimestampMixin, Base):
    __tablename__ = "ifood_alertas_leituras"
    __table_args__ = (UniqueConstraint("tenant_id", "usuario_id", "alerta_id"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    alerta_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ifood_alertas.id"), nullable=False
    )
