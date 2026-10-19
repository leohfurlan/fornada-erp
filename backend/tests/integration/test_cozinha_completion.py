"""Checklist commands persist in the existing station JSON, under lease/CAS."""

from decimal import Decimal
from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_authenticated_actor
from domain.receitas.central_snapshot import snapshot
from infrastructure.database.cozinha_models import CozinhaEstacao
from infrastructure.database.models import Receita, ReceitaEtapa, Tenant, Usuario
from main import app


async def test_checklist_persists_through_pause_and_new_lease(
    client: AsyncClient, db: AsyncSession
) -> None:
    assert db.bind is not None
    assert db.bind.url.database.startswith("fornada_central_test_")
    tenant = Tenant(nome="Checklist synthetic")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id, nome="Cook", email=f"{uuid4()}@example.invalid", senha_hash="unused"
    )
    recipe = Receita(
        tenant_id=tenant.id,
        nome="Synthetic cake",
        categoria="Bolo",
        rendimento=Decimal("1"),
        rendimento_unidade="un",
        modo_preparo="1. Misture\n2. Asse",
    )
    other_recipe = Receita(
        tenant_id=tenant.id,
        nome="Other cake",
        categoria="Bolo",
        rendimento=Decimal("1"),
        rendimento_unidade="un",
        modo_preparo="1. Espere",
    )
    db.add_all([user, recipe, other_recipe])
    await db.flush()
    registered = [
        ReceitaEtapa(receita_id=recipe.id, nome="Misturar", duracao_minutos=5, ordem=0),
        ReceitaEtapa(receita_id=recipe.id, nome="Assar", duracao_minutos=30, ordem=1),
    ]
    db.add_all(registered)
    await db.flush()
    first_step, second_step = (f"step-{step.id}" for step in registered)
    central = await snapshot(db, tenant.id, recipe.id)
    kitchen = await snapshot(db, tenant.id, recipe.id, include_steps=True)
    assert "steps" not in central
    assert [step["id"] for step in kitchen["steps"]] == [str(step.id) for step in registered]
    app.dependency_overrides[get_authenticated_actor] = lambda: user
    created = await client.post("/api/v1/cozinha/stations", json={"name": "Checklist"})
    station_id = created.json()["station"]["id"]
    root = f"/api/v1/cozinha/stations/{station_id}"
    activated = await client.post(root + "/lease", json={"expected_revision": 0})
    assert activated.status_code == 200, activated.text
    lease = activated.json()["lease_id"]
    revision = activated.json()["station"]["revision"]

    async def send(kind: str, **payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        nonlocal revision
        body = {
            "command_id": str(uuid4()),
            "expected_revision": revision,
            "lease_id": lease,
            "type": kind,
            "payload": payload,
        }
        result = await client.post(root + "/commands", json=body)
        assert result.status_code == 200, result.text
        revision = result.json()["revision"]
        return body, result.json()

    async def read() -> dict[str, Any]:
        # Force a real station read without expiring the authenticated actor.
        for entity in list(db.identity_map.values()):
            if isinstance(entity, CozinhaEstacao):
                db.expire(entity)
        result = await client.get(root, params={"lease_id": lease})
        assert result.status_code == 200, result.text
        return result.json()["station"]

    await send("open_recipe", recipe_id=str(recipe.id))
    state = await read()
    assert [block["id"] for block in state["projection"]["blocks"] if block.get("checkable")] == [
        first_step,
        second_step,
    ]
    rejected = await client.post(
        root + "/commands",
        json={
            "command_id": str(uuid4()),
            "expected_revision": revision,
            "lease_id": lease,
            "type": "set_step_completed",
            "payload": {"block_id": "preparation-text", "completed": True},
        },
    )
    assert rejected.status_code == 422
    session = state["projection"]["session_id"]
    body, receipt = await send("set_step_completed", block_id=second_step, completed=True)
    retry = await client.post(root + "/commands", json=body)
    assert retry.json() == receipt
    await send("show_section", section="steps")
    assert (await read())["projection"]["completed_block_ids"] == [second_step]

    closed = await client.post(root + "/close", json={"lease_id": lease})
    assert closed.status_code == 204
    summary = await client.get("/api/v1/cozinha/stations")
    activated = await client.post(
        root + "/lease", json={"expected_revision": summary.json()["items"][0]["revision"]}
    )
    assert activated.status_code == 200, activated.text
    lease = activated.json()["lease_id"]
    revision = activated.json()["station"]["revision"]
    resumed = await read()
    assert resumed["projection"]["session_id"] == session
    assert resumed["projection"]["completed_block_ids"] == [second_step]
    await send("open_recipe", recipe_id=str(recipe.id))
    assert (await read())["projection"]["session_id"] == session
    assert (await read())["projection"]["completed_block_ids"] == [second_step]

    await send("set_step_completed", block_id=first_step, completed=True)
    assert len((await read())["projection"]["completed_block_ids"]) == 2
    await send("set_step_completed", block_id=second_step, completed=False)
    assert (await read())["projection"]["completed_block_ids"] == [first_step]
    await send("reset_steps")
    reset = (await read())["projection"]
    assert reset["completed_block_ids"] == []
    assert reset["session_id"] != session
    await send("set_step_completed", block_id=first_step, completed=True)
    # Switching recipes starts a new preparation session.
    await send("open_recipe", recipe_id=str(other_recipe.id))
    assert (await read())["projection"]["completed_block_ids"] == []
    await send("open_recipe", recipe_id=str(recipe.id))
    assert (await read())["projection"]["completed_block_ids"] == []
    # Another authenticated user cannot read or modify this station.
    outsider = Usuario(
        tenant_id=tenant.id,
        nome="Other cook",
        email=f"{uuid4()}@example.invalid",
        senha_hash="unused",
    )
    db.add(outsider)
    await db.commit()
    app.dependency_overrides[get_authenticated_actor] = lambda: outsider
    assert (await client.get(root, params={"lease_id": lease})).status_code == 404
    app.dependency_overrides[get_authenticated_actor] = lambda: user
    # Positional IDs must never inherit completion after a recipe edit.
    saved = await db.scalar(
        select(Receita).where(Receita.id == recipe.id, Receita.tenant_id == tenant.id)
    )
    assert saved is not None
    saved.modo_preparo = "1. Uma etapa diferente"
    await db.commit()
    invalidated = await read()
    assert invalidated["projection"] is None
    assert "alterada" in invalidated["notice"]
