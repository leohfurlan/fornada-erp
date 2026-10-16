"""Safe diagnostics at the Talk2Me HTTP boundary; synthetic purchases only."""

import pytest
from sqlalchemy import func, select

from infrastructure.database.compras_models import Compra, FornecedorCompra, ProdutoCompra
from infrastructure.database.models import MovimentacaoEstoque
from tests.integration.test_central_guards import purchase as purchase


def item(material, **changes):
    return {
        "ingrediente_id": str(material.id),
        "descricao_original": "FARINHA",
        "quantidade": "2",
        "unidade": "kg",
        "custo_unitario": "10",
        "preco_total": "20",
        "aceitar_excecao": True,
    } | changes


@pytest.mark.parametrize(
    "changes,code,field",
    [
        ({"aprovar_produto": True}, "product_required", "produto_id"),
        ({"unidade": "l"}, "fiscal_conversion_required", "unidade"),
        ({"preco_total": "19"}, "item_total_mismatch", "preco_total"),
        ({"aceitar_excecao": False}, "product_approval_required", "aprovar_produto"),
        (
            {
                "produto_novo": {
                    "nome": "Farinha",
                    "marca": "",
                    "conteudo_embalagem": "1",
                    "unidade_conteudo": "kg",
                }
            },
            "brand_required",
            "produto_novo.marca",
        ),
        (
            {
                "produto_novo": {
                    "nome": "Farinha",
                    "marca": "Sintética",
                    "conteudo_embalagem": "1",
                    "unidade_conteudo": "l",
                }
            },
            "content_conversion_required",
            "produto_novo.unidade_conteudo",
        ),
        (
            {
                "descricao_original": "CHOCOLATE BRANCO 1KG",
                "produto_novo": {
                    "nome": "Chocolate",
                    "marca": "Sintética",
                    "variante": "ao leite",
                    "conteudo_embalagem": "1",
                    "unidade_conteudo": "kg",
                },
            },
            "variant_mismatch",
            "produto_novo.variante",
        ),
        (
            {
                "descricao_original": "FARINHA 500G",
                "produto_novo": {
                    "nome": "Farinha",
                    "marca": "Sintética",
                    "conteudo_embalagem": "1",
                    "unidade_conteudo": "kg",
                },
            },
            "package_mismatch",
            "produto_novo.conteudo_embalagem",
        ),
    ],
)
async def test_item_errors_preserve_position_and_proposal(purchase, db, changes, code, field):
    post, proposal, decision, _, _, material, _ = purchase
    before = (await post("draft", proposal)).json()
    response = await post(
        "review",
        proposal
        | {
            "expected_version": decision["expected_version"],
            "reviewed": {"itens": [item(material), item(material, **changes)]},
        },
    )
    assert response.status_code == 422, response.text
    issue = response.json()["detail"]["errors"][0]
    assert (issue["code"], issue["item_index"], issue["field"]) == (code, 1, field)
    after = (await post("draft", proposal)).json()
    assert (after["version"], after["summary_hash"], after["reviewed"]) == (
        before["version"],
        before["summary_hash"],
        before["reviewed"],
    )


