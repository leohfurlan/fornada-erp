"""
Matching de itens de cupom fiscal contra ingredientes cadastrados.

Funções puras (sem I/O) para garantir testabilidade. Usa apenas a stdlib
(`difflib`) — não adiciona dependência de fuzzy matching ao projeto.

Estratégia:
1. Normaliza descrições (minúsculas, sem acento, sem ruído de marca/embalagem).
2. Compara por similaridade de sequência + sobreposição de tokens.
3. Sugere o melhor ingrediente acima de um limiar de confiança.
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

# Limiar mínimo de similaridade para considerar um match automático.
# Abaixo disso o item é tratado como "novo" (sem ingrediente correspondente).
LIMIAR_MATCH = 0.62

# Mapeia variações de unidade lidas no cupom para a forma canônica do Fornada.
_UNIDADES_CANONICAS = {
    "kg": "kg",
    "kgs": "kg",
    "quilo": "kg",
    "quilos": "kg",
    "g": "g",
    "gr": "g",
    "grama": "g",
    "gramas": "g",
    "mg": "mg",
    "l": "l",
    "lt": "l",
    "lts": "l",
    "litro": "l",
    "litros": "l",
    "ml": "ml",
    "un": "un",
    "und": "un",
    "unid": "un",
    "unidade": "un",
    "unidades": "un",
    "pc": "un",
    "pç": "un",
    "cx": "cx",
    "caixa": "cx",
    "pct": "pct",
    "pacote": "pct",
    "pacotes": "pct",
    "dz": "dz",
    "duzia": "dz",
    "fardo": "fardo",
}

# Palavras que não ajudam a identificar o ingrediente (ruído de cupom).
_RUIDO = {
    "kg",
    "g",
    "ml",
    "l",
    "un",
    "und",
    "pct",
    "cx",
    "pc",
    "tipo",
    "especial",
    "premium",
    "tradicional",
    "pacote",
    "unidade",
    "marca",
    "ref",
}

# Palavras-chave → tipo sugerido para itens novos (categorização PRD §3.6).
_PALAVRAS_EMBALAGEM = {
    "caixa",
    "caixinha",
    "sacola",
    "saco",
    "embalagem",
    "lacre",
    "fita",
    "papel",
    "forma",
    "forminha",
    "tampa",
    "pote",
    "colher",
    "garfo",
    "guardanapo",
}


@dataclass(frozen=True)
class IngredienteRef:
    """Visão mínima de um ingrediente cadastrado para fins de matching."""

    id: str
    nome: str
    unidade: str
    tipo: str


@dataclass(frozen=True)
class Sugestao:
    """Resultado do matching de um item do cupom."""

    ingrediente_id: str | None
    nome_match: str | None
    score: float  # 0.0 a 1.0
    tipo_sugerido: str
    unidade_sugerida: str


def remover_acentos(texto: str) -> str:
    """Remove acentuação preservando as letras base."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sem acento, apenas letras/dígitos/espaço, espaços colapsados."""
    sem_acento = remover_acentos(texto).lower()
    so_alfanum = re.sub(r"[^a-z0-9\s]", " ", sem_acento)
    return re.sub(r"\s+", " ", so_alfanum).strip()


def _tokens_significativos(texto_normalizado: str) -> set[str]:
    """Tokens com mais de 2 caracteres que não são ruído nem puramente numéricos."""
    return {
        tok
        for tok in texto_normalizado.split()
        if len(tok) > 2 and tok not in _RUIDO and not tok.isdigit()
    }


def normalizar_unidade(unidade: str) -> str:
    """Converte a unidade lida no cupom para a forma canônica conhecida."""
    chave = normalizar_texto(unidade)
    return _UNIDADES_CANONICAS.get(chave, chave or "un")


def sugerir_tipo(descricao: str) -> str:
    """Sugere o tipo (ingrediente | embalagem) a partir da descrição."""
    tokens = set(normalizar_texto(descricao).split())
    if tokens & _PALAVRAS_EMBALAGEM:
        return "embalagem"
    return "ingrediente"


def score_similaridade(descricao: str, nome_ingrediente: str) -> float:
    """
    Similaridade de 0 a 1 entre a descrição do cupom e o nome do ingrediente.

    Combina similaridade de sequência (difflib) com sobreposição de tokens
    significativos — a sobreposição evita que "Açúcar Cristal" e "Açúcar
    Refinado" sejam tratados como totalmente distintos, e o sequence matcher
    captura abreviações/typos do cupom.
    """
    a = normalizar_texto(descricao)
    b = normalizar_texto(nome_ingrediente)
    if not a or not b:
        return 0.0

    seq = SequenceMatcher(None, a, b).ratio()

    tokens_a = _tokens_significativos(a)
    tokens_b = _tokens_significativos(b)
    if tokens_a and tokens_b:
        intersecao = tokens_a & tokens_b
        jaccard = len(intersecao) / len(tokens_a | tokens_b)
        # Bônus forte quando todos os tokens do ingrediente aparecem na descrição
        # do cupom (ex.: cupom "ACUCAR CRISTAL UNIAO 1KG" × ingrediente "Açúcar Cristal").
        cobertura_b = len(tokens_a & tokens_b) / len(tokens_b)
    else:
        jaccard = 0.0
        cobertura_b = 0.0

    return round(max(seq, 0.5 * seq + 0.3 * jaccard + 0.2 * cobertura_b), 4)


def sugerir_match(
    descricao: str,
    unidade_cupom: str,
    ingredientes: list[IngredienteRef],
) -> Sugestao:
    """
    Encontra o melhor ingrediente para um item do cupom.

    Retorna uma sugestão com `ingrediente_id` preenchido quando o melhor score
    atinge o limiar; caso contrário, sugere criar um item novo (categorizado).
    """
    melhor: IngredienteRef | None = None
    melhor_score = 0.0
    for ing in ingredientes:
        s = score_similaridade(descricao, ing.nome)
        if s > melhor_score:
            melhor_score = s
            melhor = ing

    unidade_canonica = normalizar_unidade(unidade_cupom)

    if melhor is not None and melhor_score >= LIMIAR_MATCH:
        return Sugestao(
            ingrediente_id=melhor.id,
            nome_match=melhor.nome,
            score=melhor_score,
            tipo_sugerido=melhor.tipo,
            unidade_sugerida=melhor.unidade,
        )

    return Sugestao(
        ingrediente_id=None,
        nome_match=None,
        score=melhor_score,
        tipo_sugerido=sugerir_tipo(descricao),
        unidade_sugerida=unidade_canonica,
    )
