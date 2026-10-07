from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from core.security import create_access_token, create_refresh_token, verify_password
from infrastructure.database.models import Receita, SessaoAdministrativa, Tenant, Usuario
from scripts.criar_superusuario import criar_superusuario


async def account(db, admin=False):
    tenant = Tenant(nome=f"Negócio {uuid4()}")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id,
        nome="Teste",
        email=f"{uuid4()}@example.com",
        senha_hash="unused",
        is_superuser=admin,
    )
    db.add(user)
    await db.flush()
    return user, tenant


def headers(user, session_id=None):
    result = {"Authorization": f"Bearer {create_access_token(user.id, user.tenant_id)}"}
    if session_id:
        result["X-Admin-Session"] = str(session_id)
    return result


async def support(client, actor, target):
    response = await client.post(
        "/api/v1/admin/suporte",
        headers=headers(actor),
        json={"usuario_id": str(target.id), "motivo": "Atendimento solicitado"},
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


async def test_normal_user_cannot_list_or_open_support(client, db):
    user, _ = await account(db)
    target, _ = await account(db)
    assert (await client.get("/api/v1/admin/usuarios", headers=headers(user))).status_code == 403
    result = await client.post(
        "/api/v1/admin/suporte",
        headers=headers(user),
        json={"usuario_id": str(target.id), "motivo": "Tentativa de acesso"},
    )
    assert result.status_code == 403
    result = await client.get("/api/v1/auth/me", headers=headers(user, uuid4()))
    assert result.status_code == 403


async def test_superuser_search_and_support_read_write_isolation(client, db):
    actor, _ = await account(db, True)
    target, tenant = await account(db)
    other, _ = await account(db)
    result = await client.get(
        "/api/v1/admin/usuarios", headers=headers(actor), params={"q": target.email}
    )
    assert [item["id"] for item in result.json()] == [str(target.id)]
    assert "senha_hash" not in result.text
    sid = await support(client, actor, target)
    session = await db.get(SessaoAdministrativa, sid)
    assert session.operador_id == actor.id and session.tenant_id == tenant.id
    result = await client.get("/api/v1/auth/me", headers=headers(actor, sid))
    assert result.json()["id"] == str(target.id)
    data = dict(
        nome="Receita suporte",
        categoria="Bolo",
        rendimento="1",
        rendimento_unidade="un",
        ingredientes=[],
        etapas=[],
    )
    created = await client.post("/api/v1/receitas", headers=headers(actor, sid), json=data)
    assert created.status_code == 201, created.text
    receita_id = UUID(created.json()["id"])
    assert created.json()["tenant_id"] == str(target.tenant_id)
    assert (
        await client.get(f"/api/v1/receitas/{receita_id}", headers=headers(other))
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/receitas/{receita_id}", headers=headers(actor))
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/receitas/{receita_id}", headers=headers(actor, sid))
    ).status_code == 200
    rows = (await db.execute(select(Receita).where(Receita.id == receita_id))).scalars().all()
    assert len(rows) == 1 and rows[0].tenant_id == tenant.id
    assert (
        await client.delete(f"/api/v1/admin/suporte/{sid}", headers=headers(actor))
    ).status_code == 204
    assert (await client.get("/api/v1/receitas", headers=headers(actor, sid))).status_code == 403
    # Encerramento idempotente.
    assert (
        await client.delete(f"/api/v1/admin/suporte/{sid}", headers=headers(actor))
    ).status_code == 204


@pytest.mark.parametrize(
    "blocked", ["expired", "revoked", "target_disabled", "tenant_disabled", "target_deleted"]
)
async def test_support_rechecks_permissions_and_expiration(client, db, blocked):
    actor, _ = await account(db, True)
    target, tenant = await account(db)
    sid = await support(client, actor, target)
    session = await db.get(SessaoAdministrativa, sid)
    if blocked == "expired":
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    elif blocked == "revoked":
        actor.is_superuser = False
    elif blocked == "target_disabled":
        target.ativo = False
    elif blocked == "tenant_disabled":
        tenant.ativo = False
    else:
        target.deleted_at = datetime.now(UTC)
    await db.flush()
    assert (await client.get("/api/v1/receitas", headers=headers(actor, sid))).status_code == 403


async def test_sessions_cannot_be_used_by_another_admin_or_to_change_identity(client, db):
    actor, _ = await account(db, True)
    other_admin, _ = await account(db, True)
    target, _ = await account(db)
    sid = await support(client, actor, target)
    assert (
        await client.get("/api/v1/receitas", headers=headers(other_admin, sid))
    ).status_code == 403
    assert (
        await client.delete(f"/api/v1/admin/suporte/{sid}", headers=headers(other_admin))
    ).status_code == 404
    result = await client.post(
        "/api/v1/admin/suporte",
        headers=headers(actor),
        json={"usuario_id": str(other_admin.id), "motivo": "Tentativa de suporte"},
    )
    assert result.status_code == 403
    result = await client.post(
        "/api/v1/auth/whatsapp/vincular", headers=headers(actor, sid), json={"prova": "teste"}
    )
    assert result.status_code == 403


async def test_refresh_preserves_actor_identity(client, db):
    actor, _ = await account(db, True)
    target, _ = await account(db)
    sid = await support(client, actor, target)
    result = await client.post(
        "/api/v1/auth/refresh",
        headers=headers(actor, sid),
        json={"refresh_token": create_refresh_token(actor.id, actor.tenant_id)},
    )
    assert result.status_code == 200
    assert result.json()["usuario"]["id"] == str(actor.id)


async def test_bootstrap_login_and_duplicate_does_not_promote(client, db):
    email = f"{uuid4()}@example.com"
    senha = "Senha-de-teste-separada-16"
    actor = await criar_superusuario(db, email.upper(), "Administrador", senha)
    assert actor.is_superuser and verify_password(senha, actor.senha_hash)
    await db.commit()
    response = await client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    assert response.status_code == 200, response.text
    assert response.json()["usuario"]["is_superuser"] is True
    existing, _ = await account(db)
    with pytest.raises(ValueError, match="já cadastrado"):
        await criar_superusuario(db, existing.email, "Administrador", senha)
    assert not existing.is_superuser


async def test_registration_cannot_self_grant_superuser(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "nome_negocio": "Conta normal",
            "nome": "Usuário",
            "email": f"{uuid4()}@example.com",
            "senha": "Senha-de-teste-16",
            "is_superuser": True,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["usuario"]["is_superuser"] is False
