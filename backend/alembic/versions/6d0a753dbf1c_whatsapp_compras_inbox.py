"""whatsapp_compras_inbox

Revision ID: 6d0a753dbf1c
Revises: a42f344c4565
Create Date: 2026-10-06 11:24:56.674753

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "6d0a753dbf1c"
down_revision: Union[str, None] = "a42f344c4565"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    def timestamps() -> list:
        return [
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        ]

    op.create_table(
        "whatsapp_eventos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chave", sa.String(300), nullable=False, unique=True),
        sa.Column("resposta", sa.Text(), nullable=False),
        sa.Column("enviado", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "whatsapp_compras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=False,
        ),
        sa.Column("telefone", sa.String(15), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("itens", postgresql.JSONB(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_whatsapp_compras_tenant_id", "whatsapp_compras", ["tenant_id"])
    op.create_table(
        "whatsapp_cadastros",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telefone", sa.String(15), nullable=False, unique=True),
        sa.Column("dados", postgresql.JSONB(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
    )


def downgrade() -> None:
    op.drop_table("whatsapp_cadastros")
    op.drop_index("ix_whatsapp_compras_tenant_id", table_name="whatsapp_compras")
    op.drop_table("whatsapp_compras")
    op.drop_table("whatsapp_eventos")
