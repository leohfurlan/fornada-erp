import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_authenticated_actor
from core.security import create_access_token
from infrastructure.database.models import Tenant, Usuario
from infrastructure.database.pwa_models import PwaEvento
from main import app


async def criar_usuario(db: AsyncSession, admin: bool = False) -> Usuario:
    tenant = Tenant(nome="Teste PWA")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id,
        nome="Teste",
        email=f"{uuid4()}@example.com",
        senha_hash="teste",
        is_superuser=admin,
    )
    db.add(user)
    await db.flush()
    return user


def evento(**overrides: str) -> dict[str, str]:
    return {
        "event_id": str(uuid4()),
        "browser_id": str(uuid4()),
        "session_id": str(uuid4()),
        "tipo": "convite_exibido",
        "origem": "automatico",
        **overrides,
    }


@pytest.mark.asyncio
async def test_eventos_idempotencia_e_conflito(client: AsyncClient, db: AsyncSession) -> None:
    user = await criar_usuario(db)
    app.dependency_overrides[get_authenticated_actor] = lambda: user
    payload = evento()
    first = await client.post("/api/v1/pwa/eventos", json=payload)
    assert first.status_code == 201, first.text
    repeat = await client.post("/api/v1/pwa/eventos", json=payload)
    assert repeat.status_code == 200
    assert repeat.json() == first.json()
    conflict = await client.post("/api/v1/pwa/eventos", json={**payload, "tipo": "adiado"})
    assert conflict.status_code == 409
    assert (
        await db.execute(
            select(func.count())
            .select_from(PwaEvento)
            .where(
                PwaEvento.tenant_id == user.tenant_id,
                PwaEvento.usuario_id == user.id,
                PwaEvento.event_id == payload["event_id"],
            )
        )
    ).scalar_one() == 1


@pytest.mark.asyncio
async def test_identidade_e_suporte(client: AsyncClient, db: AsyncSession) -> None:
    user = await criar_usuario(db)
    app.dependency_overrides[get_authenticated_actor] = lambda: user
    assert (
        await client.post(
            "/api/v1/pwa/eventos", json=evento(), headers={"X-Admin-Session": str(uuid4())}
        )
    ).status_code == 403
    assert (
        await client.post("/api/v1/pwa/eventos", json=evento(usuario_id=str(uuid4())))
    ).status_code == 422
    assert (await client.get("/api/v1/admin/pwa/usuarios")).status_code == 403
    assert (
        await client.post("/api/v1/pwa/eventos", json=evento(tipo="acesso_app"))
    ).status_code == 422
    assert (
        await client.post("/api/v1/pwa/eventos", json=evento(event_id="bad"))
    ).status_code == 422
    assert (await client.post("/api/v1/pwa/eventos", json={})).status_code == 422


@pytest.mark.asyncio
async def test_admin_sinais_independentes_e_conta_sem_eventos(
    client: AsyncClient, db: AsyncSession
) -> None:
    user = await criar_usuario(db)
    other = await criar_usuario(db)
    admin = await criar_usuario(db, admin=True)
    app.dependency_overrides[get_authenticated_actor] = lambda: user
    assert (
        await client.post(
            "/api/v1/pwa/eventos", json=evento(tipo="instalacao_sinalizada", origem="navegador")
        )
    ).status_code == 201
    assert (
        await client.post(
            "/api/v1/pwa/eventos", json=evento(tipo="acesso_app", origem="abertura_app")
        )
    ).status_code == 201
    app.dependency_overrides[get_authenticated_actor] = lambda: admin
    result = await client.get("/api/v1/admin/pwa/usuarios", params={"q": user.email})
    assert result.status_code == 200, result.text
    item = result.json()["items"][0]
    assert item["usuario_id"] == str(user.id)
    assert item["sinais"]["acesso_app"]["quantidade"] == 1
    assert item["sinais"]["confirmacao_aceita"] == {"quantidade": 0, "ultimo_em": None}
    empty = (await client.get("/api/v1/admin/pwa/usuarios", params={"q": other.email})).json()
    assert all(s["quantidade"] == 0 for s in empty["items"][0]["sinais"].values())
    assert (await client.get("/api/v1/admin/pwa/usuarios", params={"limit": 0})).status_code == 422
    assert (
        await client.get("/api/v1/admin/pwa/usuarios", headers={"X-Admin-Session": "x"})
    ).status_code == 403


@pytest.mark.asyncio
async def test_anonimo_nao_acessa_coleta_nem_painel(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/pwa/eventos", json=evento())).status_code in (401, 403)
    assert (await client.get("/api/v1/admin/pwa/usuarios")).status_code in (401, 403)


@pytest.mark.asyncio
async def test_jwt_real_isolamento_e_reenvio_concorrente(
    client: AsyncClient, db: AsyncSession
) -> None:
    from infrastructure.database.session import get_db
    from tests.conftest import TestingSessionLocal

    user = await criar_usuario(db)
    other = await criar_usuario(db)
    admin = await criar_usuario(db, admin=True)
    await db.commit()

    async def independent_db():
        async with TestingSessionLocal() as request_db:
            yield request_db

    app.dependency_overrides[get_db] = independent_db

    def headers(actor: Usuario) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(actor.id, actor.tenant_id)}"}

    payload = evento()
    responses = await asyncio.gather(
        *[client.post("/api/v1/pwa/eventos", json=payload, headers=headers(user)) for _ in range(2)]
    )
    assert sorted(r.status_code for r in responses) == [200, 201]
    # A mesma chave em outro tenant não se confunde com o primeiro ator.
    assert (
        await client.post("/api/v1/pwa/eventos", json=payload, headers=headers(other))
    ).status_code == 201
    assert (
        await client.get("/api/v1/admin/pwa/usuarios", headers=headers(other))
    ).status_code == 403
    for actor in (user, other):
        result = await client.get(
            "/api/v1/admin/pwa/usuarios", params={"q": actor.email}, headers=headers(admin)
        )
        assert result.json()["items"][0]["sinais"]["convite_exibido"]["quantidade"] == 1
    user.ativo = False
    await db.commit()
    assert (
        await client.post("/api/v1/pwa/eventos", json=evento(), headers=headers(user))
    ).status_code == 401
