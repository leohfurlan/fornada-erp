from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

from domain.pedidos.state_machine import STATUS_VALIDOS


# --------- Clientes ---------


class CriarClienteRequest(BaseModel):
    nome: str
    telefone: str | None = None
    observacoes: str | None = None

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Nome do cliente é obrigatório")
        return v.strip()


class AtualizarClienteRequest(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    observacoes: str | None = None


class ClienteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nome: str
    telefone: str | None
    observacoes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --------- Pedidos ---------


class PedidoItemRequest(BaseModel):
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


class PedidoItemResponse(BaseModel):
    id: UUID
    receita_id: UUID
    nome_receita: str
    quantidade: Decimal
    preco_unitario: Decimal
    subtotal: Decimal
    observacoes: str | None

    model_config = {"from_attributes": True}


class CriarPedidoRequest(BaseModel):
    cliente_id: UUID | None = None
    data_entrega: date | None = None
    observacoes: str | None = None
    foto_referencia_url: str | None = None
    itens: list[PedidoItemRequest]

    @field_validator("itens")
    @classmethod
    def pelo_menos_um_item(cls, v: list[PedidoItemRequest]) -> list[PedidoItemRequest]:
        if not v:
            raise ValueError("Pedido precisa de pelo menos um item")
        return v


class AtualizarPedidoRequest(BaseModel):
    cliente_id: UUID | None = None
    data_entrega: date | None = None
    observacoes: str | None = None
    foto_referencia_url: str | None = None
    itens: list[PedidoItemRequest] | None = None


class MudarStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: str) -> str:
        if v not in STATUS_VALIDOS:
            raise ValueError(f"Status deve ser um de: {', '.join(sorted(STATUS_VALIDOS))}")
        return v


class PedidoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    numero: int
    cliente_id: UUID | None
    cliente_nome: str | None
    status: str
    data_entrega: date | None
    valor_total: Decimal
    observacoes: str | None
    foto_referencia_url: str | None
    created_at: datetime
    updated_at: datetime
    itens: list[PedidoItemResponse]
    # Status que esse pedido pode transicionar agora (sugestão para a UI).
    proximas_transicoes: list[str]

    model_config = {"from_attributes": True}
