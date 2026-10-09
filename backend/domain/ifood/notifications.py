"""Aviso de recebimento separado de qualquer comando comercial do pedido."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class Delivery:
    id: UUID
    order_id: UUID
    number: str
    total: Decimal
    shop: str
    is_test: bool
    attempts: int


class NotificationStore(Protocol):
    async def claim(self) -> Delivery | None: ...
    async def finish(self, delivery: Delivery, state: str, error: str | None = None) -> None: ...


class NotificationSender(Protocol):
    async def send(self, phone: str, message: str) -> None: ...


class DeliveryFailure(Exception):
    def __init__(self, state: str, message: str) -> None:
        self.state, self.message = state, message


def message_for(delivery: Delivery, frontend_url: str) -> str:
    amount = f"{delivery.total:.2f}".replace(".", ",")
    shop = delivery.shop.replace("\n", " ").replace("\r", " ")[:200]
    return (
        f"Fornada — novo pedido iFood{' (teste)' if delivery.is_test else ''}\n"
        f"Pedido #{delivery.number}\nLoja: {shop}\nTotal: R$ {amount}\n"
        f"{frontend_url.rstrip('/')}/configuracoes/integracoes/ifood#pedido-{delivery.order_id}"
    )


class NotificationService:
    def __init__(
        self, store: NotificationStore, sender: NotificationSender, phone: str, frontend_url: str
    ) -> None:
        self.store, self.sender = store, sender
        self.phone, self.frontend_url = phone, frontend_url

    async def deliver_one(self) -> None:
        delivery = await self.store.claim()
        if delivery is None:
            return
        try:
            await self.sender.send(self.phone, message_for(delivery, self.frontend_url))
        except DeliveryFailure as exc:
            state = "erro" if exc.state == "pendente" and delivery.attempts >= 5 else exc.state
            await self.store.finish(delivery, state, exc.message)
        except Exception:
            # Não sabemos se o transporte aceitou. Evita reenvio cego após resposta perdida.
            await self.store.finish(delivery, "incerto", "Resposta de envio não confirmada.")
        else:
            await self.store.finish(delivery, "enviado")
