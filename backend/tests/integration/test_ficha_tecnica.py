from decimal import Decimal
from uuid import uuid4

import pytest

from domain.exceptions import ConflictError, NotFoundError
from domain.receitas.ficha_service import FichaTecnicaService
from domain.receitas.ficha_tecnica import FichaTecnicaInput
from infrastructure.database.models import Receita, Tenant


@pytest.mark.asyncio
async def test_persistencia_isolamento_e_revisao(db):
    tenant = Tenant(nome="Ficha tenant")
    db.add(tenant)
    await db.flush()
    receita = Receita(tenant_id=tenant.id, nome="Sedução", categoria="Copo", rendimento=Decimal("1"), rendimento_unidade="un", margem_desejada=Decimal("0.3"))
    db.add(receita)
    await db.flush()
    service = FichaTecnicaService(db)
    assert (await service.buscar(receita.id, tenant.id)).passos == []
    data = FichaTecnicaInput(descricao_produto="Copo sedução", revisao=0, passos=[
        dict(descricao="Brigadeiro", tipo="componente", quantidade="30", unidade="g"),
        dict(descricao="Brownie", tipo="componente", quantidade="50", unidade="g"),
        dict(descricao="Brigadeiro", tipo="componente", quantidade="30", unidade="g"),
    ])
    salvo = await service.salvar(receita.id, tenant.id, data)
    assert salvo.revisao == 1
    leitura = await service.buscar(receita.id, tenant.id)
    assert [p.descricao for p in leitura.passos] == ["Brigadeiro", "Brownie", "Brigadeiro"]
    with pytest.raises(ConflictError):
        await service.salvar(receita.id, tenant.id, data)
    with pytest.raises(NotFoundError):
        await service.buscar(receita.id, uuid4())
    with pytest.raises(NotFoundError):
        await service.salvar(receita.id, uuid4(), data)
    from domain.receitas.repository import ReceitaRepository
    repo = ReceitaRepository(db)
    original = await repo.buscar_por_id(receita.id, tenant.id)
    copia = await repo.duplicar(original, tenant.id)
    ficha_copia = await service.buscar(copia.id, tenant.id)
    assert ficha_copia.revisao == 0
    assert ficha_copia.passos == leitura.passos
