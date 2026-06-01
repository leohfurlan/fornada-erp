"""estoque_pa: unique (tenant_id, receita_id) ativo

Garante um único saldo de produto acabado por (tenant_id, receita_id)
considerando apenas registros não soft-deletados. Previne duplicatas
criadas por race em buscar_ou_criar.

Revision ID: a1b2c3d4e5f6
Revises: 5773d636139d
Create Date: 2026-06-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5773d636139d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ux_estoque_pa_tenant_receita_ativo',
        'estoque_produto_acabado',
        ['tenant_id', 'receita_id'],
        unique=True,
        postgresql_where='deleted_at IS NULL',
    )


def downgrade() -> None:
    op.drop_index(
        'ux_estoque_pa_tenant_receita_ativo',
        table_name='estoque_produto_acabado',
    )
