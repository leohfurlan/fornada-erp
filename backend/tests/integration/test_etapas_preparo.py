import pytest
from domain.configuracoes.repository import ConfiguracoesRepository
from domain.configuracoes.schemas import CriarEtapaPadraoRequest, EtapaPadraoResponse
from infrastructure.database.models import Tenant


@pytest.mark.asyncio
async def test_etapa_sem_tempo_preserva_instrucao_e_origem_por_tenant(db):
    tenant = Tenant(nome="Preparo")
    outro = Tenant(nome="Outro")
    db.add_all([tenant, outro])
    await db.flush()
    repo = ConfiguracoesRepository(db)
    etapa = await repo.criar_etapa(tenant.id, CriarEtapaPadraoRequest(nome="Misturar", instrucao="Misture até ficar homogêneo.", receita_origem="Massa branca"))
    response = EtapaPadraoResponse.model_validate(etapa)
    assert response.duracao_minutos_default is None
    assert response.instrucao == "Misture até ficar homogêneo."
    assert response.receita_origem == "Massa branca"
    assert await repo.listar_etapas(outro.id) == []
