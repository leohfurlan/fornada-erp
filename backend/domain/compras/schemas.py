from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

from domain.estoque.schemas import IngredienteResponse, TIPOS_VALIDOS


class ItemCompraSugerido(BaseModel):
    """Item extraído do cupom já enriquecido com a sugestão de match."""

    descricao: str
    quantidade: Decimal
    unidade: str
    preco_unitario: Decimal
    preco_total: Decimal
    # Sugestão de vínculo com ingrediente existente
    ingrediente_id: UUID | None
    nome_match: str | None
    score: float
    # Para itens sem match: tipo e unidade já normalizados para facilitar o cadastro
    tipo_sugerido: str
    unidade_sugerida: str


class OcrComprasResponse(BaseModel):
    """Resposta do processamento de OCR de um cupom."""

    itens: list[ItemCompraSugerido]
    total: Decimal | None
    estabelecimento: str | None
    fonte: str  # gemma4 | mock
    confianca: float


class ItemConfirmado(BaseModel):
    """Item revisado pela usuária, pronto para virar entrada de estoque."""

    ingrediente_id: UUID | None = None  # preenchido quando vincula a existente
    criar_novo: bool = False
    nome: str
    tipo: str = "ingrediente"
    unidade: str
    quantidade: Decimal
    custo_unitario: Decimal

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_VALIDOS:
            raise ValueError(f"tipo deve ser um de: {', '.join(sorted(TIPOS_VALIDOS))}")
        return v

    @field_validator("quantidade", "custo_unitario")
    @classmethod
    def positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class ConfirmarCompraRequest(BaseModel):
    """Lista de itens confirmados de uma compra para dar entrada no estoque."""

    itens: list[ItemConfirmado]
    estabelecimento: str | None = None

    @field_validator("itens")
    @classmethod
    def nao_vazia(cls, v: list[ItemConfirmado]) -> list[ItemConfirmado]:
        if not v:
            raise ValueError("Informe ao menos um item para confirmar a compra.")
        return v


class ConfirmarCompraResponse(BaseModel):
    """Resumo do que foi gravado após confirmar a compra."""

    ingredientes_criados: int
    ingredientes_atualizados: int
    itens: list[IngredienteResponse]


class ItemListaCompras(BaseModel):
    """Ingrediente que precisa de recompra (saldo no/abaixo do mínimo)."""

    ingrediente_id: UUID
    nome: str
    unidade: str
    saldo: Decimal
    estoque_minimo: Decimal
    status_estoque: str  # baixo | critico | zerado
    quantidade_sugerida: Decimal
    custo_estimado: Decimal


class ListaComprasResponse(BaseModel):
    """Lista consolidada de reposição com custo total estimado."""

    itens: list[ItemListaCompras]
    custo_total_estimado: Decimal
