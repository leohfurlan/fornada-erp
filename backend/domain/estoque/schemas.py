from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

TIPOS_VALIDOS = {"ingrediente", "embalagem", "insumo", "descartavel", "outro"}


class CriarIngredienteRequest(BaseModel):
    nome: str
    tipo: str = "ingrediente"
    unidade: str
    estoque_minimo: Decimal = Decimal("0")
    estoque_inicial: Decimal = Decimal("0")
    custo_inicial: Decimal = Decimal("0")

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_VALIDOS:
            raise ValueError(f"tipo deve ser um de: {', '.join(sorted(TIPOS_VALIDOS))}")
        return v

    @field_validator("estoque_minimo", "estoque_inicial", "custo_inicial")
    @classmethod
    def nao_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Valor não pode ser negativo")
        return v


class AtualizarIngredienteRequest(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    unidade: str | None = None
    estoque_minimo: Decimal | None = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str | None) -> str | None:
        if v is not None and v not in TIPOS_VALIDOS:
            raise ValueError(f"tipo deve ser um de: {', '.join(sorted(TIPOS_VALIDOS))}")
        return v


class EntradaEstoqueRequest(BaseModel):
    ingrediente_id: UUID
    quantidade: Decimal
    custo_unitario: Decimal
    origem: str = "compra"

    @field_validator("quantidade", "custo_unitario")
    @classmethod
    def positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class IngredienteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    codigo: int
    tipo: str
    nome: str
    unidade: str
    estoque_atual: Decimal
    quantidade_reservada: Decimal
    saldo: Decimal  # estoque_atual - quantidade_reservada
    estoque_minimo: Decimal
    custo_medio: Decimal
    data_custo_atualizado: datetime | None
    status_estoque: str  # ok | baixo | critico | zerado

    model_config = {"from_attributes": True}


class MovimentacaoResponse(BaseModel):
    id: UUID
    ingrediente_id: UUID
    tipo: str
    quantidade: Decimal
    custo_unitario: Decimal
    origem: str
    created_at: datetime

    model_config = {"from_attributes": True}
