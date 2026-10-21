"""Durable conversational purchase draft."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "b208d193ca01"
down_revision = "a85c10b7d302"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("central_compras", sa.Column("dialogo", JSONB(), nullable=True))


def downgrade():
    op.drop_column("central_compras", "dialogo")
