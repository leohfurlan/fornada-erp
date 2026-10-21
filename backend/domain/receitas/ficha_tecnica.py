"""Contrato de montagem por unidade; não substitui o motor de custos/estoque."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from domain.validation import field_error

TextoMarkdown = Annotated[str, StringConstraints(strip_whitespace=False)]


class PassoMontagem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    descricao: str = Field(min_length=1, max_length=300)
    tipo: Literal["componente", "ingrediente", "embalagem", "acabamento"]
    quantidade: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    quantidade_minima: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    quantidade_maxima: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    unidade: Literal["g", "kg", "ml", "l", "un"]
    especificacao: TextoMarkdown = Field(default="", max_length=500)
    instrucao: TextoMarkdown = Field(default="", max_length=1000)
    receita_base_id: UUID | None = None
    ingrediente_id: UUID | None = None

    @model_validator(mode="after")
    def validar_faixa(self) -> "PassoMontagem":
        """Faixa deve ser completa e conter a quantidade nominal explícita."""
        if self.receita_base_id and self.ingrediente_id:
            raise field_error(
                ("receita_base_id",), "Selecione uma receita-base ou um material, não os dois"
            )
        if self.receita_base_id and self.tipo != "componente":
            raise field_error(("tipo",), "Receita-base deve ser uma etapa do tipo componente")
        if (self.quantidade_minima is None) != (self.quantidade_maxima is None):
            campo = "quantidade_minima" if self.quantidade_minima is None else "quantidade_maxima"
            raise field_error((campo,), "Informe os dois limites da faixa de quantidade")
        if self.quantidade_minima is not None:
            if not self.quantidade_minima <= self.quantidade <= self.quantidade_maxima:
                raise field_error(
                    ("quantidade",), "A quantidade nominal deve estar dentro da faixa"
                )
        return self


class FichaTecnicaInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    descricao_produto: TextoMarkdown = Field(min_length=1, max_length=2000)
    especificacao_final: TextoMarkdown = Field(default="", max_length=1000)
    passos: list[PassoMontagem] = Field(min_length=1, max_length=100)
    revisao: int = Field(ge=0)
    composicao_ativa: bool = False

    @field_validator("descricao_produto")
    @classmethod
    def validar_descricao(cls, value: str) -> str:
        """Exige conteúdo sem remover indentação ou espaços do Markdown."""
        if not value.strip():
            raise ValueError("Informe a descrição do produto")
        return value

    @model_validator(mode="after")
    def validar_vinculos(self) -> "FichaTecnicaInput":
        if self.composicao_ativa:
            for index, passo in enumerate(self.passos):
                if not (passo.receita_base_id or passo.ingrediente_id):
                    raise field_error(
                        ("passos", index, "receita_base_id"),
                        "Vincule esta etapa a uma receita-base ou material "
                        "para calcular a composição",
                    )
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
