"""Turn a complete reading into an approval proposal, without writing the catalog."""

import json
from decimal import ROUND_HALF_UP, Decimal

from domain.compras.comercial_schemas import (
    CompraRevisada,
    FornecedorCriar,
    ItemRevisado,
    ProdutoDados,
)
from domain.compras.identificadores import normalizar_descricao
from domain.exceptions import ValidationError


def fail(message):
    raise ValidationError(message)


def propose_purchase(reading, products, materials, suppliers):
    if reading.aviso_mock or reading.avisos or not reading.itens or not reading.total_nota:
        fail("Confira os campos ilegíveis e a soma do cupom antes do resumo.")
    if not reading.estabelecimento or not reading.data_compra:
        fail("Informe a loja e a data legíveis no cupom.")
    supplier = reading.fornecedor_id
    if not supplier:
        matches = [
            f
            for f in suppliers
            if (reading.cnpj_observado and f.cnpj == reading.cnpj_observado)
            or normalizar_descricao(f.nome) == normalizar_descricao(reading.estabelecimento)
        ]
        if len(matches) > 1:
            fail("Há mais de uma loja correspondente; escolha a loja.")
        supplier = matches[0].id if matches else None
    by_material = {m.id: m for m in materials}
    items = []
    for item in reading.itens:
        values = (item.quantidade, item.preco_unitario, item.preco_total)
        if any(v is None or not v.is_finite() or v <= 0 for v in values) or not item.unidade:
            fail("Confira quantidade, unidade e valores do item: " + item.descricao)
        discount = item.desconto_item or Decimal(0)
        if (
            discount < 0
            or not discount.is_finite()
            or (item.quantidade * item.preco_unitario - discount).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            )
            != item.preco_total
        ):
            fail("Quantidade, preço e total não conferem: " + item.descricao)
        if item.reconhecimento == "conflito":
            fail("Há conflito de produto: " + item.descricao)
        product = None
        if item.produto_id and item.reconhecimento in {
            "gtin_confirmado",
            "descricao",
            "codigo_loja",
        }:
            matches = [
                p for p in products if p.id == item.produto_id and p.revisao == item.produto_revisao
            ]
        else:
            matches = [
                p
                for p in products
                if normalizar_descricao(p.nome) == normalizar_descricao(item.descricao)
                and item.marca_observada
                and normalizar_descricao(p.marca) == normalizar_descricao(item.marca_observada)
                and p.conteudo_embalagem == item.conteudo_observado
                and p.unidade_conteudo == item.unidade_conteudo_observada
            ]
        if len(matches) > 1:
            fail("Há mais de um produto correspondente: " + item.descricao)
        product = matches[0] if matches else None
        material = by_material.get(product.ingrediente_id) if product else None
        if product and not material:
            fail("O material do produto precisa ser revisado.")
        if not product:
            exact = [
                m
                for m in materials
                if normalizar_descricao(m.nome) == normalizar_descricao(item.descricao)
            ]
            if len(exact) > 1 or (item.ingrediente_id and not exact):
                fail("Confirme o material sugerido: " + item.descricao)
            material = exact[0] if exact else None
            if (
                not item.marca_observada
                or not item.conteudo_observado
                or not item.unidade_conteudo_observada
            ):
                fail("Confira a marca e o conteúdo da embalagem: " + item.descricao)
        unit = item.unidade.strip().lower()
        package_unit = (item.unidade_conteudo_observada or unit).strip().lower()
        principal = (
            material.unidade
            if material
            else {
                "g": "kg",
                "mg": "kg",
                "ml": "l",
                "und": "un",
            }.get(package_unit, package_unit)
        )
        if principal not in {"kg", "g", "mg", "l", "ml", "un", "dz", "pct", "cx", "fardo"}:
            fail("Confira a unidade de estoque: " + item.descricao)
        items.append(
            ItemRevisado(
                ingrediente_id=material.id if material else None,
                criar_novo=material is None,
                nome=material.nome if material else item.descricao[:200],
                tipo=material.tipo if material else (item.tipo_observado or item.tipo_sugerido),
                unidade_principal=principal,
                descricao_original=item.descricao,
                quantidade=item.quantidade,
                unidade=unit,
                custo_unitario=item.preco_unitario,
                desconto_item=discount,
                preco_total=item.preco_total,
                produto_id=product.id if product else None,
                produto_revisao=product.revisao if product else None,
                produto_novo=None
                if product
                else ProdutoDados(
                    nome=item.descricao[:200],
                    marca=item.marca_observada,
                    fabricante=item.fabricante_observado,
                    variante=item.variante_observada,
                    conteudo_embalagem=item.conteudo_observado,
                    unidade_conteudo=package_unit,
                ),
                codigo_loja=item.codigo_loja,
                aprovar_produto=True,
                aprovar_fornecedor=True,
                guardar_vinculo=True,
            )
        )
    # Reading retains every fiscal line; identical proposal rows share one new catalog entry.
    grouped = {}
    for item in items:
        key = json.dumps(
            item.model_dump(mode="json", exclude={"quantidade", "desconto_item", "preco_total"}),
            sort_keys=True,
        )
        if key not in grouped:
            grouped[key] = item
            continue
        previous = grouped[key]
        merged = previous.model_dump()
        for field in ("quantidade", "desconto_item", "preco_total"):
            merged[field] += getattr(item, field)
        combined = ItemRevisado.model_validate(merged)
        expected = (
            combined.quantidade * combined.custo_unitario - combined.desconto_item
        ).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        if expected != combined.preco_total:
            fail("Linhas repetidas exigem revisão do arredondamento.")
        grouped[key] = combined
    items = list(grouped.values())
    new_names = [normalizar_descricao(i.nome) for i in items if i.criar_novo]
    if len(new_names) != len(set(new_names)):
        fail("Novos materiais repetidos com condições diferentes exigem revisão.")
    if sum((i.preco_total for i in items), Decimal(0)) != reading.total_nota:
        fail("A soma dos itens difere do total do cupom.")
    return CompraRevisada(
        itens=items,
        estabelecimento=reading.estabelecimento,
        data_compra=reading.data_compra,
        total_nota=reading.total_nota,
        fornecedor_id=supplier,
        fornecedor_novo=None
        if supplier
        else FornecedorCriar(nome=reading.estabelecimento, cnpj=reading.cnpj_observado),
        origem="web_ocr",
    )
