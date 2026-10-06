from scripts.importar_catalogo_receitas import montar_plano


def test_tempo_identificado_por_fonte_preserva_original_e_nao_estima():
    texto = "Asse por 45 a 55 minutos."
    receita = {"fonte": "image(10).png", "titulo": "Chocolate", "modo_preparo": ["Bata", "Misture", "Misture", "Incorpore", texto]}
    outra = {"fonte": "outra", "titulo": "Outra", "modo_preparo": ["Misture"]}
    plano = montar_plano({"receitas": [outra, receita]})
    assar = next(e for e in plano["etapas"] if e["instrucao"] == texto)
    assert assar["duracao_minutos_default"] == 55
    assert assar["tipo_mao_obra"] == "indireta"
    assert plano["etapas"][0]["duracao_minutos_default"] is None


def test_materiais_confirmados_e_alternativas_separadas():
    plano = montar_plano({"receitas": [{"titulo": "Brownie", "ingredientes": [{"ingrediente": "manteiga ou margarina"}]}]})
    itens = {i["nome"]: i for i in plano["ingredientes"]}
    assert "Manteiga" in itens and "Margarina" in itens
    assert itens["Desmoldante"]["unidades_alternativas"][0]["fator"] == "120"
    assert itens["Plástico filme"]["unidade"] == "un"
    assert all(i["estoque_inicial"] == "0" and i["custo_inicial"] == "0" and i["estoque_minimo"] == "1" for i in itens.values())
