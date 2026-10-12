"""pwa_eventos

Revision ID: 2a86c837f345
Revises: f17d5b4e421d
Create Date: 2026-10-12 15:01:38.281172

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2a86c837f345"
down_revision: Union[str, None] = "f17d5b4e421d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pwa_eventos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("browser_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(32), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "usuario_id", "event_id", name="uq_pwa_evento"),
    )
    op.create_index("ix_pwa_eventos_tenant_id", "pwa_eventos", ["tenant_id"])
    op.create_index(
        "ix_pwa_usuario_tipo_data", "pwa_eventos", ["tenant_id", "usuario_id", "tipo", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_pwa_usuario_tipo_data", table_name="pwa_eventos")
    op.drop_index("ix_pwa_eventos_tenant_id", table_name="pwa_eventos")
    op.drop_table("pwa_eventos")
