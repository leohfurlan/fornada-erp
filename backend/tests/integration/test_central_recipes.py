import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import event

from core.config import settings
from infrastructure.database.models import (
    Ingrediente,
    Receita,
    ReceitaEtapa,
    ReceitaIngrediente,
    Tenant,
    Usuario,
)


@pytest.fixture
async def recipes(db, monkeypatch):
    assert db.bind.url.database.startswith("fornada_central_test_")
    tenant, other = Tenant(nome="Recipe QA"), Tenant(nome="Other QA")
    db.add_all([tenant, other])
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id,
        nome="Synthetic",
        email=f"{uuid4()}@example.invalid",
        senha_hash="unused",
        telefone="+55119" + str(uuid4().int % 100000000).zfill(8),
    )
    ingredient = Ingrediente(tenant_id=tenant.id, codigo=1, nome="Farinha", unidade="kg")
    base = Receita(
        tenant_id=tenant.id,
        nome="Pão base",
        categoria="massas",
        rendimento=Decimal("12"),
        rendimento_unidade="un",
        modo_preparo="  **Misture** 🥣.\n\nAsse.",
    )
    assembled = Receita(
        tenant_id=tenant.id,
        nome="Pão montado",
        categoria="montagem",
        rendimento=Decimal("1"),
        rendimento_unidade="un",
        modo_preparo="Monte.",
    )
    private = Receita(
        tenant_id=other.id,
        nome="Pão secreto",
        categoria="outra",
        rendimento=Decimal("1"),
        rendimento_unidade="un",
        modo_preparo="Não divulgar.",
    )
    db.add_all([user, ingredient, base, assembled, private])
    await db.flush()
    db.add(
        ReceitaIngrediente(
            receita_id=base.id,
            ingrediente_id=ingredient.id,
            quantidade=Decimal("0.1250"),
            unidade="kg",
        )
    )
    db.add(
        ReceitaEtapa(
            receita_id=base.id, nome="Assar", duracao_minutos=35, tipo_mao_obra="indireta", ordem=1
        )
    )
    assembled.ficha_tecnica = {
        "descricao_produto": "Pão final",
        "especificacao_final": "  Sirva quente.\n",
        "passos": [
            {
                "descricao": "Massa",
                "tipo": "componente",
                "quantidade": "1.0000",
                "unidade": "un",
                "receita_base_id": str(base.id),
                "especificacao": "Inteira",
                "instrucao": "  **Recheie**.\n",
            }
        ],
    }
    await db.commit()
    bid = uuid4()
    monkeypatch.setattr(settings, "central_enabled", True)
    monkeypatch.setattr(
        settings, "central_service_token", SecretStr("synthetic-service-token-at-least-32")
    )
    monkeypatch.setattr(settings, "central_business_tenants", {bid: tenant.id})
    envelope = {
        "operation_id": str(uuid4()),
        "command_id": str(uuid4()),
        "business_id": str(bid),
        "idempotency_key": str(uuid4()),
        "principal_ref": str(user.id),
        "scope": {"tenant_id": str(tenant.id), "company_id": None},
    }
    return envelope, user, base, assembled, private


HEADERS = {"Authorization": "Bearer synthetic-service-token-at-least-32"}
PREFIX = "/api/v1/central/"


async def post(client, envelope, code, payload, **extra):
    return await client.post(
        PREFIX + "recipes/" + code,
        headers=HEADERS,
        json={
            **envelope,
            "capability_code": "recipes." + code,
            "payload": payload,
            **extra,
        },
    )


async def test_search_authentication_isolation_and_pagination(client, recipes):
    envelope, _, base, assembled, private = recipes
    body = envelope | {"capability_code": "recipes.search", "payload": {"query": "pao"}}
    assert (await client.post(PREFIX + "recipes/search", json=body)).status_code == 401
    first = await post(client, envelope, "search", {"query": "pao", "limit": 1})
    assert first.status_code == 200, first.text
    data = first.json()["data"]
    assert data["next_offset"] == 1
    second = await post(client, envelope, "search", {"query": "pao", "offset": 1, "limit": 1})
    ids = [data["items"][0]["recipe_id"], second.json()["data"]["items"][0]["recipe_id"]]
    assert set(ids) == {str(base.id), str(assembled.id)}
    assert str(private.id) not in ids
    assert second.json()["data"]["next_offset"] is None


