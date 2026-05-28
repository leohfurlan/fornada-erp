from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


# -------- Etapas padrão --------

class CriarEtapaPadraoRequest(BaseModel):
    nome: str
    tipo_mao_obra: str = "direta"
    duracao_minutos_default: int = 30

    @field_validator("tipo_mao_obra")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ("direta", "indireta"):
            raise ValueError("tipo_mao_obra deve ser 'direta' ou 'indireta'")
        return v

    @field_validator("duracao_minutos_default")
    @classmethod
    def positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Duração deve ser maior que zero")
        return v


class AtualizarEtapaPadraoRequest(BaseModel):
    nome: str | None = None
    tipo_mao_obra: str | None = None
    duracao_minutos_default: int | None = None


class EtapaPadraoResponse(BaseModel):
    id: UUID
    nome: str
    tipo_mao_obra: str
    duracao_minutos_default: int

    model_config = {"from_attributes": True}


# -------- Configuração de custo operacional + valor/hora --------

class ConfiguracaoCustoRequest(BaseModel):
    custo_operacional_mensal: Decimal
    horas_mensais: Decimal
    valor_hora: Decimal

    @field_validator("custo_operacional_mensal", "valor_hora")
    @classmethod
    def nao_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Valor não pode ser negativo")
        return v

    @field_validator("horas_mensais")
    @classmethod
    def horas_positivas(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Horas mensais deve ser maior que zero")
        return v


class ConfiguracaoCustoResponse(BaseModel):
    custo_operacional_mensal: Decimal
    horas_mensais: Decimal
    valor_hora: Decimal
    custo_por_hora: Decimal
