"""Máquina de estados da Ordem de Produção.

Transições possíveis:
    planejada    → em_producao | cancelada
    em_producao  → finalizada | cancelada
    finalizada   → (terminal)
    cancelada    → (terminal)

Efeitos colaterais (ver service.py):
    → em_producao : reserva ingredientes (quantidade_reservada += necessário)
    → finalizada  : debita ingredientes, entrada no estoque PA (qtd_produzida)
    → cancelada (de em_producao) : estorna reserva de ingredientes
"""

from __future__ import annotations

STATUS_PLANEJADA = "planejada"
STATUS_EM_PRODUCAO = "em_producao"
STATUS_FINALIZADA = "finalizada"
STATUS_CANCELADA = "cancelada"

STATUS_VALIDOS: frozenset[str] = frozenset(
    {STATUS_PLANEJADA, STATUS_EM_PRODUCAO, STATUS_FINALIZADA, STATUS_CANCELADA}
)

# Status nos quais a edição dos dados da OP (receita, qtd_planejada, data) é permitida.
STATUS_EDITAVEIS: frozenset[str] = frozenset({STATUS_PLANEJADA})

# Status nos quais a OP pode ser deletada (soft delete).
STATUS_DELETAVEIS: frozenset[str] = frozenset({STATUS_PLANEJADA, STATUS_CANCELADA})

_TRANSICOES: dict[str, frozenset[str]] = {
    STATUS_PLANEJADA: frozenset({STATUS_EM_PRODUCAO, STATUS_CANCELADA}),
    STATUS_EM_PRODUCAO: frozenset({STATUS_FINALIZADA, STATUS_CANCELADA}),
    STATUS_FINALIZADA: frozenset(),
    STATUS_CANCELADA: frozenset(),
}


def proximas_transicoes(status: str) -> frozenset[str]:
    return _TRANSICOES.get(status, frozenset())


def pode_transicionar(de: str, para: str) -> bool:
    return para in proximas_transicoes(de)
