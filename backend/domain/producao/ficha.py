"""Snapshot de montagem e consumo por execução da receita."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from domain.exceptions import ValidationError
from domain.receitas.composicao import converter_quantidade
from domain.estoque.unidades import converter_para_principal
from domain.receitas.repository import ReceitaRepository
from infrastructure.database.models import Receita


async def montar_snapshot(receita: Receita, repo: ReceitaRepository, tenant_id: UUID) -> dict:
    """Congela instruções, rendimento, unidades e consumo para produção futura."""
    ficha = deepcopy(receita.ficha_tecnica or {})
    materiais: dict[str, Decimal] = {}
    bases: dict[str, Decimal] = {}
    detalhes: dict[str, dict] = {}
    if ficha.get("composicao_ativa"):
        for passo in ficha["passos"]:
            quantidade = Decimal(passo["quantidade"]) * receita.rendimento
            if passo.get("receita_base_id"):
                alvo = passo["receita_base_id"]
                base = await repo.buscar_por_id(UUID(alvo), tenant_id)
                if not base:
                    raise ValidationError("Receita-base removida; revise a ficha técnica")
                convertido = converter_quantidade(quantidade, passo["unidade"], base.rendimento_unidade)
                bases[alvo] = bases.get(alvo, Decimal("0")) + convertido
                detalhes[alvo] = {"tipo": "receita_base", "id": alvo, "nome": base.nome, "unidade": base.rendimento_unidade}
            else:
                alvo = passo["ingrediente_id"]
                material = await repo.buscar_ingrediente(UUID(alvo), tenant_id)
                if not material:
                    raise ValidationError("Material removido; revise a ficha técnica")
                convertido = converter_para_principal(quantidade, passo["unidade"], material.unidade, material.unidades_alternativas)
                materiais[alvo] = materiais.get(alvo, Decimal("0")) + convertido
                detalhes[alvo] = {"tipo": "material", "id": alvo, "nome": material.nome, "unidade": material.unidade}
    else:
        for item in receita.ingredientes:
            alvo = str(item.ingrediente_id)
            materiais[alvo] = materiais.get(alvo, Decimal("0")) + converter_para_principal(item.quantidade, item.unidade, item.ingrediente.unidade, item.ingrediente.unidades_alternativas)
            detalhes[alvo] = {"tipo": "material", "id": alvo, "nome": item.ingrediente.nome, "unidade": item.ingrediente.unidade}
    return {"ficha": ficha, "revisao": receita.ficha_revisao,
            "nome": receita.nome, "rendimento": str(receita.rendimento),
            "unidade": receita.rendimento_unidade,
            "materiais": {k: str(v) for k, v in materiais.items()},
            "bases": {k: str(v) for k, v in bases.items()},
            "consumo": [{**detalhes[k], "quantidade_por_fornada": str(v)} for k, v in (materiais | bases).items()]}


def necessidade(snapshot: dict, campo: str, execucoes: Decimal) -> dict[UUID, Decimal]:
    """Agrega consumo congelado e aplica precisão do estoque (três casas)."""
    valores = {UUID(k): (Decimal(v) * execucoes).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
               for k, v in snapshot[campo].items()}
    if any(v <= 0 for v in valores.values()):
        raise ValidationError("Uma quantidade de consumo ficou abaixo da precisão do estoque. Aumente a quantidade planejada.")
    return valores
