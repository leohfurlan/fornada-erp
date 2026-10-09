import httpx

from domain.ifood.notifications import DeliveryFailure
from infrastructure.whatsapp.evolution import EvolutionAdapter


class IfoodWhatsAppSender:
    async def send(self, phone: str, message: str) -> None:
        try:
            await EvolutionAdapter().send_text(phone, message)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            raise DeliveryFailure(
                "pendente", "Conexão indisponível; nova tentativa agendada."
            ) from None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            state = "pendente" if status == 429 else "erro" if 400 <= status < 500 else "incerto"
            raise DeliveryFailure(
                state, f"Envio WhatsApp não confirmado (HTTP {status})."
            ) from None
        except Exception:
            raise DeliveryFailure(
                "incerto", "Resposta de envio não confirmada; conferir no WhatsApp."
            ) from None
