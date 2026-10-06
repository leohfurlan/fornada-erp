"""taxas_precificacao (iFood/cartão) em configuracoes_custo

Revision ID: b1c2d3e4f5a6
Revises: 4d4eb7c39e35
Create Date: 2026-06-01 12:00:00.000000

NOTA: migration escrita à mão (ambiente Docker/DB indisponível para
`alembic revision --autogenerate`). Revise antes de aplicar com
`alembic upgrade head`. Apenas adiciona duas colunas com default 0,
então é compatível com linhas existentes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = '4d4eb7c39e35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'configuracoes_custo',
        sa.Column(
            'taxa_ifood',
            sa.Numeric(precision=5, scale=4),
            server_default='0',
            nullable=False,
        ),
    )
    op.add_column(
        'configuracoes_custo',
        sa.Column(
            'taxa_cartao',
            sa.Numeric(precision=5, scale=4),
            server_default='0',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('configuracoes_custo', 'taxa_cartao')
    op.drop_column('configuracoes_custo', 'taxa_ifood')
