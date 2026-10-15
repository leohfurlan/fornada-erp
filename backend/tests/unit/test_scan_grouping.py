from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domain.compras.extraction import ItemOCR, ResultadoOCR
from domain.compras.reconhecimento import ReconhecimentoCompras


def line(name, price, code, *, discount=None):
    return ItemOCR(
        name,
        Decimal(1),
        "un",
        Decimal(price),
        Decimal(price) - Decimal(discount or 0),
        codigo_loja=code,
        desconto_item=Decimal(discount) if discount else None,
    )


async def read(lines):
    repo = SimpleNamespace(
        fornecedores=AsyncMock(return_value=[]),
        produtos=AsyncMock(return_value=[]),
        aliases=AsyncMock(return_value=[]),
    )
    compras = SimpleNamespace(repo=repo, estoque=SimpleNamespace(listar=AsyncMock(return_value=[])))
    result = ResultadoOCR(lines, Decimal("50.05"), "Loja", "2026-10-02")
    ocr = SimpleNamespace(processar_imagem=AsyncMock(return_value=result))
    return await ReconhecimentoCompras(compras, ocr).ler(uuid4(), b"fixture", "image/jpeg")


@pytest.mark.asyncio
async def test_receipt_nine_lines_become_five_products_without_changing_total():
    lines = [line("REFRIG COCA COLA 310ML S/ACUCAR LT", "3.08", "coca")] * 4
    lines += [
        line("CHOC GAROTO 400G", "13.49", "choc"),
        line("PAO 200G", "12.98", "pao"),
        line("LEITE CONDENSADO 395G", "6.29", "leite", discount="0.81"),
    ]
    lines += [line("CREME DE LEITE ITALAC 200G", "2.89", "creme")] * 2
    result = await read(lines)
    assert len(result.itens) == 5
    assert result.itens[0].quantidade == 4
    assert result.itens[0].preco_total == Decimal("12.32")
    assert result.itens[0].linhas_origem == [0, 1, 2, 3]
    assert result.itens[-1].quantidade == 2
    assert result.itens[-1].preco_total == Decimal("5.78")
    assert sum(i.preco_total for i in result.itens) == Decimal("50.05")
    assert result.itens[3].desconto_item == Decimal("0.81")


@pytest.mark.asyncio
async def test_different_price_or_packaging_remains_separate():
    result = await read(
        [
            line("CREME 200G", "2.89", "creme"),
            line("CREME 200G", "3.00", "creme"),
            line("CREME 300G", "2.89", "outro"),
        ]
    )
    assert len(result.itens) == 3


@pytest.mark.asyncio
async def test_incomplete_values_are_not_inferred_or_merged():
    first = line("CREME 200G", "2.89", "creme")
    first.quantidade = None
    first.campos_pendentes = ["quantidade"]
    result = await read([first, line("CREME 200G", "2.89", "creme")])
    assert len(result.itens) == 2
    assert result.itens[0].quantidade is None


@pytest.mark.asyncio
async def test_does_not_force_grouping_when_rounding_changes_cents():
    first = line("Produto", "0.33333333", "codigo")
    first.preco_total = Decimal("0.33")
    result = await read([first, first])
    assert len(result.itens) == 2
    assert sum(item.preco_total for item in result.itens) == Decimal("0.66")
