"""Contratos do catálogo, revisão de compras e reconhecimento."""

from datetime import date, datetime
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

from domain.compras.identificadores import validar_cnpj, validar_gtin
from domain.compras.schemas import ConfirmarCompraResponse
from domain.estoque.schemas import TIPOS_VALIDOS

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Quantidade = Annotated[Decimal, Field(gt=0, max_digits=16, decimal_places=8)]
Valor = Annotated[Decimal, Field(gt=0, max_digits=16, decimal_places=8)]
Moeda = Annotated[Decimal, Field(gt=0, max_digits=16, decimal_places=2)]


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProdutoDados(Contrato):
    nome: Texto
    marca: Texto
    fabricante: Texto | None = None
    variante: Texto | None = None
    conteudo_embalagem: Quantidade
    unidade_conteudo: str = Field(min_length=1, max_length=40)
    fator_para_principal: Quantidade | None = None
    gtin: str | None = None

    _gtin = field_validator("gtin")(validar_gtin)

    @field_validator("unidade_conteudo")
    @classmethod
    def unidade_normalizada(cls, value: str) -> str:
        return value.lower().strip()


class ProdutoCriar(ProdutoDados):
    ingrediente_id: UUID
    aprovado: bool = False
    fornecedores_aprovados: list[UUID] = Field(default_factory=list, max_length=200)


class ProdutoEditar(Contrato):
    revisao: int = Field(ge=1)
    nome: Texto | None = None
    marca: Texto | None = None
    fabricante: Texto | None = None
    variante: Texto | None = None
    conteudo_embalagem: Quantidade | None = None
    unidade_conteudo: str | None = Field(default=None, min_length=1, max_length=40)
    fator_para_principal: Quantidade | None = None
    gtin: str | None = None
    aprovado: bool | None = None
    fornecedores_aprovados: list[UUID] | None = Field(default=None, max_length=200)
    _gtin = field_validator("gtin")(validar_gtin)

    @model_validator(mode="after")
    def campos_obrigatorios(self):
        for campo in (
            "nome",
            "marca",
            "conteudo_embalagem",
            "unidade_conteudo",
            "aprovado",
            "fornecedores_aprovados",
        ):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        return self


class ProdutoResponse(ProdutoCriar):
    id: UUID
    tenant_id: UUID
    revisao: int
    created_at: datetime
    updated_at: datetime


class FornecedorCriar(Contrato):
    nome: Texto
    cnpj: str | None = None
    _cnpj = field_validator("cnpj")(validar_cnpj)


class FornecedorEditar(Contrato):
    revisao: int = Field(ge=1)
    nome: Texto | None = None
    cnpj: str | None = None
    _cnpj = field_validator("cnpj")(validar_cnpj)

    @model_validator(mode="after")
    def nome_obrigatorio(self):
        if "nome" in self.model_fields_set and self.nome is None:
            raise ValueError("nome não pode ser nulo.")
        return self


class FornecedorResponse(FornecedorCriar):
    id: UUID
    revisao: int
    created_at: datetime


class PaginaProdutos(BaseModel):
    itens: list[ProdutoResponse]
    total: int


class PaginaFornecedores(BaseModel):
    itens: list[FornecedorResponse]
    total: int


class VinculoConflito(Contrato):
    id: UUID
    revisao: int = Field(ge=1)


class VinculoEditar(Contrato):
    revisao: int = Field(ge=1)
    produto_id: UUID
    produto_revisao: int = Field(ge=1)


class VinculoResponse(BaseModel):
    id: UUID
    fornecedor_id: UUID
    produto_id: UUID
    tipo: str
    valor_original: str
    valor_normalizado: str
    revisao: int
    produto_revisao_confirmada: int
    ativo: bool
    model_config = ConfigDict(from_attributes=True)


class PaginaVinculos(BaseModel):
    itens: list[VinculoResponse]
    total: int


class ItemRevisado(Contrato):
    ingrediente_id: UUID | None = None
    criar_novo: bool = False
    nome: Texto = "Material"
    tipo: str = "ingrediente"
    unidade_principal: str | None = Field(default=None, min_length=1, max_length=40)
    descricao_original: str = Field(min_length=1, max_length=500)
    quantidade: Quantidade
    unidade: str = Field(min_length=1, max_length=40)
    custo_unitario: Valor
    desconto_item: Decimal = Field(default=Decimal("0"), ge=0, max_digits=16, decimal_places=2)
    preco_total: Moeda
    produto_id: UUID | None = None
    produto_revisao: int | None = Field(default=None, ge=1)
    produto_novo: ProdutoDados | None = None
    codigo_loja: str | None = Field(default=None, min_length=1, max_length=100)
    gtin_confirmado: str | None = None
    aprovar_produto: bool = False
    aprovar_fornecedor: bool = False
    aceitar_excecao: bool = False
    guardar_vinculo: bool = False
    conflito_vinculo: VinculoConflito | None = None

    _gtin = field_validator("gtin_confirmado")(validar_gtin)

    @model_validator(mode="after")
    def modos_validos(self) -> "ItemRevisado":
        if self.tipo not in TIPOS_VALIDOS:
            raise ValueError("Tipo de material inválido.")
        if self.criar_novo == (self.ingrediente_id is not None):
            raise ValueError("Escolha um material existente ou crie um novo.")
        if self.produto_id and (self.criar_novo or self.produto_novo or not self.produto_revisao):
            raise ValueError("Escolha produto existente com revisão ou cadastre outro.")
        if self.guardar_vinculo and self.aceitar_excecao:
            raise ValueError("Compra excepcional não pode guardar uma aprovação permanente.")
        return self


