"""Contratos sanitizados: nenhum dado do consumidor é armazenado no monitor."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    merchantId: UUID
    orderId: UUID | None = None
    code: str = Field(max_length=80)
    fullCode: str | None = Field(default=None, max_length=80)
    createdAt: AwareDatetime


class Merchant(BaseModel):
    id: UUID
    name: str


class OrderOption(BaseModel):
    id: str | None = None
    uniqueId: str | None = None
    externalCode: str | None = None
    name: str
    quantity: Decimal = Field(ge=0)
    unitPrice: Decimal | None = None
    price: Decimal | None = None
    totalPrice: Decimal | None = None
    options: list["OrderOption"] = Field(default_factory=list)


class OrderItem(OrderOption):
    unit: str | None = None
    optionsPrice: Decimal | None = None


class OrderTotal(BaseModel):
    subTotal: Decimal
    deliveryFee: Decimal
    benefits: Decimal = Decimal("0")
    additionalFees: Decimal = Decimal("0")
    orderAmount: Decimal


class ObservedOrder(BaseModel):
    """Campos necessários à prova de recepção, sem customer, endereço ou documentos."""

    id: UUID
    displayId: str
    merchant: Merchant
    isTest: bool
    createdAt: AwareDatetime
    orderType: str
    orderTiming: str
    category: str
    salesChannel: str
    total: OrderTotal
    items: list[OrderItem]


class OrderView(BaseModel):
    id: UUID
    ultimo_evento: str
    evento_em: datetime
    snapshot: ObservedOrder
    aviso_whatsapp: str | None = None


class EventView(BaseModel):
    event_id: UUID
    order_id: UUID | None
    codigo: str
    ocorrido_em: datetime
    ack_em: datetime | None
    processado_em: datetime | None
    erro: str | None

    model_config = ConfigDict(from_attributes=True)


class MonitorView(BaseModel):
    habilitado: bool
    intervalo_segundos: int
    loja_nome: str | None = None
    merchant_id: UUID | None = None
    ultima_consulta: datetime | None = None
    ultima_recepcao: datetime | None = None
    erro: str | None = None
    eventos_pendentes: int = 0
    pedidos: list[OrderView] = Field(default_factory=list)
    eventos: list[EventView] = Field(default_factory=list)
    alertas_habilitados: bool = False
    whatsapp_habilitado: bool = False
    whatsapp_final: str | None = None


class AlertView(BaseModel):
    id: UUID
    order_id: UUID
    numero: str
    total: Decimal
    is_test: bool
    recebido_em: datetime
    whatsapp_estado: str


class AlertFeed(BaseModel):
    habilitado: bool = False
    alertas: list[AlertView] = Field(default_factory=list)
