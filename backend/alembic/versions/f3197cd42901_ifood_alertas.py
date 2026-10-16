"""Alertas de novos pedidos iFood e leitura por usuário.

Revision ID: f3197cd42901
Revises: d72ab3149801
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "f3197cd42901"
down_revision = "d72ab3149801"
branch_labels = None
depends_on = None


def common() -> list[sa.Column]:
    return [
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
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
        "ifood_alertas",
        *common(),
        sa.Column("merchant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("whatsapp_estado", sa.String(20), nullable=False, server_default="desabilitado"),
        sa.Column("whatsapp_tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("whatsapp_iniciado_em", sa.DateTime(timezone=True)),
        sa.Column("whatsapp_enviado_em", sa.DateTime(timezone=True)),
        sa.Column("proxima_tentativa", sa.DateTime(timezone=True)),
        sa.Column("erro", sa.String(200)),
        sa.UniqueConstraint("tenant_id", "order_id"),
    )
    op.create_table(
        "ifood_alertas_leituras",
        *common(),
        sa.Column(
            "usuario_id", pg.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False
        ),
        sa.Column(
            "alerta_id", pg.UUID(as_uuid=True), sa.ForeignKey("ifood_alertas.id"), nullable=False
        ),
        sa.UniqueConstraint("tenant_id", "usuario_id", "alerta_id"),
    )
    for table in ("ifood_alertas", "ifood_alertas_leituras"):
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    op.drop_table("ifood_alertas_leituras")
    op.drop_table("ifood_alertas")
