"""Fluxos em PostgreSQL isolado; transporte e OCR externos substituídos por fakes."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from domain.compras.service import ComprasService
from domain.estoque.repository import EstoqueRepository
from domain.estoque.service import EstoqueService
from domain.whatsapp.messages import IncomingMessage, manual_item
from domain.whatsapp.registration import FIELDS
from domain.whatsapp.service import WhatsAppService
from infrastructure.database.models import Ingrediente, Tenant, Usuario
from infrastructure.database.whatsapp_models import WhatsAppCompra
from infrastructure.ocr.gemma_adapter import ItemOCR, ResultadoOCR


class FakeOCR:
    async def processar_imagem(self, image_bytes, mime_type):
        return ResultadoOCR(
            itens=[
                ItemOCR(
                    descricao="Açúcar",
                    quantidade=Decimal("2"),
                    unidade="kg",
                    preco_unitario=Decimal("5"),
                    preco_total=Decimal("10"),
                )
            ],
            total=Decimal("10"),
            data=None,
            estabelecimento="Mercado",
            fonte="gemma4",
            confianca=0.9,
        )


def make_service(db):
    adapter = SimpleNamespace(
        send_text=AsyncMock(),
        image=AsyncMock(return_value=(b"image", "image/png")),
    )
    return WhatsAppService(
        db, adapter, ComprasService(EstoqueService(EstoqueRepository(db)), FakeOCR())
    )


@pytest.mark.asyncio
async def test_chat_registration_then_ocr_confirmation_is_idempotent(db):
    service = make_service(db)
    phone = "5511" + str(uuid4().int)[-9:]
    messages = [
        "CADASTRAR",
        "Maria",
        "Doces da Maria",
        f"{uuid4().hex}@example.com",
        "BR",
        "01001000",
        "Rua das Flores",
        "12",
        "Centro",
        "São Paulo",
        "SP",
        "CONFIRMAR CADASTRO",
    ]
    assert len(messages) == len(FIELDS) + 2
    for text in messages:
        await service.process(IncomingMessage(phone, uuid4().hex, text, False, {}))
    account = await db.scalar(select(Usuario).where(Usuario.telefone == "+" + phone))
    assert account is not None
    tenant = await db.get(Tenant, account.tenant_id)
    assert tenant.endereco["cidade"] == "São Paulo"
    image = IncomingMessage(phone, uuid4().hex, "", True, {})
    await service.process(image)
    draft = await db.scalar(
        select(WhatsAppCompra).where(WhatsAppCompra.tenant_id == account.tenant_id)
    )
    assert draft.status == "pendente"
    assert (
        await db.scalar(
            select(func.count())
            .select_from(Ingrediente)
            .where(Ingrediente.tenant_id == account.tenant_id)
        )
        == 0
    )
    confirmation = IncomingMessage(phone, uuid4().hex, "CONFIRMAR", False, {})
    await service.process(confirmation)
    await service.process(confirmation)
    # Outra mensagem de confirmação também não encontra rascunho pendente.
    await service.process(IncomingMessage(phone, uuid4().hex, "CONFIRMAR", False, {}))
    ingredient = await db.scalar(
        select(Ingrediente).where(Ingrediente.tenant_id == account.tenant_id)
    )
    assert ingredient.estoque_atual == Decimal("2")
    assert draft.status == "confirmada"


@pytest.mark.asyncio
async def test_confirmation_does_not_read_other_tenant_draft(db):
    own, other = Tenant(nome="Conta A"), Tenant(nome="Conta B")
    db.add_all([own, other])
    await db.flush()
    phone = "5511" + str(uuid4().int)[-9:]
    account = Usuario(
        tenant_id=own.id,
        nome="Ana",
        email=f"{uuid4().hex}@example.com",
        senha_hash="test",
        telefone="+" + phone,
    )
    db.add(account)
    await db.flush()
    draft = WhatsAppCompra(
        tenant_id=other.id,
        usuario_id=account.id,
        telefone=phone,
        status="pendente",
        itens=[],
        expira_em=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(draft)
    await db.flush()
    service = make_service(db)
    result = await service.handle(IncomingMessage(phone, uuid4().hex, "CONFIRMAR", False, {}))
    assert "Não há compra pendente" in result
    assert draft.status == "pendente"


@pytest.mark.asyncio
async def test_failed_second_item_rolls_back_first_stock_entry(db):
    tenant = Tenant(nome="Compra atômica")
    db.add(tenant)
    await db.flush()
    phone = "5511" + str(uuid4().int)[-9:]
    account = Usuario(
        tenant_id=tenant.id,
        nome="Ana",
        email=f"{uuid4().hex}@example.com",
        senha_hash="test",
        telefone="+" + phone,
    )
    db.add(account)
    await db.flush()
    first = manual_item("ITEM Açúcar; 2; kg; 5")
    invalid = first.model_copy(update={"criar_novo": False, "ingrediente_id": uuid4()})
    draft = WhatsAppCompra(
        tenant_id=tenant.id,
        usuario_id=account.id,
        telefone=phone,
        status="pendente",
        itens=[item.model_dump(mode="json") for item in (first, invalid)],
        expira_em=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(draft)
    await db.commit()
    tenant_id, draft_id = tenant.id, draft.id
    service = make_service(db)
    await service.process(IncomingMessage(phone, uuid4().hex, "CONFIRMAR", False, {}))
    count = await db.scalar(
        select(func.count())
        .select_from(Ingrediente)
        .where(
            Ingrediente.tenant_id == tenant_id,
        )
    )
    assert count == 0
    reloaded = await db.get(WhatsAppCompra, draft_id)
    await db.refresh(reloaded)
    assert reloaded.status == "pendente"
