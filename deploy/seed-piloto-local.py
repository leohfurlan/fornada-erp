"""Dados demonstrativos apenas na API local de QA (nunca chama a VPS)."""
import json
from pathlib import Path
from uuid import uuid4

import httpx

base = "http://127.0.0.1:8012/api/v1"
with httpx.Client(timeout=20) as client:
    email = f"qa-{uuid4().hex}@example.com"
    login = client.post(f"{base}/auth/register", json={"email": email, "senha": "FornadaTeste2026!", "nome": "Confeiteira QA", "nome_negocio": "Loja QA"})
    login.raise_for_status()
    tokens = login.json()
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    ids = {}
    for nome, tipo, unidade, custo, estoque in [("Leite condensado", "ingrediente", "kg", "12", "10"), ("Copo 300 ml", "embalagem", "un", "0.80", "100"), ("Morango", "ingrediente", "kg", "20", "10")]:
        resposta = client.post(f"{base}/estoque/ingredientes", json={"nome": nome, "tipo": tipo, "unidade": unidade, "custo_inicial": custo, "estoque_inicial": estoque})
        resposta.raise_for_status()
        ids[nome] = resposta.json()["id"]
    receitas = {}
    for nome, rendimento, unidade in [("Brigadeiro", "1000", "g"), ("Copo Sedução QA", "1", "un")]:
        resposta = client.post(f"{base}/receitas", json={"nome": nome, "categoria": "Piloto", "rendimento": rendimento, "rendimento_unidade": unidade, "ingredientes": [{"ingrediente_id": ids["Leite condensado"], "quantidade": "1", "unidade": "kg"}] if nome == "Brigadeiro" else [], "etapas": []})
        resposta.raise_for_status()
        receitas[nome] = resposta.json()["id"]
    ficha = {"descricao_produto": "Copo Sedução — demonstração de montagem", "especificacao_final": "Copo de 300 ml com tampa e adesivo", "revisao": 0, "composicao_ativa": True, "passos": [
        {"descricao": "Copo", "tipo": "embalagem", "quantidade": "1", "unidade": "un", "ingrediente_id": ids["Copo 300 ml"], "especificacao": "300 ml"},
        {"descricao": "Brigadeiro", "tipo": "componente", "quantidade": "30", "unidade": "g", "receita_base_id": receitas["Brigadeiro"], "instrucao": "Distribuir uma camada uniforme."},
        {"descricao": "Morango picado", "tipo": "ingrediente", "quantidade": "25", "unidade": "g", "ingrediente_id": ids["Morango"]},
        {"descricao": "Brigadeiro", "tipo": "componente", "quantidade": "30", "unidade": "g", "receita_base_id": receitas["Brigadeiro"]},
    ]}
    resposta = client.put(f"{base}/receitas/{receitas['Copo Sedução QA']}/ficha-tecnica", json=ficha)
    resposta.raise_for_status()
    dest = Path(__file__).resolve().parents[1] / "dist" / "qa-local.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps({"email": email, "tokens": tokens, "receitas": receitas}), encoding="utf-8")
    print("Dados de QA criados no banco local isolado.")