async def test_selected_grouped_items_prepare_without_catalog_or_stock_writes(purchase, db):
    post, proposal, decision, _, _, material, tenant = purchase
    models = [Compra, ProdutoCompra, FornecedorCompra, MovimentacaoEstoque]

    async def counts():
        return [
            await db.scalar(
                select(func.count()).select_from(model).where(model.tenant_id == tenant.id)
            )
            for model in models
        ]

    before = await counts()
    response = await post(
        "review",
        proposal
        | {
            "expected_version": decision["expected_version"],
            "reviewed": {
                "total_nota": "100",
                "itens": [item(material, quantidade="3", desconto_item="2", preco_total="28")],
            },
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["preview"]["total_selecionado"] == "28"
    assert response.json()["preview"]["itens"][0]["quantidade_principal"] == "3"
    assert await counts() == before
    await db.refresh(material)
    assert material.estoque_atual == 0


async def test_stale_proposal_has_refresh_instruction(purchase):
    post, proposal, _, _, _, material, _ = purchase
    response = await post(
        "review", proposal | {"expected_version": 1, "reviewed": {"itens": [item(material)]}}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["errors"][0]["code"] == "proposal_version_changed"


@pytest.mark.parametrize(
    "change,code",
    [("version", "product_version_changed"), ("material", "product_material_mismatch")],
)
async def test_existing_product_checks_version_and_material(purchase, db, change, code):
    post, proposal, decision, _, _, material, tenant = purchase

    product = ProdutoCompra(
        tenant_id=tenant.id,
        ingrediente_id=material.id,
        nome="Farinha",
        marca="Sintética",
        conteudo_embalagem=1,
        unidade_conteudo="kg",
        revisao=2,
    )
    db.add(product)
    await db.commit()
    reviewed_item = item(
        material, produto_id=str(product.id), produto_revisao=1 if change == "version" else 2
    )
    if change == "material":
        other = type(material)(tenant_id=tenant.id, codigo=2, nome="Outro material", unidade="kg")
        db.add(other)
        await db.commit()
        reviewed_item["ingrediente_id"] = str(other.id)
    response = await post(
        "review",
        proposal
        | {
            "expected_version": decision["expected_version"],
            "reviewed": {"itens": [reviewed_item]},
        },
    )
    assert response.status_code == (409 if change == "version" else 422)
    assert response.json()["detail"]["errors"][0]["code"] == code


async def test_new_product_and_supplier_remain_proposals_until_customer_approval(purchase, db):
    post, proposal, decision, _, _, material, tenant = purchase
    response = await post(
        "review",
        proposal
        | {
            "expected_version": decision["expected_version"],
            "reviewed": {
                "fornecedor_novo": {"nome": "Loja sintética"},
                "itens": [
                    item(
                        material,
                        unidade="un",
                        quantidade="3",
                        desconto_item="2",
                        preco_total="28",
                        aceitar_excecao=False,
                        produto_novo={
                            "nome": "Farinha",
                            "marca": "Sintética",
                            "conteudo_embalagem": "500",
                            "unidade_conteudo": "g",
                        },
                        aprovar_produto=True,
                        aprovar_fornecedor=True,
                    )
                ],
            },
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "awaiting_approval"
    assert response.json()["preview"]["itens"][0]["quantidade_principal"] == "1.500"
    for model in (ProdutoCompra, FornecedorCompra, Compra, MovimentacaoEstoque):
        assert (
            await db.scalar(
                select(func.count()).select_from(model).where(model.tenant_id == tenant.id)
            )
            == 0
        )


async def test_schema_error_does_not_echo_unknown_keys_or_input(purchase):
    post, proposal, decision, _, _, material, _ = purchase
    response = await post(
        "review",
        proposal
        | {
            "expected_version": decision["expected_version"],
            "reviewed": {"itens": [item(material, **{"PRIVATE-KEY": "PRIVATE-VALUE"})]},
        },
    )
    assert response.status_code == 422
    assert "PRIVATE" not in response.text
    assert response.json()["detail"]["errors"][0]["item_index"] == 0


async def test_store_approval_without_store_identifies_item_and_action(purchase):
    post, proposal, decision, _, _, material, _ = purchase
    response = await post(
        "review",
        proposal
        | {
            "expected_version": decision["expected_version"],
            "reviewed": {
                "itens": [
                    {
                        "ingrediente_id": str(material.id),
                        "descricao_original": "FARINHA",
                        "quantidade": "2",
                        "unidade": "kg",
                        "custo_unitario": "10",
                        "preco_total": "20",
                        "aceitar_excecao": True,
                        "aprovar_fornecedor": True,
                    }
                ]
            },
        },
    )
    assert response.status_code == 422
    issue = response.json()["detail"]["errors"][0]
    assert issue["code"] == "supplier_required"
    assert issue["item_index"] == 0
    assert issue["field"] == "fornecedor_id"
    assert issue["action"] == "select_supplier"


@pytest.mark.parametrize(
    "case", ["renew", "implicit", "invalid", "stale", "scope", "confirmed", "operation"]
)
async def test_expired_review_renewal_requires_valid_explicit_scoped_review(purchase, db, case):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID, uuid4

    from infrastructure.database.central_models import CentralCompra

    post, proposal, decision, _, _, material, _ = purchase
    if case == "renew":
        assert (await post("decision", decision)).status_code == 200
    row = await db.get(CentralCompra, UUID(proposal["proposal_id"]))
    row.expira_em = datetime.now(UTC) - timedelta(days=1)
    if case == "confirmed":
        row.estado = "confirmed"
    if case == "operation":
        row.operation_id = uuid4()
    await db.commit()
    before = (row.revisao, row.expira_em, row.resumo_hash, row.aprovacao_ref)
    payload = proposal | {
        "expected_version": row.revisao,
        "renew_expired": True,
        "reviewed": {"itens": [item(material)]},
    }
    if case == "implicit":
        del payload["renew_expired"]
    if case == "invalid":
        payload["reviewed"]["itens"][0]["preco_total"] = "19"
    if case == "stale":
        payload["expected_version"] -= 1
    if case == "scope":
        payload["scope"] = {"tenant_id": str(uuid4()), "company_id": None}
    response = await post("review", payload)
    await db.refresh(row)
    if case == "renew":
        assert response.status_code == 200, response.text
        assert row.expira_em > datetime.now(UTC) + timedelta(hours=23)
        assert row.estado == "awaiting_approval" and row.revisao == before[0] + 1
        assert row.aprovacao_ref is None and row.aprovacao_message_id is None
        assert (
            row.revisada == payload["reviewed"] or row.revisada["itens"][0]["preco_total"] == "20"
        )
        assert (await post("decision", decision)).status_code == 409
    else:
        assert response.status_code == (
            403 if case == "scope" else 422 if case == "invalid" else 409
        ), response.text
        assert (row.revisao, row.expira_em, row.resumo_hash, row.aprovacao_ref) == before
    await db.refresh(material)
    assert material.estoque_atual == 0
