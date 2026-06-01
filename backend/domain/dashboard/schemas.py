from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AlertaEstoque(BaseModel):
    ingrediente_id: UUID
    nome: str
    estoque_atual: Decimal
    estoque_minimo: Decimal
    unidade: str
    status: str  # "baixo" | "critico" | "zerado"


class DashboardResumoResponse(BaseModel):
    # Financeiro — semana atual (segunda a domingo)
    faturamento_semana: Decimal
    lucro_estimado_semana: Decimal | None  # None enquanto não integrarmos custo × vendas
    total_vendas_semana: int
    # Operacional
    pedidos_em_aberto: int  # status in ('orcamento', 'aprovado')
    ops_hoje: int  # data_prevista = hoje AND status in ('planejada', 'em_producao')
    ops_em_producao: int  # status = 'em_producao'
    # Estoque
    alertas_estoque: list[AlertaEstoque]  # status in (baixo, critico, zerado), max 5
    total_ingredientes_criticos: int  # status in ('critico', 'zerado')