class CompraRevisada(Contrato):
    itens: list[ItemRevisado] = Field(min_length=1, max_length=100)
    estabelecimento: Texto | None = None
    data_compra: date | None = None
    total_nota: Moeda | None = None
    fornecedor_id: UUID | None = None
    fornecedor_novo: FornecedorCriar | None = None
    identidade_nota: str | None = Field(default=None, pattern=r"^\d{44}$")
    identidade_confirmada: bool = False
    confirmar_duplicidade: bool = False
    origem: Literal["web_manual", "web_ocr"] = "web_manual"

    @model_validator(mode="after")
    def contexto_valido(self) -> "CompraRevisada":
        if self.fornecedor_id and self.fornecedor_novo:
            raise ValueError("Escolha uma loja existente ou cadastre uma nova.")
        if self.identidade_confirmada and not self.identidade_nota:
            raise ValueError("Informe a identidade da nota para confirmá-la.")
        return self


class ItemPrevia(BaseModel):
    indice: int
    ingrediente_id: UUID | None
    nome_material: str
    produto_id: UUID | None
    quantidade_principal: Decimal
    unidade_principal: str
    fator_aplicado: Decimal
    custo_normalizado: Decimal
    preco_total: Decimal
    pendencias: list[str]


class Duplicidade(BaseModel):
    compra_id: UUID
    data_registro: datetime


class PreviaCompra(BaseModel):
    itens: list[ItemPrevia]
    total_selecionado: Decimal
    duplicidade: list[Duplicidade]
    pode_confirmar: bool


class ResultadoCompra(ConfirmarCompraResponse):
    compra_id: UUID
    data_compra: date | None
    fornecedor_id: UUID | None
    data_registro: datetime
    total_selecionado: Decimal


class ItemObservado(Contrato):
    indice: int = Field(ge=0)
    descricao: str = Field(min_length=1, max_length=500)
    quantidade: Decimal | None = None
    unidade: str | None = None
    preco_unitario: Decimal | None = None
    preco_total: Decimal | None = None
    desconto_item: Decimal | None = None
    marca_observada: str | None = None
    fabricante_observado: str | None = None
    variante_observada: str | None = None
    conteudo_observado: Decimal | None = None
    unidade_conteudo_observada: str | None = None
    codigo_loja: str | None = None
    gtin: str | None = None
    gtin_confirmado: bool = False
    _gtin = field_validator("gtin")(validar_gtin)


class Candidato(BaseModel):
    produto_id: UUID
    produto_revisao: int
    ingrediente_id: UUID
    nome_produto: str
    nome_material: str


class ItemLido(ItemObservado):
    ingrediente_id: UUID | None = None
    nome_match: str | None = None
    produto_id: UUID | None = None
    produto_revisao: int | None = None
    reconhecimento: str = "nenhum"
    score: float = 0
    explicacao: str = "Escolha o material e confira o produto."
    pendencias: list[str] = Field(default_factory=list)
    candidatos: list[Candidato] = Field(default_factory=list)
    vinculo_id: UUID | None = None
    vinculo_revisao: int | None = None
    tipo_sugerido: str = "ingrediente"
    unidade_sugerida: str = "un"


class ReconhecerRequest(Contrato):
    fornecedor_id: UUID | None = None
    itens: list[ItemObservado] = Field(min_length=1, max_length=100)


class ReconhecerResponse(BaseModel):
    itens: list[ItemLido]


class LeituraCompra(ReconhecerResponse):
    total_nota: Decimal | None
    estabelecimento: str | None
    data_compra: date | None
    data_original: str | None
    fornecedor_id: UUID | None
    fornecedores_candidatos: list[FornecedorResponse]
    cnpj_observado: str | None = None
    identidade_nota: str | None = None
    identidade_confirmada: bool = False
    fonte: str
    confianca: float
    aviso_mock: bool


class CompraResumo(BaseModel):
    id: UUID
    data_compra: date | None
    data_registro: datetime
    estabelecimento_original: str | None
    fornecedor_id: UUID | None
    fornecedor_nome_snapshot: str | None
    origem: str
    total_selecionado: Decimal
    metadados_completos: bool
    quantidade_itens: int


class CompraItemResponse(BaseModel):
    id: UUID
    ingrediente_id: UUID
    produto_id: UUID | None
    movimentacao_id: UUID
    quantidade_principal: Decimal
    custo_normalizado: Decimal
    preco_total: Decimal
    snapshot: dict


class CompraDetalhada(CompraResumo):
    itens: list[CompraItemResponse]


class PaginaCompras(BaseModel):
    itens: list[CompraResumo]
    total: int
