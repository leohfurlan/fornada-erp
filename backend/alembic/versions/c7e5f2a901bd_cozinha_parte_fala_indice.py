"""Persist current spoken chunk for kitchen station."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7e5f2a901bd"
down_revision: str | Sequence[str] | None = "a41e0d2f9c66"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cozinha_estacoes",
        sa.Column("parte_fala_indice", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("cozinha_estacoes", "parte_fala_indice")
