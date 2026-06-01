"""
Testes do fluxo de compras via OCR (Sprint 3).

Usa um adapter de OCR falso (sem chamar a API externa) e o EstoqueService real,
validando: sugestão de match, entrada que recalcula custo médio, cadastro de
item novo, erro de item sem vínculo e isolamento por tenant.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from domain.compras.schemas import ConfirmarCompraRequest, ItemConfirmado
from domain.compras.service import ComprasService
from domain.estoque.repository import EstoqueRepository
from domain.estoque.schemas import CriarIngredienteRequest
from domain.estoque.service import EstoqueService
from domain.exceptions import ValidationError
from infrastructure.database.models import Tenant
from infrastructure.ocr.gemma_adapter import ItemOCR, ResultadoOCR


class FakeOCRAdapter:
    """Adapter de OCR determinístico para os testes."""

    def __init__(self, resultado: ResultadoOCR) -> None:
        self._resultado = resultado

    async def processar_imagem(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> ResultadoOCR:
        return self._resultado


def _resultado_padrao() -> ResultadoOCR:
    return ResultadoOCR(
        itens=[
            ItemOCR(
                descricao="ACUCAR CRISTAL UNIAO 1KG",
                quantidade=2.0,
                unidade="un",
                preco_unitario=4.0,
                preco_total=8.0,
            ),
            ItemOCR(
                descricao="Sacola Plastica Reforcada",
                quantidade=1.0,
                unidade="pct",
                preco_unitario=10.0,
                preco_total=10.0,
            ),
        ],
        total=18.0,
        estabelecimento="Mercado Teste",
        data=None,
        fonte="mock",
        confianca=0.0,
    )


@pytest_asyncio.fixture
async def tenant_id(db: AsyncSession):
    tenant = Tenant(nome="Confeitaria")
    db.add(tenant)
    await db.flush()
    return tenant.id


@pytest_asyncio.fixture
async def estoque(db: AsyncSession) -> EstoqueService:
    return EstoqueService(EstoqueRepository(db))


@pytest_asyncio.fixture
async def compras(estoque: EstoqueService) -> ComprasService:
    return ComprasService(estoque, FakeOCRAdapter(_resultado_padrao()))


@pytest.mark.asyncio
async def test_processar_ocr_sugere_match_e_item_novo(
    estoque: EstoqueService, compras: ComprasService, tenant_id
):
    # Ingrediente que deve casar com o primeiro item do cupom.
    acucar = await estoque.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Açúcar Cristal",
            unidade="kg",
            estoque_inicial=Decimal("2"),
            custo_inicial=Decimal("3"),
        ),
    )

    resposta = await compras.processar_ocr(tenant_id, b"fake-bytes")

    assert len(resposta.itens) == 2
    item_acucar, item_sacola = resposta.itens

    # 1º item: vinculado ao açúcar existente.
    assert item_acucar.ingrediente_id == acucar.id
    assert item_acucar.nome_match == "Açúcar Cristal"

    # 2º item: sem correspondente, categorizado como embalagem.
    assert item_sacola.ingrediente_id is None
    assert item_sacola.tipo_sugerido == "embalagem"


@pytest.mark.asyncio
async def test_confirmar_atualiza_existente_e_cria_novo(
    estoque: EstoqueService, compras: ComprasService, tenant_id
):
    acucar = await estoque.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Açúcar Cristal",
            unidade="kg",
            estoque_inicial=Decimal("2"),
            custo_inicial=Decimal("3"),
        ),
    )

    req = ConfirmarCompraRequest(
        itens=[
            # Entrada no existente: 2kg × R$4 → média = (2×3 + 2×4)/4 = 3,5
            ItemConfirmado(
                ingrediente_id=acucar.id,
                criar_novo=False,
                nome="Açúcar Cristal",
                tipo="ingrediente",
                unidade="kg",
                quantidade=Decimal("2"),
                custo_unitario=Decimal("4"),
            ),
            # Item novo
            ItemConfirmado(
                criar_novo=True,
                nome="Sacola Plástica",
                tipo="embalagem",
                unidade="un",
                quantidade=Decimal("1"),
                custo_unitario=Decimal("10"),
            ),
        ]
    )

    resultado = await compras.confirmar(tenant_id, req)

    assert resultado.ingredientes_atualizados == 1
    assert resultado.ingredientes_criados == 1

    atualizado = await estoque.buscar(acucar.id, tenant_id)
    assert atualizado.estoque_atual == Decimal("4.0000")
    assert atualizado.custo_medio == Decimal("3.5000")

    # O novo ingrediente aparece na listagem do tenant.
    nomes = {i.nome for i in await estoque.listar(tenant_id)}
    assert "Sacola Plástica" in nomes


@pytest.mark.asyncio
async def test_confirmar_item_sem_vinculo_falha(
    compras: ComprasService, tenant_id
):
    req = ConfirmarCompraRequest(
        itens=[
            ItemConfirmado(
                ingrediente_id=None,
                criar_novo=False,  # nem vincula nem cria → inválido
                nome="Item órfão",
                tipo="ingrediente",
                unidade="kg",
                quantidade=Decimal("1"),
                custo_unitario=Decimal("5"),
            )
        ]
    )
    with pytest.raises(ValidationError):
        await compras.confirmar(tenant_id, req)


@pytest.mark.asyncio
async def test_isolamento_tenant_no_match(
    estoque: EstoqueService, compras: ComprasService, tenant_id
):
    # Açúcar de OUTRO tenant não deve ser sugerido como match.
    outro_tenant = uuid4()
    await estoque.criar_ingrediente(
        outro_tenant,
        CriarIngredienteRequest(nome="Açúcar Cristal", unidade="kg"),
    )

    resposta = await compras.processar_ocr(tenant_id, b"fake-bytes")
    # Nenhum ingrediente do tenant atual → nenhum match.
    assert all(item.ingrediente_id is None for item in resposta.itens)


@pytest.mark.asyncio
async def test_lista_reposicao_so_inclui_abaixo_do_minimo(
    estoque: EstoqueService, compras: ComprasService, tenant_id
):
    # Precisa repor: saldo 2 ≤ mínimo 5.
    await estoque.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Chocolate",
            unidade="kg",
            estoque_minimo=Decimal("5"),
            estoque_inicial=Decimal("2"),
            custo_inicial=Decimal("30"),
        ),
    )
    # Não precisa repor: saldo 10 > mínimo 1.
    await estoque.criar_ingrediente(
        tenant_id,
        CriarIngredienteRequest(
            nome="Sal",
            unidade="kg",
            estoque_minimo=Decimal("1"),
            estoque_inicial=Decimal("10"),
            custo_inicial=Decimal("2"),
        ),
    )

    lista = await compras.lista_reposicao(tenant_id)

    nomes = [i.nome for i in lista.itens]
    assert nomes == ["Chocolate"]
    item = lista.itens[0]
    # alvo = 2 × mínimo (10), saldo 2 → comprar 8; custo 8 × R$30 = R$240
    assert item.quantidade_sugerida == Decimal("8.0000")
    assert item.custo_estimado == Decimal("240.00")
    assert lista.custo_total_estimado == Decimal("240.00")


@pytest.mark.asyncio
async def test_lista_reposicao_isolada_por_tenant(
    estoque: EstoqueService, compras: ComprasService, tenant_id
):
    outro = uuid4()
    await estoque.criar_ingrediente(
        outro,
        CriarIngredienteRequest(
            nome="Farinha",
            unidade="kg",
            estoque_minimo=Decimal("5"),
            estoque_inicial=Decimal("0"),
        ),
    )
    lista = await compras.lista_reposicao(tenant_id)
    assert lista.itens == []
