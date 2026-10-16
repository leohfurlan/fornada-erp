from uuid import uuid4

import pytest
from sqlalchemy import select

from domain.exceptions import ConflictError, NotFoundError
from domain.receitas.historico import HistoricoReceita
from domain.receitas.repository import ReceitaRepository
from domain.receitas.service import ReceitaService
from domain.receitas.schemas import CriarReceitaRequest, AtualizarReceitaRequest
from domain.receitas.ficha_service import FichaTecnicaService
from domain.receitas.ficha_tecnica import FichaTecnicaInput
from infrastructure.database.models import Tenant, Usuario, ReceitaVersao


@pytest.mark.asyncio
async def test_criacao_edicao_montagem_copia_conflito_e_isolamento(db):
    tenant = Tenant(nome="QA versões")
    db.add(tenant)
    await db.flush()
    user = Usuario(tenant_id=tenant.id, nome="Editor QA", email=f"{uuid4()}@example.test", senha_hash="synthetic")
    db.add(user)
    await db.flush()
    service = ReceitaService(ReceitaRepository(db), db)
    texto = "# Preparo\n\n  Mexa 🍰 suavemente."
    receita = await service.criar(tenant.id, CriarReceitaRequest(nome="bolo", categoria="Bolos", rendimento="2.5", rendimento_unidade="un", ingredientes=[], etapas=[], modo_preparo=texto), user.id)
    assert receita.nome == "BOLO" and receita.versao == 1
    editada = await service.atualizar(receita.id, tenant.id, AtualizarReceitaRequest(nome="bolo especial", versao=1), user.id)
    assert editada.versao == 2
    with pytest.raises(ConflictError):
        await service.atualizar(receita.id, tenant.id, AtualizarReceitaRequest(nome="Sobrescrito", versao=1), user.id)
    ficha = FichaTecnicaInput(revisao=0, descricao_produto="Monte delicadamente 🍫", passos=[dict(descricao="Chocolate", tipo="acabamento", quantidade="0.125", unidade="g", instrucao="  Preserve\n\ntexto")])
    await FichaTecnicaService(db).salvar(receita.id, tenant.id, ficha, user.id)
    rows = (await db.scalars(select(ReceitaVersao).where(ReceitaVersao.receita_id == receita.id).order_by(ReceitaVersao.versao))).all()
    assert [r.versao for r in rows] == [1, 2, 3]
    assert all(r.usuario_id == user.id for r in rows)
    assert rows[0].snapshot["nome"] == "BOLO"
    assert rows[1].snapshot["nome"] == "BOLO ESPECIAL"
    assert rows[2].snapshot["modo_preparo"] == texto
    assert rows[2].snapshot["ficha_tecnica"]["passos"][0]["quantidade"] == "0.125"
    assert rows[2].snapshot["ficha_revisao"] == 1
    with pytest.raises(NotFoundError):
        await HistoricoReceita(db).receita(receita.id, uuid4())
    copia = await service.duplicar(receita.id, tenant.id, user.id)
    assert copia.versao == 1 and "CÓPIA" in copia.nome
    assert (await db.scalar(select(ReceitaVersao).where(ReceitaVersao.receita_id == copia.id))).origem == "copia"


@pytest.mark.asyncio
async def test_legado_baseline_preserva_conteudo_sem_atribuir_autoria(db):
    from infrastructure.database.models import Receita
    tenant = Tenant(nome="QA legado")
    db.add(tenant)
    await db.flush()
    row = Receita(tenant_id=tenant.id, nome="Bolo antigo", categoria="Bolo", rendimento=1, rendimento_unidade="un", margem_desejada=0.3)
    db.add(row)
    await db.flush()
    await ReceitaService(ReceitaRepository(db), db).atualizar(row.id, tenant.id, AtualizarReceitaRequest(nome="bolo novo"))
    rows = (await db.scalars(select(ReceitaVersao).where(ReceitaVersao.receita_id == row.id).order_by(ReceitaVersao.versao))).all()
    assert len(rows) == 2
    assert rows[0].origem == "base_anterior" and rows[0].usuario_id is None
    assert rows[0].snapshot["nome"] == "Bolo antigo"
    assert rows[1].snapshot["nome"] == "BOLO NOVO"


