import json
from datetime import date
from uuid import uuid4

import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as SchemaError
from starlette.requests import Request

from core.validation import schema_issues
from domain.agenda.schemas import CriarAgendaItemRequest
from domain.compras.comercial_schemas import CompraRevisada
from domain.exceptions import ValidationError
from domain.receitas.ficha_tecnica import FichaTecnicaInput, PassoMontagem
from main import central_validation_handler, validation_handler


@pytest.mark.asyncio
async def test_request_errors_include_nested_fields_without_private_input():
    request = Request({"type": "http", "path": "/api/v1/compras/v2/prever", "headers": []})
    error = RequestValidationError(
        [
            {
                "type": "string_too_short",
                "loc": ("body", "itens", 1, "produto_novo", "marca"),
                "msg": "String should have at least 1 character",
                "input": "PRIVATE_INPUT",
                "ctx": {"min_length": 1},
            }
        ]
    )
    response = await central_validation_handler(request, error)
    body = json.loads(response.body)
    assert response.status_code == 422
    assert body["field_errors"] == [
        {
            "path": "itens.1.produto_novo.marca",
            "message": "Informe pelo menos 1 caractere(s).",
        }
    ]
    assert b"PRIVATE_INPUT" not in response.body
    assert b"String should" not in response.body


@pytest.mark.asyncio
async def test_domain_validation_preserves_field():
    request = Request({"type": "http", "path": "/api/v1/auth/whatsapp", "headers": []})
    response = await validation_handler(
        request, ValidationError("Informe um número válido", field="telefone")
    )
    assert json.loads(response.body)["field_errors"][0]["path"] == "telefone"


def test_agenda_cross_field_rule_points_to_end_time():
    with pytest.raises(SchemaError) as result:
        CriarAgendaItemRequest(
            titulo="Tarefa", tipo="tarefa", data=date.today(), hora_inicio="10:00", hora_fim="09:00"
        )
    assert schema_issues(result.value.errors())[0]["path"] == "hora_fim"


def test_quantity_range_points_to_missing_limit():
    with pytest.raises(SchemaError) as result:
        PassoMontagem(
            descricao="Camada",
            tipo="componente",
            quantidade="10",
            quantidade_minima="5",
            unidade="g",
        )
    assert schema_issues(result.value.errors())[0]["path"] == "quantidade_maxima"


def test_composition_missing_link_preserves_step_index():
    with pytest.raises(SchemaError) as result:
        FichaTecnicaInput(
            descricao_produto="Produto",
            revisao=0,
            composicao_ativa=True,
            passos=[dict(descricao="Camada", tipo="componente", quantidade=10, unidade="g")],
        )
    assert schema_issues(result.value.errors())[0]["path"] == "passos.0.receita_base_id"


def test_purchase_selection_errors_identify_material():
    with pytest.raises(SchemaError) as result:
        CompraRevisada(
            itens=[
                dict(
                    nome="Material",
                    tipo="ingrediente",
                    criar_novo=False,
                    descricao_original="Cupom",
                    quantidade=1,
                    unidade="un",
                    custo_unitario=1,
                    preco_total=1,
                )
            ]
        )
    assert schema_issues(result.value.errors())[0]["path"] == "itens.0.ingrediente_id"


def test_multiple_product_fields_preserved():
    with pytest.raises(SchemaError) as result:
        CompraRevisada(
            itens=[
                dict(
                    nome="Material",
                    tipo="ingrediente",
                    ingrediente_id=uuid4(),
                    descricao_original="Cupom",
                    quantidade=1,
                    unidade="un",
                    custo_unitario=1,
                    preco_total=1,
                    produto_novo=dict(
                        nome="Produto", marca="", conteudo_embalagem="1", unidade_conteudo=""
                    ),
                )
            ]
        )
    paths = {issue["path"] for issue in schema_issues(result.value.errors())}
    assert "itens.0.produto_novo.marca" in paths
    assert "itens.0.produto_novo.unidade_conteudo" in paths
