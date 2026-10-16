from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models import TenantMixin, TimestampMixin
from infrastructure.database.session import Base


class PwaEvento(TenantMixin, TimestampMixin, Base):
    """Sinais de adesão declarados pelo navegador, não estado de instalação."""

    __tablename__ = "pwa_eventos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "usuario_id", "event_id", name="uq_pwa_evento"),
        Index("ix_pwa_usuario_tipo_data", "tenant_id", "usuario_id", "tipo", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    browser_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    origem: Mapped[str] = mapped_column(String(20), nullable=False)