async def test_integral_snapshot_has_no_costs_and_includes_components(client, recipes, db):
    envelope, _, base, assembled, _ = recipes
    statements = []

    def collect(conn, cursor, statement, params, context, many):
        if statement.lstrip().upper().startswith("SELECT") and "receitas" in statement:
            statements.append(statement)

    event.listen(db.bind.sync_engine, "before_cursor_execute", collect)
    try:
        response = await post(client, envelope, "read", {"recipe_id": str(assembled.id)})
    finally:
        event.remove(db.bind.sync_engine, "before_cursor_execute", collect)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(statements) == 1
    assert "0.1250 kg" in str(data)
    assert base.modo_preparo in [section["text"] for section in data["sections"]]
    assert "  **Recheie**.\n" in str([section["text"] for section in data["sections"]]).replace(
        "\\n", "\n"
    )
    assert not {"custo", "margem_desejada", "preco_de_venda_real"}.intersection(data)
    canonical = {key: value for key, value in data.items() if key != "version"}
    digest = hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == data["version"] == response.json()["resource_version"]
    assert (
        await post(
            client,
            envelope,
            "read",
            {"recipe_id": str(assembled.id)},
            expected_resource_version="wrong",
        )
    ).status_code == 409


async def test_read_and_resolve_do_not_cross_tenant(client, recipes):
    envelope, user, _, _, private = recipes
    assert (await post(client, envelope, "read", {"recipe_id": str(private.id)})).status_code == 404
    identity = {
        "business_id": envelope["business_id"],
        "sender_phone": user.telefone,
        "operation": "recipes.read",
        "resource_id": str(private.id),
    }
    assert (
        await client.post(PREFIX + "resolve", headers=HEADERS, json=identity)
    ).status_code == 403
    response = await post(
        client,
        envelope,
        "search",
        {"query": "pao"},
        scope={"tenant_id": str(uuid4()), "company_id": None},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("change", ["inactive", "deleted", "phone", "superuser", "tenant"])
async def test_actor_revocation_blocks_search(client, recipes, db, change):
    envelope, user, _, _, _ = recipes
    if change == "inactive":
        user.ativo = False
    elif change == "deleted":
        user.deleted_at = datetime.now(UTC)
    elif change == "phone":
        user.telefone = None
    elif change == "superuser":
        user.is_superuser = True
    else:
        tenant = await db.get(Tenant, user.tenant_id)
        tenant.ativo = False
    await db.commit()
    assert (await post(client, envelope, "search", {"query": "pao"})).status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"query": " "},
        {"query": "x\ny"},
        {"query": "pao", "limit": True},
        {"query": "pao", "limit": 21},
        {"query": "pao", "offset": -1},
        {"query": "pao", "tenant_id": str(uuid4())},
    ],
)
async def test_invalid_payload_is_422_and_private_fields_are_hidden(client, recipes, payload):
    response = await post(client, recipes[0], "search", payload)
    assert response.status_code == 422, response.text


async def test_cycle_and_unavailable_dependency_are_explicit(client, recipes, db):
    envelope, _, base, assembled, private = recipes
    base.ficha_tecnica = {
        "passos": [
            {
                "descricao": "Volta",
                "tipo": "componente",
                "quantidade": "1",
                "unidade": "un",
                "receita_base_id": str(assembled.id),
            },
            {
                "descricao": "Ausente",
                "tipo": "componente",
                "quantidade": "1",
                "unidade": "un",
                "receita_base_id": str(private.id),
            },
        ]
    }
    await db.commit()
    response = await post(client, envelope, "read", {"recipe_id": str(assembled.id)})
    assert response.status_code == 200, response.text
    warnings = response.json()["data"]["warnings"]
    assert any("cíclica" in warning for warning in warnings)
    assert any("indisponível" in warning for warning in warnings)
    assert private.nome not in response.text


