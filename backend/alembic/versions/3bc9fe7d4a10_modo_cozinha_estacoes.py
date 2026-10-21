"""Persistent kitchen station and idempotent command receipts."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "3bc9fe7d4a10"
down_revision: Union[str, Sequence[str], None] = "c409e872a103"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cozinha_estacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="paused", nullable=False),
        sa.Column("revisao", sa.Integer(), server_default="0", nullable=False),
        sa.Column("receita_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receita_versao", sa.String(length=64), nullable=True),
        sa.Column("selecao_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resultados_busca", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("secao", sa.String(length=20), server_default="ingredients", nullable=False),
        sa.Column("bloco_indice", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_hash", sa.String(length=64), nullable=True),
        sa.Column("lease_expira_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_revision", sa.Integer(), nullable=True),
        sa.Column("rendered_revision", sa.Integer(), nullable=True),
        sa.Column("projection", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("aviso", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["receita_id"], ["receitas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "usuario_id", name="uq_cozinha_estacao_usuario"),
    )
    op.create_index("ix_cozinha_estacao_tenant_usuario", "cozinha_estacoes", ["tenant_id", "usuario_id"])
    op.create_index("ix_cozinha_estacoes_tenant_id", "cozinha_estacoes", ["tenant_id"])

    op.create_table(
        "cozinha_comandos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estacao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("command_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("receipt", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["estacao_id"], ["cozinha_estacoes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "usuario_id", "estacao_id", "command_id", name="uq_cozinha_command"),
    )
    op.create_index("ix_cozinha_comandos_tenant_id", "cozinha_comandos", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_cozinha_comandos_tenant_id", table_name="cozinha_comandos")
    op.drop_table("cozinha_comandos")
    op.drop_index("ix_cozinha_estacoes_tenant_id", table_name="cozinha_estacoes")
    op.drop_index("ix_cozinha_estacao_tenant_usuario", table_name="cozinha_estacoes")
    op.drop_table("cozinha_estacoes")
