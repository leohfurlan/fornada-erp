from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

from domain.producao.state_machine import STATUS_VALIDOS


class CriarOrdemProducaoRequest(BaseModel):
    receita_id: UUID
    qtd_planejada: Decimal
    data_prevista: date | None = None
    pedido_id: UUID | None = None
    observacoes: str | None = None

    @field_validator("qtd_planejada")
    @classmethod
    def positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantidade planejada deve ser maior que zero")
        return v


class AtualizarOrdemProducaoRequest(BaseModel):
    receita_id: UUID | None = None
    qtd_planejada: Decimal | None = None
    data_prevista: date | None = None
    pedido_id: UUID | None = None
    observacoes: str | None = None


class MudarStatusOPRequest(BaseModel):
    status: str
    # Obrigatório quando status='finalizada' (apontamento).
    qtd_produzida: Decimal | None = None

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: str) -> str:
        if v not in STATUS_VALIDOS:
            raise ValueError(f"Status deve ser um de: {', '.join(sorted(STATUS_VALIDOS))}")
        return v

    @field_validator("qtd_produzida")
    @classmethod
    def qtd_nao_negativa(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("Quantidade produzida não pode ser negativa")
        return v


class OrdemProducaoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    numero: int
    receita_id: UUID
    nome_receita: str
    # Rendimento da receita (qtd de unidades finais por execução / "fornada").
    # Usado pra UI calcular "1 fornada × 20 = 20 brownies" sem refetch da receita.
    receita_rendimento: Decimal
    receita_rendimento_unidade: str
    pedido_id: UUID | None
    pedido_numero: int | None
    # qtd_planejada é em "fornadas/execuções da receita" (não em unidades finais).
    # Ingredientes consumidos = receita.ingredientes × qtd_planejada.
    qtd_planejada: Decimal
    # qtd_produzida é em UNIDADES FINAIS reais que saíram (não em fornadas).
    # Estoque PA recebe este valor. Default sugerido no apontamento =
    # qtd_planejada × receita_rendimento.
    qtd_produzida: Decimal | None
    status: str
    data_prevista: date | None
    observacoes: str | None
    created_at: datetime
    updated_at: datetime
    # Sugestão para a UI.
    proximas_transicoes: list[str]

    model_config = {"from_attributes": True}