async def test_soft_deleted_recipe_children_are_not_exported(client, recipes, db):
    from sqlalchemy import select

    envelope, _, base, _, _ = recipes
    item = await db.scalar(
        select(ReceitaIngrediente).where(ReceitaIngrediente.receita_id == base.id)
    )
    step = await db.scalar(select(ReceitaEtapa).where(ReceitaEtapa.receita_id == base.id))
    item.deleted_at = step.deleted_at = datetime.now(UTC)
    await db.commit()
    response = await post(client, envelope, "read", {"recipe_id": str(base.id)})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["ingredients"] == []
    assert not any(s["title"] == "Etapa 1" for s in data["sections"])
    assert any("ingredientes não cadastrados" in w for w in data["warnings"])


async def test_assembly_material_links_are_resolved_in_same_snapshot(client, recipes, db):
    envelope, user, _, assembled, private = recipes
    material = Ingrediente(
        tenant_id=user.tenant_id, codigo=99, nome="Chocolate da montagem", unidade="g"
    )
    hidden = Ingrediente(
        tenant_id=private.tenant_id, codigo=99, nome="Material privado", unidade="g"
    )
    db.add_all([material, hidden])
    await db.flush()
    assembled.ficha_tecnica = {
        "passos": [
            {
                "descricao": "Cobertura",
                "tipo": "ingrediente",
                "quantidade": "0.1234",
                "unidade": "g",
                "ingrediente_id": str(material.id),
                "instrucao": "  Derreta.\n",
            },
            {
                "descricao": "Alheio",
                "tipo": "ingrediente",
                "quantidade": "1",
                "unidade": "g",
                "ingrediente_id": str(hidden.id),
            },
            {
                "descricao": "Inválido",
                "tipo": "componente",
                "quantidade": "1",
                "unidade": "un",
                "receita_base_id": "legacy-invalid-id",
            },
        ]
    }
    await db.commit()
    statements = []

    def collect(conn, cursor, statement, params, context, many):
        if statement.lstrip().upper().startswith("SELECT") and "receitas" in statement:
            statements.append(statement)

    event.listen(db.bind.sync_engine, "before_cursor_execute", collect)
    try:
        response = await post(client, envelope, "read", {"recipe_id": str(assembled.id)})
    finally:
        event.remove(db.bind.sync_engine, "before_cursor_execute", collect)
    assert response.status_code == 200, response.text
    assert len(statements) == 1
    data = response.json()["data"]
    assert material.nome in str(data["sections"])
    assert "0.1234 g" in str(data["sections"])
    assert hidden.nome not in response.text
    assert any("material vinculado indisponível" in w for w in data["warnings"])
    assert any("sub-receita vinculada indisponível" in w for w in data["warnings"])


@pytest.mark.parametrize("field", ["yield", "ingredient", "assembly"])
async def test_invalid_nested_quantities_are_rejected(client, recipes, db, field):
    from sqlalchemy import select

    envelope, _, base, assembled, _ = recipes
    if field == "yield":
        base.rendimento = Decimal("0")
    elif field == "ingredient":
        item = await db.scalar(
            select(ReceitaIngrediente).where(ReceitaIngrediente.receita_id == base.id)
        )
        item.quantidade = Decimal("0")
    else:
        assembled.ficha_tecnica = {
            "passos": [
                {
                    "descricao": "Inválido",
                    "tipo": "ingrediente",
                    "quantidade": "NaN",
                    "unidade": "g",
                }
            ]
        }
    await db.commit()
    response = await post(client, envelope, "read", {"recipe_id": str(assembled.id)})
    assert response.status_code == 422, response.text
    assert "data" not in response.json()
