"""API oficial: autenticação, leitura e ACK de transporte; nenhum comando de pedido."""

import time
from uuid import UUID

import httpx

from domain.ifood.errors import IfoodAPIError
from domain.ifood.schemas import EventEnvelope, ObservedOrder

BASE_URL = "https://merchant-api.ifood.com.br"


class IfoodClient:
    """Cliente reutilizado pelo processo para renovar token somente quando necessário."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        client_id: UUID,
        secret: str,
        merchant_id: UUID,
        expected_name: str,
    ) -> None:
        self.http = http
        self.client_id = client_id
        self._secret = secret
        self.merchant_id = merchant_id
        self.expected_name = expected_name
        self._token = ""
        self._expires = 0.0
        self._verified = False

    async def _authenticate(self) -> None:
        if self._token and time.monotonic() < self._expires:
            return
        try:
            response = await self.http.post(
                BASE_URL + "/authentication/v1.0/oauth/token",
                data={
                    "grantType": "client_credentials",
                    "clientId": str(self.client_id),
                    "clientSecret": self._secret,
                },
            )
        except httpx.HTTPError:
            raise IfoodAPIError() from None
        if response.status_code != 200:
            raise IfoodAPIError(response.status_code)
        try:
            data = response.json()
            token = data["accessToken"]
            lifetime = float(data["expiresIn"])
            if not isinstance(token, str) or not token or lifetime <= 0:
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise IfoodAPIError(502) from None
        self._token = token
        self._expires = time.monotonic() + max(0, lifetime - min(60, lifetime / 10))

    async def _request(
        self,
        method: str,
        path: str,
        accepted: tuple[int, ...],
        **kwargs: object,
    ) -> httpx.Response:
        extra_headers = kwargs.pop("headers", {})
        for attempt in range(2):
            await self._authenticate()
            headers = {"Authorization": f"Bearer {self._token}"}
            headers.update(extra_headers)
            try:
                response = await self.http.request(
                    method,
                    BASE_URL + path,
                    headers=headers,
                    **kwargs,
                )
            except httpx.HTTPError:
                raise IfoodAPIError() from None
            if response.status_code == 401 and attempt == 0:
                self._token = ""
                continue
            if response.status_code not in accepted:
                try:
                    delay = min(3600, max(30, int(response.headers.get("Retry-After", "30"))))
                except ValueError:
                    delay = 60
                raise IfoodAPIError(response.status_code, delay)
            if len(response.content) > 2 * 1024 * 1024:
                raise IfoodAPIError(413)
            return response
        raise IfoodAPIError(401)

    async def verify_merchant(self) -> None:
        """Confere identidade antes do polling, que gera presença da loja de teste."""
        if self._verified:
            return
        response = await self._request(
            "GET",
            f"/merchant/v1.0/merchants/{self.merchant_id}",
            (200,),
        )
        try:
            data = response.json()
            if data.get("id") != str(self.merchant_id) or data.get("name") != self.expected_name:
                raise ValueError
        except (ValueError, AttributeError):
            raise IfoodAPIError(403) from None
        self._verified = True

    async def poll(self) -> list[EventEnvelope]:
        await self.verify_merchant()
        response = await self._request(
            "GET",
            "/events/v1.0/events:polling",
            (200, 204),
            headers={"x-polling-merchants": str(self.merchant_id)},
            params={"categories": "FOOD"},
        )
        if response.status_code == 204:
            return []
        try:
            events = response.json()
            if not isinstance(events, list):
                raise ValueError
            parsed = [EventEnvelope.model_validate(item) for item in events]
            if any(event.merchantId != self.merchant_id for event in parsed):
                raise ValueError
            return parsed
        except (ValueError, TypeError):
            raise IfoodAPIError(502) from None

    async def acknowledge(self, ids: list[UUID]) -> None:
        if ids:
            await self._request(
                "POST",
                "/events/v1.0/events/acknowledgment",
                (200, 202),
                json=[{"id": str(event_id)} for event_id in dict.fromkeys(ids)],
            )

    async def order(self, order_id: UUID) -> ObservedOrder:
        response = await self._request("GET", f"/order/v1.0/orders/{order_id}", (200,))
        try:
            order = ObservedOrder.model_validate(response.json())
            if order.id != order_id or order.merchant.id != self.merchant_id or not order.isTest:
                raise ValueError
            return order
        except (ValueError, TypeError):
            raise IfoodAPIError(502) from None
