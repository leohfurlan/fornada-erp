from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


class EstoquePAResponse(BaseModel):
    receita_id: UUID
    nome_receita: str
    qtd_disponivel: Decimal
    qtd_minima: Decimal
    status: str  # ok | baixo | zerado

    model_config = {"from_attributes": True}


class AtualizarEstoquePARequest(BaseModel):
    qtd_minima: Decimal

    @field_validator("qtd_minima")
    @classmethod
    def nao_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Quantidade mínima não pode ser negativa")
        return v


class MovimentacaoEstoquePAResponse(BaseModel):
    id: UUID
    receita_id: UUID
    tipo: str
    quantidade: Decimal
    origem: str
    created_at: datetime

    model_config = {"from_attributes": True}
