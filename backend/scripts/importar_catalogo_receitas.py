"""Importa ingredientes e etapas; não cria receitas nem inventa rendimentos."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import select
from domain.estoque.schemas import CriarIngredienteRequest
from domain.configuracoes.schemas import CriarEtapaPadraoRequest

logger = structlog.get_logger(__name__)
NESTLE = "https://www.receitasnestle.com.br/artigos/medidas-para-os-ingredientes-na-cozinha"
KING_ARTHUR = "https://www.kingarthurbaking.com/learn/ingredient-weight-chart"
ALIASES = {
    "ovos": "Ovos", "ovo": "Ovos", "ovos grandes": "Ovos grandes",
    "açúcar": "Açúcar", "farinha de trigo": "Farinha de trigo", "farinha de trigo peneirada": "Farinha de trigo",
    "farinha de trigo sem fermento": "Farinha de trigo sem fermento",
    "leite morno": "Leite", "leite": "Leite", "água morna": "Água",
    "chocolate em pó": "Chocolate em pó (teor não informado)",
    "fermento": "Fermento (tipo não informado)", "fermento biológico": "Fermento biológico (tipo não informado)",
    "margarina derretida": "Margarina 80% lipídios", "gema para pincelar": "Gema de ovo",
    "mortadela fatiada ou picada": "Mortadela",
}


def alternativas(nome: str) -> list[dict]:
    """Fatores explícitos do JSON ou referências identificadas, não densidades globais."""
    fator: dict[str, str] = {}
    fonte = NESTLE
    if nome in {"Leite", "Leite integral", "Óleo", "Água", "Essência de baunilha"}:
        fator = {"xícara": "240", "colher de sopa": "15", "colher de chá": "5"}
    elif nome in {"Farinha de trigo", "Farinha de trigo sem fermento"}:
        fator = {"xícara": "120", "colher de sopa": "7.5", "colher de chá": "2.5"}
    elif nome == "Açúcar":
        fator = {"xícara": "160", "colher de sopa": "10", "colher de chá": "3.5"}
    elif nome in {"Chocolate em pó 50%", "Chocolate em pó (teor não informado)"}:
        fator = {"xícara": "90", "colher de sopa": "6", "colher de chá": "2"}
    elif nome in {"Fermento químico", "Fermento em pó"}:
        fator = {"colher de sopa": "14", "colher de chá": "5"}
    elif nome == "Sal":
        fator = {"colher de sopa": "20", "colher de chá": "5"}
    elif nome == "Manteiga":
        fator = {"xícara": "200", "colher de sopa": "14", "colher de chá": "4"}
    elif nome == "Bicarbonato de sódio":
        fator = {"colher de chá": "6"}
        fonte = KING_ARTHUR
    resultado = [{"unidade": u, "fator": v, "observacao": f"Referência culinária aproximada; validar seu medidor. Fonte: {fonte}"} for u, v in fator.items()]
    extras = {
        "Açúcar": [("xícara (massa chocolate média)", "180", "JSON: 360 g = 2 xícaras"), ("colher de sopa rasa", "10", "JSON: 30 g = 3 colheres rasas")],
        "Sal": [("colher de sopa rasa", "10", "JSON: 20 g = 2 colheres rasas")],
        "Fermento químico": [("colher de sopa bem cheia", "15", "JSON: 15 g = 1 colher bem cheia")],
        "Fermento biológico seco": [("envelope", "10", "JSON: 10 g = 1 envelope")],
        "Fermento biológico (tipo não informado)": [("pacote", "10", "JSON: meio pacote = 5 g")],
        "Farinha de trigo": [("copo americano (esponja pão caseiro)", "120", "JSON: 1 copo = 120 g; não aplicar à massa do mesmo pão")],
    }
    resultado.extend({"unidade": u, "fator": v, "observacao": f} for u, v, f in extras.get(nome, []))
    return resultado


def montar_plano(data: dict) -> dict:
    """Extrai materiais e instruções, com tempos somente onde explicitados."""
    materiais: dict[str, dict] = {}
    etapas: list[dict] = []
    pendencias = ["Pitada: medir por ingrediente; não há fator universal.", "Farinha no pão caseiro: 1 copo = 120 g na esponja, mas 3 copos = 260 g na massa. Preservados sem conversão universal.", "Colher sem tipo e colher rasa de sobremesa: medida ainda não confirmada.", "Tempos não informados permanecem pendentes; não são estimados."]
    # Índices do arquivo transcrito: apenas tempos expressamente informados.
    tempos = {(3, 4): (55, "indireta"), (4, 0): (8, "direta"), (4, 4): (40, "indireta"), (5, 4): (45, "indireta"), (6, 0): (7, "direta"), (8, 1): (10, "direta"), (8, 2): (60, "indireta"), (8, 4): (40, "indireta")}
    fontes = {"image(10).png": 3, "image(20261006-165838).png": 4, "image(20261006-165859).png": 5, "image(20261006-165913).png": 6, "image(20261006-170007).png": 8, "image(20261006-170031).png": 9}
    for receita in data["receitas"]:
        rindex = fontes.get(receita.get("fonte"), -1)
        contextos = [(None, receita)] + [(c["nome"], c) for c in receita.get("componentes", [])]
        for componente, contexto in contextos:
            origem = receita["titulo"] + (f" / {componente}" if componente else "")
            for item in contexto.get("ingredientes", []):
                raw = item["ingrediente"].lower()
                nomes = {"manteiga ou margarina": ["Manteiga", "Margarina"], "tomate em rodelas finas ou requeijão": ["Tomate", "Requeijão"], "chocolate em pó 50% ou essência de baunilha": ["Chocolate em pó 50%", "Essência de baunilha"]}.get(raw, [ALIASES.get(raw, item["ingrediente"][:1].upper() + item["ingrediente"][1:])])
                if raw == "chocolate meio amargo" and item.get("observacao") == "fracionado":
                    nomes = ["Chocolate meio amargo fracionado"]
                for nome in nomes:
                    principal = "un" if nome in {"Ovos", "Ovos grandes", "Gema de ovo"} else "mL" if nome in {"Leite", "Leite integral", "Óleo", "Água", "Essência de baunilha"} else "g"
                    materiais.setdefault(nome, {"nome": nome, "tipo": "ingrediente", "unidade": principal, "estoque_minimo": "1", "estoque_inicial": "0", "custo_inicial": "0", "unidades_alternativas": alternativas(nome)})
            for index, texto in enumerate(contexto.get("modo_preparo", [])):
                duracao, tipo = tempos.get((rindex, index), (None, "direta")) if not componente else (None, "direta")
                if texto.startswith(("Descanso:", "Asse ", "Leve ao forno", "Depois deixe esfriar")) or texto.startswith("Em seguida acrescente o fermento e leve"):
                    tipo = "indireta"
                resumo = texto.split(":", 1)[0] if ":" in texto else texto.split(".", 1)[0][:65]
                etapas.append({"nome": f"{index + 1:02d}. {resumo} — {origem}"[:200], "tipo_mao_obra": tipo, "duracao_minutos_default": duracao, "instrucao": texto, "receita_origem": origem})
            # Formatos alternativos de forno permanecem etapas distintas.
            for texto in contexto.get("tempo_de_forno", []):
                import re
                match = re.search(r"(\d+)\s*(?:a|–|-)\s*(\d+)\s*(?:minutos|min)", texto)
                if match:
                    etapas.append({"nome": f"Assar — {texto} — {origem}"[:200], "tipo_mao_obra": "indireta", "duracao_minutos_default": int(match[2]), "instrucao": texto, "receita_origem": origem})
            if contexto.get("segredo"):
                etapas.append({"nome": f"Após assar — {origem}"[:200], "tipo_mao_obra": "direta", "duracao_minutos_default": None, "instrucao": "\n".join(contexto["segredo"]), "receita_origem": origem})
            if contexto.get("dica"):
                etapas.append({"nome": f"Finalização opcional — {origem}"[:200], "tipo_mao_obra": "direta", "duracao_minutos_default": None, "instrucao": contexto["dica"], "receita_origem": origem})
        # Tempos em instruções compostas: cada espera/temperatura separada do trabalho ativo.
        extras: list[tuple[str, int, str, str]] = []
        if rindex == 8:
            extras = [("Descansar fermento", 5, "indireta", receita["modo_preparo"][0])]
        if rindex == 9:
            c = receita["componentes"]
            extras = [("Descansar esponja", 20, "indireta", c[0]["modo_preparo"][0]), ("Descansar massa", 30, "indireta", c[1]["modo_preparo"][1]), ("Descansar após dividir", 10, "indireta", c[1]["modo_preparo"][2]), ("Descansar na assadeira", 40, "indireta", c[1]["modo_preparo"][3]), ("Assar a 160°C", 20, "indireta", c[1]["modo_preparo"][3]), ("Assar a 180°C", 25, "indireta", c[1]["modo_preparo"][3])]
        for nome, minutos, tipo, texto in extras:
            etapas.append({"nome": f"{nome} — {receita['titulo']}"[:200], "tipo_mao_obra": tipo, "duracao_minutos_default": minutos, "instrucao": texto, "receita_origem": receita["titulo"]})
    materiais["Alho"] = {"nome": "Alho", "tipo": "ingrediente", "unidade": "g", "estoque_minimo": "1", "estoque_inicial": "0", "custo_inicial": "0", "unidades_alternativas": []}
    materiais["Desmoldante"] = {"nome": "Desmoldante", "tipo": "insumo", "unidade": "g", "estoque_minimo": "1", "estoque_inicial": "0", "custo_inicial": "0", "unidades_alternativas": [{"unidade": "lata", "fator": "120", "observacao": "Embalagem de 120 g informada pelo usuário."}]}
    materiais["Plástico filme"] = {"nome": "Plástico filme", "tipo": "descartavel", "unidade": "un", "estoque_minimo": "1", "estoque_inicial": "0", "custo_inicial": "0", "unidades_alternativas": []}
    return {"ingredientes": list(materiais.values()), "etapas": etapas, "pendencias": pendencias}


async def importar(plano: dict, email: str, tenant_id: UUID, aplicar: bool) -> dict:
    """Aplica por services/repositories em uma transação e somente no tenant confirmado."""
    from domain.estoque.repository import EstoqueRepository
    from domain.estoque.service import EstoqueService
    from domain.configuracoes.repository import ConfiguracoesRepository
    from infrastructure.database.session import AsyncSessionLocal
    from infrastructure.database.models import Usuario, Tenant
    async with AsyncSessionLocal() as db:
        usuario = (await db.execute(select(Usuario).join(Tenant).where(Usuario.email == email, Usuario.tenant_id == tenant_id, Usuario.ativo.is_(True), Usuario.deleted_at.is_(None), Tenant.ativo.is_(True)))).scalar_one()
        user_id = str(usuario.id)
        estoque = EstoqueService(EstoqueRepository(db))
        configuracoes = ConfiguracoesRepository(db)
        existentes = {i.nome.casefold(): i for i in await EstoqueRepository(db).listar(tenant_id)}
        cadastradas = {(e.nome, e.receita_origem) for e in await configuracoes.listar_etapas(tenant_id)}
        novos_ingredientes = novos_etapas = 0
        for item in plano["ingredientes"]:
            request = CriarIngredienteRequest(**item)
            atual = existentes.get(request.nome.casefold())
            if atual is not None:
                if atual.unidade.lower() != request.unidade.lower():
                    raise ValueError(f"Unidade existente incompatível em {atual.nome}; dados preservados.")
                # Não zerar inventário nem substituir conversões já cadastradas.
                continue
            await estoque.criar_ingrediente(tenant_id, request)
            novos_ingredientes += 1
        for item in plano["etapas"]:
            if (item["nome"], item["receita_origem"]) not in cadastradas:
                await configuracoes.criar_etapa(tenant_id, CriarEtapaPadraoRequest(**item))
                novos_etapas += 1
        if aplicar:
            await db.commit()
        else:
            await db.rollback()
        resultado = {"aplicado": aplicar, "tenant_id": str(tenant_id), "ingredientes_novos": novos_ingredientes, "etapas_novas": novos_etapas, "tempos_pendentes": sum(e["duracao_minutos_default"] is None for e in plano["etapas"]), "pendencias": plano["pendencias"]}
        logger.info("catalogo_receitas_importado" if aplicar else "catalogo_receitas_simulado", tenant_id=str(tenant_id), user_id=user_id, action="import", entity="catalogo_receitas", entity_id=str(tenant_id), **{k: v for k, v in resultado.items() if k not in {"tenant_id", "pendencias"}})
        return resultado


def main() -> None:
    """CLI: planejamento puro ou importação explícita com identidade confirmada."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--arquivo", required=True, type=Path)
    parser.add_argument("--email")
    parser.add_argument("--tenant-id", type=UUID)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--plano", action="store_true")
    args = parser.parse_args()
    conteudo = args.arquivo.read_bytes()
    plano = montar_plano(json.loads(conteudo.decode("utf-8-sig")))
    plano["sha256_fonte"] = hashlib.sha256(conteudo).hexdigest()
    if args.plano:
        print(json.dumps(plano, ensure_ascii=False, indent=2))
    else:
        if not args.email or not args.tenant_id:
            parser.error("Informe --email e --tenant-id para consultar/aplicar na conta.")
        print(json.dumps(asyncio.run(importar(plano, args.email, args.tenant_id, args.aplicar)), ensure_ascii=False))


if __name__ == "__main__":
    main()
