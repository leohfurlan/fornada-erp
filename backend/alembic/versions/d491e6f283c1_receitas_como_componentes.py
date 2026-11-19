"""Allow recipes to be used as recipe ingredients.

Revision ID: d491e6f283c1
Revises: c7e5f2a901bd
Create Date: 2026-11-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d491e6f283c1"
down_revision: Union[str, None] = "c7e5f2a901bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "receita_ingredientes",
        "ingrediente_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "receita_ingredientes",
        sa.Column("receita_componente_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_receita_ingredientes_receita_componente_id_receitas",
        "receita_ingredientes",
        "receitas",
        ["receita_componente_id"],
        ["id"],
    )
    op.create_index(
        "ix_receita_ingredientes_receita_componente_id",
        "receita_ingredientes",
        ["receita_componente_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_receita_ingredientes_uma_origem",
        "receita_ingredientes",
        "(ingrediente_id IS NOT NULL AND receita_componente_id IS NULL) OR "
        "(ingrediente_id IS NULL AND receita_componente_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_receita_ingredientes_uma_origem", "receita_ingredientes", type_="check"
    )
    op.drop_index(
        "ix_receita_ingredientes_receita_componente_id",
        table_name="receita_ingredientes",
    )
    op.drop_constraint(
        "fk_receita_ingredientes_receita_componente_id_receitas",
        "receita_ingredientes",
        type_="foreignkey",
    )
    op.drop_column("receita_ingredientes", "receita_componente_id")
    op.alter_column(
        "receita_ingredientes",
        "ingrediente_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
