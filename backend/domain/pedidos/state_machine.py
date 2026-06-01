"""
Máquina de estados de pedidos (encomendas).

Sprint 3 simplificou o fluxo: pedido não mexe mais em ingredientes. Quem
produz é a Ordem de Produção. O pedido só registra a encomenda e dispara
baixa do estoque de produto acabado na entrega.

Transições possíveis:
    orcamento → aprovado | cancelado
    aprovado  → entregue | cancelado
    entregue  → (terminal)
    cancelado → (terminal)

Efeitos colaterais (ver service.py):
    → entregue : debita estoque PA dos itens. Se faltar saldo, raise.

Status legados `em_producao` e `finalizado` continuam aceitos como string
no banco para registros pré-refator, mas são inalcançáveis pelo novo fluxo.
"""

from __future__ import annotations

STATUS_ORCAMENTO = "orcamento"
STATUS_APROVADO = "aprovado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"

# Status legados (Sprint 2) — mantidos no conjunto válido para não quebrar
# pedidos criados antes do refator. Não aparecem mais nas transições.
STATUS_EM_PRODUCAO = "em_producao"
STATUS_FINALIZADO = "finalizado"

STATUS_VALIDOS: frozenset[str] = frozenset(
    {
        STATUS_ORCAMENTO,
        STATUS_APROVADO,
        STATUS_ENTREGUE,
        STATUS_CANCELADO,
        STATUS_EM_PRODUCAO,  # legado
        STATUS_FINALIZADO,  # legado
    }
)

# Status nos quais a edição de itens/cliente/data ainda é permitida.
STATUS_EDITAVEIS: frozenset[str] = frozenset({STATUS_ORCAMENTO})

# Status nos quais o pedido pode ser deletado (soft delete).
STATUS_DELETAVEIS: frozenset[str] = frozenset({STATUS_ORCAMENTO, STATUS_CANCELADO})

_TRANSICOES: dict[str, frozenset[str]] = {
    STATUS_ORCAMENTO: frozenset({STATUS_APROVADO, STATUS_CANCELADO}),
    STATUS_APROVADO: frozenset({STATUS_ENTREGUE, STATUS_CANCELADO}),
    STATUS_ENTREGUE: frozenset(),
    STATUS_CANCELADO: frozenset(),
}


def proximas_transicoes(status: str) -> frozenset[str]:
    """Retorna o conjunto de status que `status` pode transicionar."""
    return _TRANSICOES.get(status, frozenset())


def pode_transicionar(de: str, para: str) -> bool:
    """True se a transição `de → para` é permitida."""
    return para in proximas_transicoes(de)
