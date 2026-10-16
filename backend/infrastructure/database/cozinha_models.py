from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models import TenantMixin, TimestampMixin
from infrastructure.database.session import Base


class CozinhaEstacao(TenantMixin, TimestampMixin, Base):
    """Persistent recipe position controlled by one authenticated kitchen browser."""

    __tablename__ = "cozinha_estacoes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "usuario_id", name="uq_cozinha_estacao_usuario"),
        Index("ix_cozinha_estacao_tenant_usuario", "tenant_id", "usuario_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False, default="Minha cozinha")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="paused")
    revisao: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    receita_id: Mapped[UUID | None] = mapped_column(ForeignKey("receitas.id"), nullable=True)
    receita_versao: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selecao_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    resultados_busca: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    secao: Mapped[str] = mapped_column(String(20), nullable=False, default="ingredients")
    bloco_indice: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    parte_fala_indice: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lease_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expira_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rendered_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    projection: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    aviso: Mapped[str | None] = mapped_column(Text, nullable=True)


class CozinhaComando(TenantMixin, TimestampMixin, Base):
    """Idempotency receipt for a UI command and its station revision."""

    __tablename__ = "cozinha_comandos"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "usuario_id", "estacao_id", "command_id", name="uq_cozinha_command"
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    estacao_id: Mapped[UUID] = mapped_column(ForeignKey("cozinha_estacoes.id"), nullable=False)
    command_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt: Mapped[dict] = mapped_column(JSONB, nullable=False)


class CozinhaAlexaVinculo(TenantMixin, TimestampMixin, Base):
    """Account consent and explicitly confirmed Echo device for one Fornada user."""

    __tablename__ = "cozinha_alexa_vinculos"
    __table_args__ = (UniqueConstraint("tenant_id", "usuario_id", name="uq_cozinha_alexa_usuario"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    estacao_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cozinha_estacoes.id"), nullable=True
    )
    amazon_user_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_device_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    pending_device_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_device_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_device_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    approved_device_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CozinhaAlexaOAuthContext(TimestampMixin, Base):
    """Short-lived context created by Alexa's authorization-code request."""

    __tablename__ = "cozinha_alexa_oauth_contextos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id: Mapped[str] = mapped_column(String(200), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    code_challenge: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_challenge_method: Mapped[str | None] = mapped_column(String(8), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CozinhaAlexaOAuthGrant(TenantMixin, TimestampMixin, Base):
    """Hashed OAuth authorization codes and rotating opaque tokens."""

    __tablename__ = "cozinha_alexa_oauth_grants"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_cozinha_alexa_token_hash"),
        Index("ix_cozinha_alexa_grant_subject", "tenant_id", "usuario_id", "grant_type"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    family_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(200), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    grant_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    redirect_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_challenge: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_challenge_method: Mapped[str | None] = mapped_column(String(8), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CozinhaAlexaRequest(TenantMixin, TimestampMixin, Base):
    """Idempotency receipt for a verified Alexa request."""

    __tablename__ = "cozinha_alexa_requests"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "amazon_user_hash", "request_id", name="uq_cozinha_alexa_request"
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(String(200), nullable=False)
    amazon_user_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str] = mapped_column(String(300), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
