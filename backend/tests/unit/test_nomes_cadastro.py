from uuid import uuid4

import pytest
from pydantic import ValidationError

from domain.nomes import nome_cadastro, padronizar_nome_existente
from domain.receitas.schemas import AtualizarReceitaRequest, CriarReceitaRequest
from domain.compras.comercial_schemas import ProdutoCriar, ProdutoEditar


@pytest.mark.parametrize("nome", [" bolo 🍰", "Chocolate ❤️", "Bolo 👩‍🍳", "Brasil 🇧🇷", "Lote 1️⃣", "a\u200bb", "a\nb", " ", "a" * 201])
def test_rejeita_nomes_invalidos(nome):
    with pytest.raises(ValueError):
        nome_cadastro(nome)
    with pytest.raises(ValidationError):
        AtualizarReceitaRequest(nome=nome)
    with pytest.raises(ValidationError):
        ProdutoEditar(revisao=1, nome=nome)


def test_normalizacao_apenas_nome():
    texto = "Misture suavemente 🍰\n\n  Preserve espaços."
    receita = CriarReceitaRequest(nome="  seduc\u0327a\u0303o  de chocolate ", categoria="Copo", rendimento="1", rendimento_unidade="un", ingredientes=[], etapas=[], modo_preparo=texto)
    assert receita.nome == "SEDUÇÃO DE CHOCOLATE"
    assert receita.modo_preparo == texto
    produto = ProdutoCriar(nome="  leite integral ", marca="Marca", conteudo_embalagem="1", unidade_conteudo="l", ingrediente_id=uuid4())
    assert produto.nome == "LEITE INTEGRAL"
    assert produto.marca == "Marca"
    assert nome_cadastro("água 20°C / 50%") == "ÁGUA 20°C / 50%"
    assert AtualizarReceitaRequest().model_fields_set == set()


def test_limpeza_legado_nao_inventa_nome():
    assert padronizar_nome_existente("Bolo 👩‍🍳 de 🍫") == "BOLO DE"
    with pytest.raises(ValueError):
        padronizar_nome_existente("🍰")
