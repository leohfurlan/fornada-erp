"""Contrato de montagem por unidade; não substitui o motor de custos/estoque."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PassoMontagem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    descricao: str = Field(min_length=1, max_length=300)
    tipo: Literal["componente", "ingrediente", "embalagem", "acabamento"]
    quantidade: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    quantidade_minima: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    quantidade_maxima: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    unidade: Literal["g", "kg", "ml", "l", "un"]
    especificacao: str = Field(default="", max_length=500)
    instrucao: str = Field(default="", max_length=1000)
    receita_base_id: UUID | None = None
    ingrediente_id: UUID | None = None

    @model_validator(mode="after")
    def validar_faixa(self) -> "PassoMontagem":
        """Faixa deve ser completa e conter a quantidade nominal explícita."""
        if self.receita_base_id and self.ingrediente_id:
            raise ValueError("Selecione uma receita-base ou um material, não os dois")
        if self.receita_base_id and self.tipo != "componente":
            raise ValueError("Receita-base deve ser uma etapa do tipo componente")
        if (self.quantidade_minima is None) != (self.quantidade_maxima is None):
            raise ValueError("Informe os dois limites da faixa de quantidade")
        if self.quantidade_minima is not None:
            if not self.quantidade_minima <= self.quantidade <= self.quantidade_maxima:
                raise ValueError("A quantidade nominal deve estar dentro da faixa")
        return self


class FichaTecnicaInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    descricao_produto: str = Field(min_length=1, max_length=2000)
    especificacao_final: str = Field(default="", max_length=1000)
    passos: list[PassoMontagem] = Field(min_length=1, max_length=100)
    revisao: int = Field(ge=0)
    composicao_ativa: bool = False

    @model_validator(mode="after")
    def validar_vinculos(self) -> "FichaTecnicaInput":
        if self.composicao_ativa and any(not (p.receita_base_id or p.ingrediente_id) for p in self.passos):
            raise ValueError("Vincule cada etapa a uma receita-base ou material para calcular a composição")
        return self


class FichaTecnicaResponse(BaseModel):
    descricao_produto: str = ""
    especificacao_final: str = ""
    passos: list[PassoMontagem] = Field(default_factory=list)
    revisao: int = 0
    composicao_ativa: bool = False


class ConsumoComponente(BaseModel):
    tipo: str
    id: UUID
    nome: str
    unidade: str
    quantidade_por_fornada: Decimal
