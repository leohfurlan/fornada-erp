"""Compras pelo WhatsApp: nenhuma entrada de estoque antes da revisão explícita."""

import hashlib
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError as SchemaError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from domain.compras.matching import normalizar_unidade
from domain.compras.schemas import ConfirmarCompraRequest, ItemConfirmado
from domain.compras.service import ComprasService
from domain.exceptions import FornadaError
from domain.whatsapp.messages import (
    MENU,
    ONBOARDING,
    IncomingMessage,
    WhatsAppPort,
    manual_item,
    preview_text,
)
from domain.whatsapp.registration import register_chat
from infrastructure.database.models import Tenant, Usuario
from infrastructure.database.whatsapp_models import WhatsAppCompra, WhatsAppEvento


class WhatsAppService:
    def __init__(self, db: AsyncSession, adapter: WhatsAppPort, compras: ComprasService) -> None:
        self.db, self.adapter, self.compras = db, adapter, compras

    async def process(self, incoming: IncomingMessage) -> None:
        """Worker serializa remetentes; efeitos e resposta persistem na mesma transação."""
        key = hashlib.sha256(
            f"{settings.evolution_instance}:{incoming.phone}:{incoming.message_id}".encode()
        ).hexdigest()
        event = await self.db.scalar(select(WhatsAppEvento).where(WhatsAppEvento.chave == key))
        if not event:
            try:
                async with self.db.begin_nested():
                    response = await self.handle(incoming)
            except FornadaError as exc:
                response = exc.message
            except SchemaError:
                response = "Não foi possível concluir. Confira os dados e tente novamente."
            event = WhatsAppEvento(chave=key, resposta=response)
            self.db.add(event)
            await self.db.commit()
        if not event.enviado:
            await self.adapter.send_text(incoming.phone, event.resposta)
            event.enviado = True
            await self.db.commit()

    async def handle(self, incoming: IncomingMessage) -> str:
        # Identidade global do transporte. Dados de negócio usam sempre o tenant resolvido.
        user = await self.db.scalar(
            select(Usuario)
            .join(Tenant)
            .where(
                Usuario.telefone == "+" + incoming.phone,
                Usuario.ativo.is_(True),
                Usuario.deleted_at.is_(None),
                Tenant.ativo.is_(True),
                Tenant.deleted_at.is_(None),
            )
        )
        if not user:
            # Número de conta inativa não pode abrir um cadastro alternativo.
            existing = await self.db.scalar(
                select(Usuario.id).where(
                    Usuario.telefone == "+" + incoming.phone,
                )
            )
            if existing:
                return "Sua conta está indisponível. Entre em contato com o suporte."
            return await register_chat(self.db, incoming)
        text = incoming.text.strip()
        command = text.upper()
        if command in {"ONBOARDING", "COMEÇAR"}:
            return ONBOARDING
        if command in {"ENTRAR", "LOGIN"}:
            return f"Abra sua conta: {settings.frontend_url.rstrip('/')}/login"
        draft = await self.db.scalar(
            select(WhatsAppCompra)
            .where(
                WhatsAppCompra.tenant_id == user.tenant_id,
                WhatsAppCompra.usuario_id == user.id,
                WhatsAppCompra.telefone == incoming.phone,
                WhatsAppCompra.status == "pendente",
            )
            .order_by(WhatsAppCompra.created_at.desc())
            .with_for_update()
        )
        if draft and draft.expira_em <= datetime.now(UTC):
            draft.status = "expirada"
            draft = None
        if command == "CANCELAR":
            if draft:
                draft.status = "cancelada"
            return "Prévia descartada. Nenhuma entrada foi salva."
        if command == "CONFIRMAR":
            if not draft:
                return "Não há compra pendente. Envie COMPRAR para começar."
            await self.compras.confirmar(user.tenant_id, ConfirmarCompraRequest(itens=draft.itens))
            draft.status = "confirmada"
            return "Compra salva! Estoque e custos atualizados.\n" + MENU
        if command.startswith("CORRIGIR "):
            if not draft:
                return "Não há prévia pendente. Envie uma foto ou um ITEM."
            try:
                index, rest = text[9:].split(";", 1)
                position = int(index.strip()) - 1
                items = [ItemConfirmado.model_validate(item) for item in draft.itens]
                if not 0 <= position < len(items):
                    raise ValueError
                previous = items[position]
                replacement = manual_item("ITEM " + rest.strip())
                replacement.ingrediente_id = previous.ingrediente_id
                replacement.criar_novo = previous.criar_novo
                replacement.tipo = previous.tipo
                if previous.ingrediente_id and replacement.unidade != previous.unidade:
                    return "Mantenha a unidade do ingrediente vinculado ou cancele a prévia."
                items[position] = replacement
            except ValueError:
                return "Use: CORRIGIR 1; Açúcar; 2; kg; 5,90."
            draft.itens = [item.model_dump(mode="json") for item in items]
            return preview_text(items)
        if incoming.image or command.startswith("ITEM "):
            if draft:
                return "Existe uma prévia pendente. CONFIRMAR ou CANCELAR antes de outra compra."
            if incoming.image:
                content, mime = await self.adapter.image(incoming.raw)
                result = await self.compras.processar_ocr(user.tenant_id, content, mime)
                if result.fonte == "mock" or not result.itens or len(result.itens) > 30:
                    return "Não conseguimos extrair este cupom. Envie outra foto ou use ITEM."
                if any(
                    normalizar_unidade(item.unidade) != item.unidade_sugerida
                    or item.unidade_sugerida not in {"g", "kg", "ml", "l", "un"}
                    for item in result.itens
                ):
                    return (
                        "O cupom usa unidades diferentes do estoque. Para evitar uma entrada "
                        "incorreta, use ITEM com a quantidade e o custo na unidade correta."
                    )
                items = [
                    ItemConfirmado(
                        ingrediente_id=item.ingrediente_id,
                        criar_novo=item.ingrediente_id is None,
                        nome=item.nome_match or item.descricao,
                        tipo=item.tipo_sugerido,
                        unidade=item.unidade_sugerida,
                        quantidade=item.quantidade,
                        custo_unitario=item.preco_unitario,
                    )
                    for item in result.itens
                ]
            else:
                items = [manual_item(text)]
            self.db.add(
                WhatsAppCompra(
                    tenant_id=user.tenant_id,
                    usuario_id=user.id,
                    telefone=incoming.phone,
                    itens=[item.model_dump(mode="json") for item in items],
                    expira_em=datetime.now(UTC) + timedelta(hours=24),
                )
            )
            warnings = getattr(result, "avisos", []) if incoming.image else []
            return "\n".join(warnings + [preview_text(items)])
        if command == "COMPRAR":
            return "Envie uma foto nítida do cupom (JPG, PNG ou WebP, até 8 MB)."
        if command == "REVISAR" and draft:
            return preview_text([ItemConfirmado.model_validate(item) for item in draft.itens])
        return MENU
