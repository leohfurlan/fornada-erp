"""Service boundary: explicit approval, tenant isolation and idempotent stock."""

import base64
import io
from decimal import Decimal
from uuid import uuid4

from PIL import Image
from pydantic import SecretStr
from sqlalchemy import func, select

from core.config import settings
from infrastructure.database.models import Ingrediente, MovimentacaoEstoque, Tenant, Usuario


async def test_approved_receipt_is_idempotent_and_scoped(client, db, monkeypatch):
    assert db.bind.url.database == "fornada_test" or db.bind.url.database.startswith(
        "fornada_central_test_"
    ), "Use um banco de testes dedicado"
    bid, cid = uuid4(), uuid4()
    tenant = Tenant(nome="Synthetic Central")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id,
        nome="Synthetic",
        email=f"{uuid4()}@example.invalid",
        senha_hash="unused",
        telefone="+55119" + str(uuid4().int % 100000000).zfill(8),
    )
    item = Ingrediente(tenant_id=tenant.id, codigo=1, nome="Farinha", unidade="kg")
    db.add_all([user, item])
    await db.commit()
    monkeypatch.setattr(settings, "central_enabled", True)
    monkeypatch.setattr(
        settings, "central_service_token", SecretStr("synthetic-central-service-token-2026")
    )
    monkeypatch.setattr(settings, "central_business_tenants", {bid: tenant.id})
    monkeypatch.setattr(settings, "central_local_ocr_enabled", False)
    headers = {"Authorization": "Bearer synthetic-central-service-token-2026"}
    prefix = "/api/v1/central/"
    identity = {
        "business_id": str(bid),
        "sender_phone": user.telefone,
        "operation": "purchases.review",
    }

    async def post(path, data):
        return await client.post(prefix + path, headers=headers, json=data)

    assert (await client.post(prefix + "resolve", json=identity)).status_code == 401
    assert (await post("resolve", identity)).json()["principal_ref"] == str(user.id)
    assert (
        await post("resolve", identity | {"scope": {"tenant_id": str(uuid4()), "company_id": None}})
    ).status_code == 403
    image = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(image, format="PNG")
    extract = identity | {
        "conversation_id": str(cid),
        "incoming_message_id": str(uuid4()),
        "content_base64": base64.b64encode(image.getvalue()).decode(),
        "mime": "image/png",
    }
    response = await post("extract", extract)
    assert response.status_code == 200, response.text
    source = response.json()
    assert source["state"] == "review"
    assert (await post("extract", extract)).json()["id"] == source["id"]
    proposal = identity | {"proposal_id": source["id"]}
    scope = {"tenant_id": str(tenant.id), "company_id": None}
    operation = {
        "operation_id": str(uuid4()),
        "command_id": str(uuid4()),
        "business_id": str(bid),
        "capability_code": "stock.receive",
        "payload": {"proposal_ref": source["id"]},
        "idempotency_key": str(uuid4()),
        "principal_ref": str(user.id),
        "scope": scope,
        "conversation_id": str(cid),
        "expected_resource_version": "1",
    }
    assert (await post("execute", operation)).status_code == 409
    reviewed = {
        "itens": [
            {
                "ingrediente_id": str(item.id),
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
    assert source["state"] == "awaiting_approval"
    assert (
        await db.scalar(
            select(func.count())
            .select_from(MovimentacaoEstoque)
            .where(MovimentacaoEstoque.tenant_id == tenant.id)
        )
        == 0
    )
    decision = proposal | {
        "expected_version": source["version"],
        "summary_hash": source["summary_hash"],
        "approved": True,
        "incoming_message_id": str(uuid4()),
    }
    assert (await post("decision", decision | {"summary_hash": "0" * 64})).status_code == 409
    response = await post("decision", decision)
    assert response.status_code == 200, response.text
    assert (await post("decision", decision | {"approved": False})).status_code == 409
    operation["expected_resource_version"] = str(source["version"])
    proof = await post("approval", operation)
    assert proof.status_code == 200, proof.text
    response = await post("execute", operation)
    assert response.status_code == 200, response.text
    confirmed = response.json()
    assert confirmed["status"] == "confirmed"
    assert (await post("execute", operation)).json() == confirmed
    await db.refresh(item)
    assert item.estoque_atual == Decimal("2")
    assert (
        await db.scalar(
            select(func.count())
            .select_from(MovimentacaoEstoque)
            .where(MovimentacaoEstoque.tenant_id == tenant.id)
        )
        == 1
    )
    reference = {
        key: operation[key]
        for key in (
            "operation_id",
            "business_id",
            "capability_code",
            "principal_ref",
            "scope",
            "idempotency_key",
        )
    }
    assert (await post("reconcile", reference)).json() == confirmed
    assert (await post("execute", operation | {"operation_id": str(uuid4())})).status_code == 409
    invalid = await post("extract", extract | {"mime": "PRIVATE_INVALID_INPUT"})
    assert invalid.status_code == 422 and "PRIVATE_INVALID_INPUT" not in invalid.text
