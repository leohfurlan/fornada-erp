"""Inbox/outbox de transporte e rascunhos de compras isolados por tenant."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models import TenantMixin, TimestampMixin
from infrastructure.database.session import Base


class WhatsAppEvento(TimestampMixin, Base):
    """Metadados do transporte anteriores à resolução da conta; sem dados de compra."""

    __tablename__ = "whatsapp_eventos"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    chave: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False)
    enviado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WhatsAppCadastro(TimestampMixin, Base):
    """Estado temporário pré-tenant, restrito ao remetente autenticado pelo transporte."""

    __tablename__ = "whatsapp_cadastros"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    telefone: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    dados: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WhatsAppCompra(TenantMixin, TimestampMixin, Base):
    __tablename__ = "whatsapp_compras"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("usuarios.id"))
    telefone: Mapped[str] = mapped_column(String(15), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pendente", nullable=False)
    itens: Mapped[list] = mapped_column(JSONB, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
