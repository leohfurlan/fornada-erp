from types import SimpleNamespace
from uuid import uuid4

import pytest

from domain.compras.conversation import Edit, patch, reviewed, seed


def receipt(items):
    return SimpleNamespace(id=uuid4(), dialogo=None, revisada={"itens": items}, leitura={})


def item(**changes):
    return {
        "descricao_original": "LEITE",
        "quantidade": "1",
        "custo_unitario": "6.29",
        "preco_total": "5.48",
        "desconto_item": "0.81",
        "produto_novo": None,
    } | changes


def test_groups_only_consistent_identical_lines():
    first, invalid = seed(receipt([item(), item(), item(preco_total="1")]))["draft"]["itens"]
    assert first["occurrences"] == 2
    assert first["quantidade"] == "2"
    assert first["desconto_item"] == "1.62"
    assert first["preco_total"] == "10.96"
    assert invalid["occurrences"] == 1


def test_edits_are_atomic_scoped_and_do_not_mutate_original():
    original = seed(receipt([item()]))
    ref = original["draft"]["itens"][0]["item_ref"]
    edits = [
        Edit(op="set_item", item_ref=ref, field="quantidade", value="2"),
        Edit(op="set_item", item_ref=ref, field="ingrediente_id", value=str(uuid4())),
    ]
    with pytest.raises(ValueError, match="catálogo"):
        patch(original, edits, {"materials": [], "products": [], "suppliers": []})
    assert original["draft"]["itens"][0]["quantidade"] == "1"


def test_nullable_product_metadata_and_remove_group():
    original = seed(receipt([item(), item()]))
    ref = original["draft"]["itens"][0]["item_ref"]
    catalog = {"materials": [], "products": [], "suppliers": []}
    edited = patch(
        original,
        [Edit(op="set_item", item_ref=ref, field="produto_novo.marca", value="Marca")],
        catalog,
    )
    assert edited["draft"]["itens"][0]["produto_novo"] == {"marca": "Marca"}
    assert "item_ref" not in reviewed(edited)["itens"][0]
    assert patch(edited, [Edit(op="remove_item", item_ref=ref)], catalog)["draft"]["itens"] == []
    assert len(original["draft"]["itens"]) == 1


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0"])
def test_invalid_quantity_rejected(value):
    original = seed(receipt([item()]))
    ref = original["draft"]["itens"][0]["item_ref"]
    with pytest.raises(ValueError):
        patch(
            original,
            [Edit(op="set_item", item_ref=ref, field="quantidade", value=value)],
            {"materials": [], "products": [], "suppliers": []},
        )


def test_inconsistent_first_line_does_not_absorb_consistent_lines():
    result = seed(receipt([item(preco_total="1"), item(), item()]))["draft"]["itens"]
    assert len(result) == 2
    assert result[0]["occurrences"] == 1
    assert result[1]["occurrences"] == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"custo_unitario": "7", "preco_total": "6.19"},
        {"unidade": "l"},
        {"produto_novo": {"marca": "Outra"}},
        {"produto_novo": {"conteudo_embalagem": "2"}},
    ],
)
def test_distinct_prices_units_brands_and_packages_remain_separate(changes):
    assert len(seed(receipt([item(), item(**changes)]))["draft"]["itens"]) == 2


def test_equivalent_decimal_and_text_representations_group():
    result = seed(receipt([item(), item(custo_unitario="6.290", descricao_original=" leite ")]))
    assert result["draft"]["itens"][0]["occurrences"] == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("unidade", True),
        ("ingrediente_id", 3),
        ("produto_revisao", True),
        ("quantidade", 2),
        ("unknown", "x"),
    ],
)
def test_edit_rejects_unknown_fields_and_wrong_types(field, value):
    with pytest.raises(ValueError):
        Edit(op="set_item", item_ref=str(uuid4()), field=field, value=value)


def test_material_selection_clears_old_product_and_uses_catalog_unit():
    source = seed(receipt([item(produto_novo={"marca": "Old"}, produto_id=str(uuid4()))]))
    ref = source["draft"]["itens"][0]["item_ref"]
    mid = str(uuid4())
    result = patch(
        source,
        [Edit(op="set_item", item_ref=ref, field="ingrediente_id", value=mid)],
        {"materials": [{"id": mid, "unit": "kg"}], "products": [], "suppliers": []},
    )
    changed = result["draft"]["itens"][0]
    assert changed["unidade_principal"] == "kg"
    assert changed["produto_id"] is None and "produto_novo" not in changed