@pytest.mark.asyncio
async def test_http_autoria_paginacao_e_bloqueio_cross_tenant(client, db, monkeypatch):
    from unittest.mock import AsyncMock
    from core.security import create_access_token
    monkeypatch.setattr(db, "commit", AsyncMock())  # rollback da fixture preserva isolamento
    tenants = [Tenant(nome="HTTP A"), Tenant(nome="HTTP B")]
    db.add_all(tenants)
    await db.flush()
    users = [Usuario(tenant_id=t.id, nome=f"Editor {n}", email=f"{uuid4()}@example.test", senha_hash="synthetic") for n, t in enumerate(tenants)]
    db.add_all(users)
    await db.flush()
    def headers(user):
        return {"Authorization": "Bearer " + create_access_token(str(user.id), str(user.tenant_id))}
    data = dict(nome="bolo novo", categoria="Bolo", rendimento="1", rendimento_unidade="un", ingredientes=[], etapas=[])
    bad = await client.post("/api/v1/receitas", json={**data, "nome": "Bolo 🍰"}, headers=headers(users[0]))
    assert bad.status_code == 422
    created = await client.post("/api/v1/receitas", json=data, headers=headers(users[0]))
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    changed = await client.patch(f"/api/v1/receitas/{rid}", json={"nome": "bolo editado", "versao": 1}, headers=headers(users[0]))
    assert changed.status_code == 200 and changed.json()["versao"] == 2
    conflict = await client.patch(f"/api/v1/receitas/{rid}", json={"nome": "Não salvar", "versao": 1}, headers=headers(users[0]))
    assert conflict.status_code == 409
    path = f"/api/v1/receitas/{rid}/versoes"
    result = await client.get(path, params={"limit": 1}, headers=headers(users[0]))
    assert result.status_code == 200
    assert len(result.json()) == 1 and result.json()[0]["versao"] == 2
    assert result.json()[0]["responsavel"] == "Editor 0"
    older = await client.get(path, params={"offset": 1, "limit": 1}, headers=headers(users[0]))
    assert older.json()[0]["snapshot"]["nome"] == "BOLO NOVO"
    assert (await client.get(path, headers=headers(users[1]))).status_code == 404
    assert (await client.get(path)).status_code in (401, 403)
    users[0].ativo = False
    await db.flush()
    assert (await client.get(path, headers=headers(users[0]))).status_code == 401


@pytest.mark.asyncio
async def test_limpeza_legado_preview_aplicacao_idempotencia(db):
    from scripts.padronizar_nomes_cadastro import padronizar
    from infrastructure.database.models import Receita, Ingrediente
    from infrastructure.database.compras_models import ProdutoCompra
    tenant = Tenant(nome="QA limpeza")
    outro = Tenant(nome="QA intocado")
    db.add_all([tenant, outro])
    await db.flush()
    material = Ingrediente(tenant_id=tenant.id, codigo=1, nome="Ingrediente", unidade="g")
    db.add(material)
    await db.flush()
    receita = Receita(tenant_id=tenant.id, nome="Bolo 🍰", categoria="Bolo", rendimento=1, rendimento_unidade="un", margem_desejada=0.3)
    invalida = Receita(tenant_id=tenant.id, nome="🍰", categoria="Bolo", rendimento=1, rendimento_unidade="un", margem_desejada=0.3)
    intocada = Receita(tenant_id=outro.id, nome="Outro 🍰", categoria="Bolo", rendimento=1, rendimento_unidade="un", margem_desejada=0.3)
    produto = ProdutoCompra(tenant_id=tenant.id, ingrediente_id=material.id, nome="Chocolate 🍫", marca="Marca", conteudo_embalagem=1, unidade_conteudo="g")
    db.add_all([receita, invalida, intocada, produto])
    await db.flush()
    preview = await padronizar(db, tenant.id)
    assert len(preview) == 3 and receita.nome == "Bolo 🍰" and produto.revisao == 1
    applied = await padronizar(db, tenant.id, True)
    assert preview == applied
    assert receita.nome == "BOLO" and receita.versao == 2
    assert produto.nome == "CHOCOLATE" and produto.revisao == 2
    assert invalida.nome == "🍰" and intocada.nome == "Outro 🍰"
    again = await padronizar(db, tenant.id, True)
    assert len(again) == 1 and "erro" in again[0] and receita.versao == 2
    rows = (await db.scalars(select(ReceitaVersao).where(ReceitaVersao.receita_id == receita.id).order_by(ReceitaVersao.versao))).all()
    assert [r.snapshot["nome"] for r in rows] == ["Bolo 🍰", "BOLO"]


@pytest.mark.asyncio
async def test_rollback_da_edicao_reverte_historico(db):
    tenant = Tenant(nome="QA rollback")
    db.add(tenant)
    await db.flush()
    service = ReceitaService(ReceitaRepository(db), db)
    row = await service.criar(tenant.id, CriarReceitaRequest(nome="bolo", categoria="Bolo", rendimento=1, rendimento_unidade="un", ingredientes=[], etapas=[]))
    rid, tid = row.id, tenant.id
    transaction = await db.begin_nested()
    await service.atualizar(rid, tid, AtualizarReceitaRequest(nome="Novo", versao=1))
    await transaction.rollback()
    restored = await service.buscar(rid, tid)
    assert restored.versao == 1 and restored.nome == "BOLO"
    assert len((await db.scalars(select(ReceitaVersao).where(ReceitaVersao.receita_id == rid))).all()) == 1
