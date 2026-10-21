"""Alexa account linking, OAuth grants, and request idempotency."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a41e0d2f9c66"
down_revision: str | Sequence[str] | None = "3bc9fe7d4a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    timestamps = [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]
    op.create_table(
        "cozinha_alexa_vinculos",
        sa.Column("id", uuid, nullable=False),
        sa.Column("usuario_id", uuid, nullable=False),
        sa.Column("estacao_id", uuid, nullable=True),
        sa.Column("amazon_user_hash", sa.String(64), nullable=True),
        sa.Column("pending_device_id", uuid, nullable=True),
        sa.Column("pending_device_hash", sa.String(64), nullable=True),
        sa.Column("pending_device_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_device_id", uuid, nullable=True),
        sa.Column("approved_device_hash", sa.String(64), nullable=True),
        sa.Column("tenant_id", uuid, nullable=False),
        *timestamps,
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["estacao_id"], ["cozinha_estacoes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "usuario_id", name="uq_cozinha_alexa_usuario"),
    )
    op.create_index("ix_cozinha_alexa_vinculos_tenant_id", "cozinha_alexa_vinculos", ["tenant_id"])
    op.create_table(
        "cozinha_alexa_oauth_contextos",
        sa.Column("id", uuid, nullable=False),
        sa.Column("client_id", sa.String(200), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=True),
        sa.Column("code_challenge_method", sa.String(8), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps,
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cozinha_alexa_oauth_grants",
        sa.Column("id", uuid, nullable=False),
        sa.Column("usuario_id", uuid, nullable=False),
        sa.Column("family_id", uuid, nullable=False),
        sa.Column("client_id", sa.String(200), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("grant_type", sa.String(16), nullable=False),
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=True),
        sa.Column("code_challenge", sa.String(128), nullable=True),
        sa.Column("code_challenge_method", sa.String(8), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", uuid, nullable=False),
        *timestamps,
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_cozinha_alexa_token_hash"),
    )
    op.create_index(
        "ix_cozinha_alexa_oauth_grants_tenant_id", "cozinha_alexa_oauth_grants", ["tenant_id"]
    )
    op.create_index(
        "ix_cozinha_alexa_grant_subject",
        "cozinha_alexa_oauth_grants",
        ["tenant_id", "usuario_id", "grant_type"],
    )
    op.create_index(
        "ix_cozinha_alexa_oauth_grants_family_id", "cozinha_alexa_oauth_grants", ["family_id"]
    )
    op.create_table(
        "cozinha_alexa_requests",
        sa.Column("id", uuid, nullable=False),
        sa.Column("usuario_id", uuid, nullable=False),
        sa.Column("application_id", sa.String(200), nullable=False),
        sa.Column("amazon_user_hash", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(300), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("response", jsonb, nullable=False),
        sa.Column("tenant_id", uuid, nullable=False),
        *timestamps,
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "amazon_user_hash", "request_id", name="uq_cozinha_alexa_request"
        ),
    )
    op.create_index("ix_cozinha_alexa_requests_tenant_id", "cozinha_alexa_requests", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_cozinha_alexa_requests_tenant_id", table_name="cozinha_alexa_requests")
    op.drop_table("cozinha_alexa_requests")
    op.drop_index(
        "ix_cozinha_alexa_oauth_grants_family_id", table_name="cozinha_alexa_oauth_grants"
    )
    op.drop_index("ix_cozinha_alexa_grant_subject", table_name="cozinha_alexa_oauth_grants")
    op.drop_index(
        "ix_cozinha_alexa_oauth_grants_tenant_id", table_name="cozinha_alexa_oauth_grants"
    )
    op.drop_table("cozinha_alexa_oauth_grants")
    op.drop_table("cozinha_alexa_oauth_contextos")
    op.drop_index("ix_cozinha_alexa_vinculos_tenant_id", table_name="cozinha_alexa_vinculos")
    op.drop_table("cozinha_alexa_vinculos")
