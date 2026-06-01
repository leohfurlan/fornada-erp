"""Testes do matching de itens de cupom × ingredientes cadastrados (funções puras)."""

from domain.compras.matching import (
    LIMIAR_MATCH,
    IngredienteRef,
    normalizar_texto,
    normalizar_unidade,
    score_similaridade,
    sugerir_match,
    sugerir_tipo,
)


def test_normalizar_texto_remove_acento_e_pontuacao():
    assert normalizar_texto("Açúcar Cristal União 1kg") == "acucar cristal uniao 1kg"
    assert normalizar_texto("LEITE, INTEGRAL!!") == "leite integral"


def test_normalizar_unidade_variacoes():
    assert normalizar_unidade("KG") == "kg"
    assert normalizar_unidade("Quilos") == "kg"
    assert normalizar_unidade("UN") == "un"
    assert normalizar_unidade("unidade") == "un"
    assert normalizar_unidade("PCT") == "pct"
    # Desconhecida cai no fallback "un"
    assert normalizar_unidade("") == "un"


def test_score_alto_quando_nome_ingrediente_aparece_no_cupom():
    # Cupom verboso contém o nome do ingrediente como subconjunto.
    s = score_similaridade("ACUCAR CRISTAL UNIAO 1KG", "Açúcar Cristal")
    assert s >= LIMIAR_MATCH


def test_score_baixo_para_produtos_diferentes():
    s = score_similaridade("Detergente Ype 500ml", "Açúcar Cristal")
    assert s < LIMIAR_MATCH


def test_sugerir_tipo_embalagem():
    assert sugerir_tipo("Caixa para bolo 25cm") == "embalagem"
    assert sugerir_tipo("Sacola plástica") == "embalagem"
    assert sugerir_tipo("Farinha de trigo") == "ingrediente"


def test_sugerir_match_vincula_ingrediente_existente():
    refs = [
        IngredienteRef(id="a1", nome="Açúcar Cristal", unidade="kg", tipo="ingrediente"),
        IngredienteRef(id="b2", nome="Farinha de Trigo", unidade="kg", tipo="ingrediente"),
    ]
    sugestao = sugerir_match("ACUCAR CRISTAL UNIAO 1KG", "kg", refs)
    assert sugestao.ingrediente_id == "a1"
    assert sugestao.nome_match == "Açúcar Cristal"
    assert sugestao.score >= LIMIAR_MATCH
    # Quando há match, herda unidade/tipo do ingrediente existente.
    assert sugestao.unidade_sugerida == "kg"
    assert sugestao.tipo_sugerido == "ingrediente"


def test_sugerir_match_item_novo_sem_correspondente():
    refs = [
        IngredienteRef(id="a1", nome="Açúcar Cristal", unidade="kg", tipo="ingrediente"),
    ]
    sugestao = sugerir_match("Sacola Plástica Reforçada", "un", refs)
    assert sugestao.ingrediente_id is None
    assert sugestao.nome_match is None
    # Categoriza e normaliza a unidade para facilitar o cadastro.
    assert sugestao.tipo_sugerido == "embalagem"
    assert sugestao.unidade_sugerida == "un"


def test_sugerir_match_lista_vazia_nao_quebra():
    sugestao = sugerir_match("Qualquer coisa", "kg", [])
    assert sugestao.ingrediente_id is None
    assert sugestao.score == 0.0
