"""Contrato de acesso atual e aprovação específica da integração privada."""

import base64
import io
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from PIL import Image
from pydantic import SecretStr

from core.config import settings
from infrastructure.database.models import Ingrediente, Tenant, Usuario


@pytest_asyncio.fixture
async def purchase(client, db, monkeypatch):
    assert db.bind.url.database == "fornada_test" or db.bind.url.database.startswith(
        "fornada_central_test_"
    ), "Use um banco de testes dedicado"
    tenant = Tenant(nome="Central synthetic guards")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id,
        nome="Synthetic",
        email=f"{uuid4()}@example.invalid",
        telefone="+55119" + str(uuid4().int % 100000000).zfill(8),
        senha_hash="unused",
    )
    material = Ingrediente(tenant_id=tenant.id, codigo=1, nome="Farinha", unidade="kg")
    db.add_all([user, material])
    await db.commit()
    bid = uuid4()
    monkeypatch.setattr(settings, "central_enabled", True)
    monkeypatch.setattr(
        settings, "central_service_token", SecretStr("synthetic-service-token-central-2026")
    )
    monkeypatch.setattr(settings, "central_business_tenants", {bid: tenant.id})
    monkeypatch.setattr(settings, "central_local_ocr_enabled", False)
    identity = {
        "business_id": str(bid),
        "sender_phone": user.telefone,
        "operation": "purchases.review",
    }

    async def post(path, data):
        return await client.post(
            "/api/v1/central/" + path,
            json=data,
            headers={"Authorization": "Bearer synthetic-service-token-central-2026"},
        )

    stream = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(stream, format="PNG")
    cid = uuid4()
    extracted = await post(
        "extract",
        identity
        | {
            "conversation_id": str(cid),
            "incoming_message_id": str(uuid4()),
            "content_base64": base64.b64encode(stream.getvalue()).decode(),
            "mime": "image/png",
        },
    )
    assert extracted.status_code == 200
    proposal = identity | {"proposal_id": extracted.json()["id"]}
    reviewed = {
        "itens": [
            {
                "ingrediente_id": str(material.id),
                "descricao_original": "FARINHA",
                "quantidade": "2",
                "unidade": "kg",
                "custo_unitario": "10",
                "preco_total": "20",
                "aceitar_excecao": True,
            }
        ]
    }
    response = await post("review", proposal | {"expected_version": 1, "reviewed": reviewed})
    assert response.status_code == 200, response.text
    source = response.json()
    decision = proposal | {
        "expected_version": source["version"],
        "summary_hash": source["summary_hash"],
        "approved": True,
        "incoming_message_id": str(uuid4()),
    }
    operation = {
        "operation_id": str(uuid4()),
        "command_id": str(uuid4()),
        "business_id": str(bid),
        "capability_code": "stock.receive",
        "payload": {"proposal_ref": source["id"]},
        "idempotency_key": str(uuid4()),
        "principal_ref": str(user.id),
        "scope": source["scope"],
        "conversation_id": str(cid),
        "expected_resource_version": str(source["version"]),
    }
    return post, proposal, decision, operation, user, material, tenant


async def test_phone_replaced_after_approval_cannot_execute(purchase, db):
    post, _, decision, operation, user, _, _ = purchase
    assert (await post("decision", decision)).status_code == 200
    user.telefone = "+55118" + str(uuid4().int % 100000000).zfill(8)
    await db.commit()
    assert (await post("execute", operation)).status_code == 403


async def test_resolve_denies_unknown_purchase_resource(purchase):
    post, proposal, *_ = purchase
    identity = {k: v for k, v in proposal.items() if k != "proposal_id"}
    assert (await post("resolve", identity | {"resource_id": str(uuid4())})).status_code == 403


@pytest.mark.parametrize("change", ["inactive", "superuser", "deleted", "tenant_inactive", "grant"])
async def test_current_access_is_required_after_approval(purchase, db, monkeypatch, change):
    post, _, decision, operation, user, material, tenant = purchase
    assert (await post("decision", decision)).status_code == 200
    if change == "inactive":
        user.ativo = False
    elif change == "superuser":
        user.is_superuser = True
    elif change == "deleted":
        user.deleted_at = datetime.now(UTC)
    elif change == "tenant_inactive":
        tenant.ativo = False
    else:
        monkeypatch.setattr(settings, "central_business_tenants", {})
    await db.commit()
    assert (await post("execute", operation)).status_code == 403
    await db.refresh(material)
    assert material.estoque_atual == 0


async def test_old_summary_and_refusal_have_no_stock_effect(purchase, db):
    post, proposal, decision, operation, _, material, _ = purchase
    assert (await post("decision", decision | {"expected_version": 1})).status_code == 409
    assert (await post("decision", decision | {"approved": False})).status_code == 200
    assert (await post("execute", operation)).status_code == 409
    await db.refresh(material)
    assert material.estoque_atual == 0


async def test_expired_proposal_requires_erp_review(purchase, db):
    from infrastructure.database.central_models import CentralCompra

    post, proposal, decision, *_ = purchase
    row = await db.get(CentralCompra, proposal["proposal_id"])
    row.expira_em = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()
    assert (await post("decision", decision)).status_code == 409


async def test_revised_summary_invalidates_previous_approval(purchase):
    post, proposal, decision, operation, *_ = purchase
    assert (await post("decision", decision)).status_code == 200
    source = (await post("draft", proposal)).json()
    assert (
        await post(
            "review",
            proposal | {"expected_version": source["version"], "reviewed": source["reviewed"]},
        )
    ).status_code == 200
    assert (await post("execute", operation)).status_code == 409


async def test_changed_material_invalidates_approved_preview(purchase, db):
    post, _, decision, operation, _, material, _ = purchase
    assert (await post("decision", decision)).status_code == 200
    material.nome = "Material revisado"
    await db.commit()
    assert (await post("execute", operation)).status_code == 409
    await db.refresh(material)
    assert material.estoque_atual == 0


async def test_approval_is_only_issued_for_stock_receive(purchase):
    post, _, decision, operation, *_ = purchase
    assert (await post("decision", decision)).status_code == 200
    assert (
        await post("approval", operation | {"capability_code": "purchases.review"})
    ).status_code == 422
