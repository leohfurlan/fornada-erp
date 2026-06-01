from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

CANAIS_VALIDOS: frozenset[str] = frozenset(
    {"loja_fisica", "whatsapp", "ifood", "instagram", "outro"}
)


class VendaItemRequest(BaseModel):
    receita_id: UUID
    quantidade: Decimal
    preco_unitario: Decimal
    observacoes: str | None = None

    @field_validator("quantidade", "preco_unitario")
    @classmethod
    def positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class CriarVendaRequest(BaseModel):
    canal: str
    cliente_id: UUID | None = None
    data_venda: datetime | None = None
    observacoes: str | None = None
    itens: list[VendaItemRequest]

    @field_validator("canal")
    @classmethod
    def canal_valido(cls, v: str) -> str:
        if v not in CANAIS_VALIDOS:
            raise ValueError(f"Canal deve ser um de: {', '.join(sorted(CANAIS_VALIDOS))}")
        return v

    @field_validator("itens")
    @classmethod
    def pelo_menos_um(cls, v: list[VendaItemRequest]) -> list[VendaItemRequest]:
        if not v:
            raise ValueError("Venda precisa de pelo menos um item")
        return v


class VendaItemResponse(BaseModel):
    id: UUID
    receita_id: UUID
    nome_receita: str
    quantidade: Decimal
    preco_unitario: Decimal
    subtotal: Decimal
    observacoes: str | None

    model_config = {"from_attributes": True}


class VendaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    numero: int
    cliente_id: UUID | None
    cliente_nome: str | None
    canal: str
    data_venda: datetime
    valor_total: Decimal
    observacoes: str | None
    created_at: datetime
    itens: list[VendaItemResponse]

    model_config = {"from_attributes": True}