def test_comma_decimal_normalized_and_removed_item_is_auditable():
    source = seed(receipt([item(), item()]))
    ref = source["draft"]["itens"][0]["item_ref"]
    cat = {"materials": [], "products": [], "suppliers": []}
    changed = patch(
        source, [Edit(op="set_item", item_ref=ref, field="desconto_item", value="3,24")], cat
    )
    assert changed["draft"]["itens"][0]["desconto_item"] == "3.24"
    removed = patch(changed, [Edit(op="remove_item", item_ref=ref)], cat)
    assert removed["removed"][0]["occurrences"] == 2
    assert removed["removed"][0]["item_ref"] == ref


def test_patch_regroups_equivalent_items_without_reusing_removed_reference():
    source = seed(receipt([item(), item(custo_unitario="7", preco_total="6.19")]))
    ref = source["draft"]["itens"][1]["item_ref"]
    result = patch(
        source,
        [
            Edit(op="set_item", item_ref=ref, field="custo_unitario", value="6.29"),
            Edit(op="set_item", item_ref=ref, field="preco_total", value="5.48"),
        ],
        {"materials": [], "products": [], "suppliers": []},
    )
    assert len(result["draft"]["itens"]) == 1
    assert result["draft"]["itens"][0]["occurrences"] == 2
    assert result["merged"][0]["item_ref"] == ref


def test_seed_preserves_receipt_context_and_does_not_infer_litres_as_kg():
    row = receipt([])
    row.revisada = None
    row.leitura = {
        "estabelecimento": "Loja",
        "fornecedor_id": str(uuid4()),
        "total_nota": "10",
        "itens": [{"descricao": "Leite", "unidade": "l", "unidade_sugerida": "kg"}],
    }
    draft = seed(row)["draft"]
    assert draft["itens"][0]["unidade_principal"] == "l"
    assert draft["total_nota"] == "10" and "fornecedor_novo" not in draft


def test_one_cent_inconsistent_line_does_not_contaminate_valid_group():
    result = seed(receipt([item(preco_total="5.47"), item(), item()]))["draft"]["itens"]
    assert len(result) == 2
    assert result[0]["occurrences"] == 1 and result[1]["occurrences"] == 2


def test_catalog_product_selection_and_brand_edit_create_proposal_only():
    mid, pid = str(uuid4()), str(uuid4())
    source = seed(receipt([item()]))
    ref = source["draft"]["itens"][0]["item_ref"]
    cat = {
        "materials": [{"id": mid, "unit": "l"}],
        "products": [
            {
                "id": pid,
                "ingrediente_id": mid,
                "revisao": 3,
                "nome": "Leite",
                "marca": "Original",
                "conteudo_embalagem": "1",
                "unidade_conteudo": "l",
            }
        ],
        "suppliers": [],
    }
    selected = patch(
        source, [Edit(op="set_item", item_ref=ref, field="produto_id", value=pid)], cat
    )
    current = selected["draft"]["itens"][0]
    assert current["ingrediente_id"] == mid and current["produto_revisao"] == 3
    assert current["unidade_principal"] == "l"
    changed = patch(
        selected, [Edit(op="set_item", item_ref=ref, field="produto_novo.marca", value="Nova")], cat
    )
    assert changed["draft"]["itens"][0]["produto_id"] is None
    assert changed["draft"]["itens"][0]["produto_novo"]["marca"] == "Nova"
    assert cat["products"][0]["marca"] == "Original"


def test_supplier_selection_and_new_supplier_are_mutually_exclusive():
    sid = str(uuid4())
    source = seed(receipt([item()]))
    source["draft"]["fornecedor_novo"] = {"nome": "Antiga"}
    cat = {"materials": [], "products": [], "suppliers": [{"id": sid}]}
    selected = patch(source, [Edit(op="set_purchase", field="fornecedor_id", value=sid)], cat)
    assert "fornecedor_novo" not in selected["draft"]
    new = patch(
        selected, [Edit(op="set_purchase", field="fornecedor_novo.nome", value="Nova")], cat
    )
    assert new["draft"]["fornecedor_id"] is None
    assert new["draft"]["fornecedor_novo"]["nome"] == "Nova"
