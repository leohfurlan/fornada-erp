"""Propostas da central: o motor comercial continua dono dos efeitos de estoque."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models import TenantMixin, TimestampMixin
from infrastructure.database.session import Base


class CentralCompra(TenantMixin, TimestampMixin, Base):
    __tablename__ = "central_compras"
    __table_args__ = (UniqueConstraint("tenant_id", "business_id", "media_hash"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    business_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    incoming_message_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    telefone: Mapped[str] = mapped_column(String(20))
    media_hash: Mapped[str] = mapped_column(String(64))
    revisao: Mapped[int] = mapped_column(Integer, default=1)
    estado: Mapped[str] = mapped_column(String(20), default="review")
    leitura: Mapped[dict] = mapped_column(JSONB)
    dialogo: Mapped[dict | None] = mapped_column(JSONB)
    revisada: Mapped[dict | None] = mapped_column(JSONB)
    previa: Mapped[dict | None] = mapped_column(JSONB)
    resumo_hash: Mapped[str | None] = mapped_column(String(64))
    aprovacao_ref: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    aprovacao_message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    operation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), unique=True)
    idempotency_key: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), unique=True)
    operation_digest: Mapped[str | None] = mapped_column(String(64))
    resultado: Mapped[dict | None] = mapped_column(JSONB)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
