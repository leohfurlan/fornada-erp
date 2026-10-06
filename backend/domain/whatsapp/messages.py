"""Comandos determinísticos e validação da identidade recebida pelo transporte."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from domain.compras.schemas import ItemConfirmado
from domain.exceptions import ValidationError

MENU = (
    "Como posso ajudar?\n"
    "COMPRAR — enviar foto do cupom\n"
    "ITEM nome; quantidade; unidade; custo unitário — compra manual\n"
    "CONFIRMAR — salvar a prévia revisada\n"
    "CANCELAR — descartar a prévia\n"
    "ONBOARDING — primeiros passos\n"
    "ENTRAR — abrir sua conta no aplicativo"
)
ONBOARDING = (
    "Vamos organizar sua confeitaria!\n"
    "1. Configure seu valor por hora e gastos da loja.\n"
    "2. Envie cupons para cadastrar ingredientes e embalagens.\n"
    "3. Cadastre suas receitas e confira os custos.\n"
    "4. Planeje a produção e registre pedidos e vendas.\n"
    "Envie COMPRAR para começar ou ENTRAR para abrir o aplicativo."
)


class WhatsAppPort(Protocol):
    async def send_text(self, phone: str, text: str) -> None: ...
    async def image(self, message: dict) -> tuple[bytes, str]: ...


@dataclass(frozen=True)
class IncomingMessage:
    phone: str
    message_id: str
    text: str
    image: bool
    raw: dict


def parse_message(payload: dict, instance: str) -> IncomingMessage | None:
    if payload.get("instance") != instance or payload.get("event") not in (
        "messages.upsert",
        "MESSAGES_UPSERT",
    ):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    key = data.get("key", {})
    if not isinstance(key, dict):
        return None
    jid = key.get("remoteJid", "")
    if key.get("fromMe") is not False or not isinstance(jid, str):
        return None
    # Ignora grupos, broadcast e LID: não deduz telefone a partir de identificadores opacos.
    if not re.fullmatch(r"[1-9][0-9]{7,14}@s\.whatsapp\.net", jid):
        return None
    message_id = key.get("id")
    if not isinstance(message_id, str) or not 1 <= len(message_id) <= 200:
        return None
    message = data.get("message", {})
    if not isinstance(message, dict):
        return None
    text = message.get("conversation") or message.get("extendedTextMessage", {}).get("text", "")
    return IncomingMessage(
        jid.split("@")[0], message_id, str(text)[:2000], "imageMessage" in message, data
    )


def manual_item(text: str) -> ItemConfirmado:
    try:
        nome, quantidade, unidade, custo = (part.strip() for part in text[5:].split(";"))
        if not nome or len(nome) > 200 or unidade not in {"g", "kg", "ml", "l", "un"}:
            raise ValueError
        return ItemConfirmado(
            criar_novo=True,
            nome=nome,
            unidade=unidade,
            quantidade=Decimal(quantidade.replace(",", ".")),
            custo_unitario=Decimal(custo.replace(",", ".")),
        )
    except (ValueError, InvalidOperation) as exc:
        raise ValidationError("Use: ITEM Açúcar; 2; kg; 5,90 (custo por kg).") from exc


def preview_text(items: list[ItemConfirmado]) -> str:
    lines = ["Revise antes de salvar:"]
    for index, item in enumerate(items, 1):
        total = item.quantidade * item.custo_unitario
        value = f"{total:.2f}".replace(".", ",")
        quantity = str(item.quantidade).replace(".", ",")
        target = "ingrediente existente" if item.ingrediente_id else "novo cadastro"
        lines.append(f"{index}. {item.nome}: {quantity} {item.unidade} — R$ {value} ({target})")
    lines.append(
        "CONFIRMAR para salvar; CANCELAR para descartar.\n"
        "Para corrigir: CORRIGIR número; nome; quantidade; unidade; custo unitário."
    )
    return "\n".join(lines)
