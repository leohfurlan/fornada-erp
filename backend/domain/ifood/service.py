"""Orquestra observação, sem chamar serviços de pedidos, vendas ou estoque."""

from typing import Protocol
from uuid import UUID

from domain.ifood.errors import IfoodAPIError
from domain.ifood.schemas import EventEnvelope, ObservedOrder


class EventRecord(Protocol):
    order_id: UUID | None
    codigo: str


class Store(Protocol):
    async def begin(self, name: str, interval: int) -> bool: ...
    async def save_events(self, events: list[EventEnvelope]) -> None: ...
    async def pending_ack(self) -> list[UUID]: ...
    async def mark_ack(self, ids: list[UUID]) -> None: ...
    async def pending(self) -> list[EventRecord]: ...
    async def cached_order(self, order_id: UUID) -> dict | None: ...
    async def complete(self, event: EventRecord, order: ObservedOrder | None) -> None: ...
    async def fail_event(self, event: EventRecord, status: int, delay: int) -> None: ...
    async def fail_poll(self, status: int, delay: int) -> None: ...


class Remote(Protocol):
    async def poll(self) -> list[EventEnvelope]: ...
    async def acknowledge(self, ids: list[UUID]) -> None: ...
    async def order(self, order_id: UUID) -> ObservedOrder: ...


class IfoodObservationService:
    def __init__(self, store: Store, remote: Remote, name: str, interval: int = 30) -> None:
        self.store = store
        self.remote = remote
        self.name = name
        self.interval = interval

    async def tick(self) -> None:
        """ACK confirma transporte; falha ao consultar pedido fica durável para retry."""
        if not await self.store.begin(self.name, self.interval):
            return
        try:
            events = await self.remote.poll()
            await self.store.save_events(events)
            ids = await self.store.pending_ack()
            if ids:
                await self.remote.acknowledge(ids)
                await self.store.mark_ack(ids)
        except IfoodAPIError as exc:
            await self.store.fail_poll(exc.status, exc.retry_after)
            # A inbox já persistida continua processável mesmo com erro de polling/ACK.
        for event in await self.store.pending():
            try:
                order = None
                if event.order_id:
                    cached = await self.store.cached_order(event.order_id)
                    if cached and event.codigo not in ("ORDER_PATCHED", "PATCHED"):
                        order = ObservedOrder.model_validate(cached)
                    else:
                        order = await self.remote.order(event.order_id)
                await self.store.complete(event, order)
            except IfoodAPIError as exc:
                await self.store.fail_event(event, exc.status, exc.retry_after)
                if exc.status in (401, 429) or exc.status >= 500:
                    await self.store.fail_poll(exc.status, exc.retry_after)
                    break
