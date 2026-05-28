from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


class EtapaInput(BaseModel):
    nome: str
    duracao_minutos: int
    tipo_mao_obra: str = "direta"
    ordem: int = 0

    @field_validator("tipo_mao_obra")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ("direta", "indireta"):
            raise ValueError("tipo_mao_obra deve ser 'direta' ou 'indireta'")
        return v

    @field_validator("duracao_minutos")
    @classmethod
    def positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Duração deve ser maior que zero")
        return v


class IngredienteInput(BaseModel):
    ingrediente_id: UUID
    quantidade: Decimal
    unidade: str

    @field_validator("quantidade")
    @classmethod
    def positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v


class CriarReceitaRequest(BaseModel):
    nome: str
    categoria: str
    rendimento: Decimal
    rendimento_unidade: str
    margem_desejada: Decimal = Decimal("0.30")
    modo_preparo: str | None = None
    ingredientes: list[IngredienteInput]
    etapas: list[EtapaInput]

    @field_validator("rendimento")
    @classmethod
    def positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Rendimento deve ser maior que zero")
        return v

    @field_validator("margem_desejada")
    @classmethod
    def margem_valida(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v < Decimal("1")):
            raise ValueError("Margem deve estar entre 0% e 99%")
        return v


class AtualizarReceitaRequest(BaseModel):
    nome: str | None = None
    categoria: str | None = None
    rendimento: Decimal | None = None
    rendimento_unidade: str | None = None
    margem_desejada: Decimal | None = None
    modo_preparo: str | None = None
    ingredientes: list[IngredienteInput] | None = None
    etapas: list[EtapaInput] | None = None


class EtapaResponse(BaseModel):
    id: UUID
    nome: str
    duracao_minutos: int
    tipo_mao_obra: str
    ordem: int

    model_config = {"from_attributes": True}


class IngredienteReceitaResponse(BaseModel):
    id: UUID
    ingrediente_id: UUID
    nome_ingrediente: str
    quantidade: Decimal
    unidade: str
    custo_total: Decimal

    model_config = {"from_attributes": True}


class CustoDetalhadoResponse(BaseModel):
    custo_ingredientes: Decimal
    custo_operacional: Decimal
    custo_mao_obra_direta: Decimal
    custo_total: Decimal
    custo_por_unidade: Decimal
    preco_minimo: Decimal
    preco_recomendado: Decimal
    tempo_total_minutos: int
    tempo_ativo_minutos: int


class ReceitaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nome: str
    categoria: str
    rendimento: Decimal
    rendimento_unidade: str
    margem_desejada: Decimal
    modo_preparo: str | None
    foto_url: str | None
    created_at: datetime
    updated_at: datetime
    ingredientes: list[IngredienteReceitaResponse]
    etapas: list[EtapaResponse]
    custo: CustoDetalhadoResponse | None = None

    model_config = {"from_attributes": True}


class ReceitaResumoResponse(BaseModel):
    id: UUID
    nome: str
    categoria: str
    rendimento: Decimal
    rendimento_unidade: str
    custo_por_unidade: Decimal | None = None
    preco_recomendado: Decimal | None = None

    model_config = {"from_attributes": True}
