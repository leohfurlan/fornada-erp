"""Inbox e monitor iFood de teste.

Revision ID: d72ab3149801
Revises: 0f6af4c60f80
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "d72ab3149801"
down_revision = "0f6af4c60f80"
branch_labels = None
depends_on = None


def common_columns() -> list[sa.Column]:
    """Identidade, isolamento e auditoria comuns às tabelas da integração."""
    return [
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("merchant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    ]


def upgrade() -> None:
    op.create_table(
        "ifood_monitores",
        *common_columns(),
        sa.Column("loja_nome", sa.String(200), nullable=False),
        sa.Column("ultima_consulta", sa.DateTime(timezone=True)),
        sa.Column("ultima_recepcao", sa.DateTime(timezone=True)),
        sa.Column("proxima_consulta", sa.DateTime(timezone=True)),
        sa.Column("erro", sa.String(200)),
        sa.UniqueConstraint("tenant_id"),
        sa.UniqueConstraint("merchant_id"),
    )
    op.create_table(
        "ifood_eventos",
        *common_columns(),
        sa.Column("event_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", pg.UUID(as_uuid=True)),
        sa.Column("codigo", sa.String(80), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ack_em", sa.DateTime(timezone=True)),
        sa.Column("processado_em", sa.DateTime(timezone=True)),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proxima_tentativa", sa.DateTime(timezone=True)),
        sa.Column("erro", sa.String(200)),
        sa.UniqueConstraint("tenant_id", "event_id"),
    )
    op.create_table(
        "ifood_pedidos_observados",
        *common_columns(),
        sa.Column("order_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("ultimo_evento", sa.String(80), nullable=False),
        sa.Column("evento_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", pg.JSONB(), nullable=False),
        sa.UniqueConstraint("tenant_id", "order_id"),
    )
    for table in ("ifood_monitores", "ifood_eventos", "ifood_pedidos_observados"):
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    op.create_index("ix_ifood_eventos_order_id", "ifood_eventos", ["order_id"])


def downgrade() -> None:
    for table in ("ifood_pedidos_observados", "ifood_eventos", "ifood_monitores"):
        op.drop_table(table)
