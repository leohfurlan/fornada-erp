"""Operational projection from one PostgreSQL statement snapshot; no cost engine."""

import hashlib
import json
import unicodedata
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import joinedload

from domain.number_format import quantity_br
from infrastructure.database.models import Ingrediente, Receita, ReceitaIngrediente


def normalized(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c)
    )


def fingerprint(data):
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def positive_quantity(value: object) -> None:
    """Reject invalid quantities even when nested content is rendered as text."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Quantidade inválida") from None
    if not number.is_finite() or number <= 0:
        raise ValueError("Quantidade inválida")


async def search(db, tenant_id, query, offset, limit):
    rows = (
        await db.execute(
            select(Receita.id, Receita.nome).where(
                Receita.tenant_id == tenant_id, Receita.deleted_at.is_(None)
            )
        )
    ).all()
    term = normalized(query)
    matches = sorted(
        ((rid, name) for rid, name in rows if term in normalized(name)),
        key=lambda item: (normalized(item[1]), str(item[0])),
    )
    page = matches[offset : offset + limit]
    return {
        "items": [{"recipe_id": str(rid), "name": name} for rid, name in page],
        "next_offset": offset + limit if offset + limit < len(matches) else None,
    }


async def snapshot(db, tenant_id, recipe_id, *, include_steps: bool = False):
    # joinedload emits one SELECT: ingredients, steps and every component share
    # the same statement snapshot even under the default READ COMMITTED level.
    materials_query = (
        select(func.jsonb_object_agg(cast(Ingrediente.id, String), Ingrediente.nome))
        .where(Ingrediente.tenant_id == tenant_id, Ingrediente.deleted_at.is_(None))
        .scalar_subquery()
    )
    rows = (
        (
            await db.execute(
                select(Receita, materials_query.label("materials"))
                .where(Receita.tenant_id == tenant_id, Receita.deleted_at.is_(None))
                .options(
                    joinedload(Receita.ingredientes).joinedload(ReceitaIngrediente.ingrediente),
                    joinedload(Receita.etapas),
                )
                .execution_options(populate_existing=True)
            )
        )
        .unique(lambda result: result[0].id)
        .all()
    )
    catalog = {row.id: row for row, _ in rows}
    materials = (rows[0][1] or {}) if rows else {}
    if recipe_id not in catalog:
        return None
    root = catalog[recipe_id]
    warnings, sections = [], []

    def section(title, value):
        if value:
            sections.append({"title": title, "text": value})

    def ingredients(row):
        result = []
        for item in sorted(row.ingredientes, key=lambda item: str(item.id)):
            if item.deleted_at:
                continue
            material = item.ingrediente
            if not material or material.tenant_id != tenant_id or material.deleted_at:
                warnings.append(f"{row.nome}: ingrediente vinculado indisponível")
                continue
            positive_quantity(item.quantidade)
            result.append(
                {
                    "name": material.nome,
                    "quantity": format(item.quantidade, "f"),
                    "unit": item.unidade,
                }
            )
        if not result:
            warnings.append(f"{row.nome}: ingredientes não cadastrados")
        return result

    root_ingredients = ingredients(root)
    visited = set()

    def visit(row, path, depth=0):
        if row.id in path:
            warnings.append(f"{row.nome}: composição cíclica")
            return
        if row.id in visited:
            return
        if depth > 50:
            warnings.append(f"{row.nome}: composição excede profundidade de consulta")
            return
        visited.add(row.id)
        positive_quantity(row.rendimento)
        prefix = "" if row.id == root.id else f"Sub-receita · {row.nome} · "
        if row.id != root.id:
            items = ingredients(row)
            body = f"Rendimento: {quantity_br(row.rendimento)} {row.rendimento_unidade}\n"
            body += "\n".join(
                f"- {i['name']}: {quantity_br(i['quantity'])} {i['unit']}" for i in items
            )
            section(prefix + "Ingredientes", body)
        section(prefix + "Categoria", row.categoria)
        section(prefix + "Foto de referência", row.foto_url)
        section(prefix + "Modo de preparo", row.modo_preparo)
        if not row.modo_preparo:
            warnings.append(f"{row.nome}: modo de preparo não cadastrado")
        for index, step in enumerate(
            sorted(
                (step for step in row.etapas if not step.deleted_at),
                key=lambda step: (step.ordem, str(step.id)),
            ),
            1,
        ):
            section(
                prefix + f"Etapa {index}",
                f"{step.nome}\nDuração: {step.duracao_minutos} min\nTipo: {step.tipo_mao_obra}",
            )
        sheet = row.ficha_tecnica or {}
        section(prefix + "Descrição do produto", sheet.get("descricao_produto"))
        section(prefix + "Apresentação final", sheet.get("especificacao_final"))
        for index, step in enumerate(sheet.get("passos", []), 1):
            positive_quantity(step["quantidade"])
            for bound in ("quantidade_minima", "quantidade_maxima"):
                if step.get(bound) is not None:
                    positive_quantity(step[bound])
            body = f"{step['descricao']}\nTipo: {step['tipo']}\n"
            body += f"Quantidade: {quantity_br(step['quantidade'])} {step['unidade']}"
            if step.get("quantidade_minima") is not None:
                body += (
                    f"\nFaixa: {quantity_br(step['quantidade_minima'])}–"
                    f"{quantity_br(step['quantidade_maxima'])} {step['unidade']}"
                )
            if step.get("especificacao"):
                body += "\nEspecificação:\n" + step["especificacao"]
            if step.get("instrucao"):
                body += "\nInstrução:\n" + step["instrucao"]
            if step.get("ingrediente_id"):
                try:
                    material_name = materials.get(str(UUID(step["ingrediente_id"])))
                except (ValueError, TypeError, AttributeError):
                    material_name = None
                if material_name is None:
                    warnings.append(f"{row.nome}: material vinculado indisponível")
                else:
                    body += "\nMaterial: " + material_name
            section(prefix + f"Montagem {index}", body)
            if step.get("receita_base_id"):
                try:
                    component = catalog.get(UUID(step["receita_base_id"]))
                except (ValueError, TypeError, AttributeError):
                    component = None
                if not component:
                    warnings.append(f"{row.nome}: sub-receita vinculada indisponível")
                else:
                    visit(component, path | {row.id}, depth + 1)

    visit(root, set())
    data = {
        "recipe_id": str(root.id),
        "name": root.nome,
        "yield_quantity": format(root.rendimento, "f"),
        "yield_unit": root.rendimento_unidade,
        "ingredients": root_ingredients,
        "sections": sections,
        "warnings": warnings,
    }
    if include_steps:
        # Kitchen-only structured data, from the same tenant-scoped SELECT.
        # Keep the Central's existing response and version contract unchanged.
        data["steps"] = [
            {
                "id": str(step.id),
                "name": step.nome,
                "duration_minutes": step.duracao_minutos,
                "work_type": step.tipo_mao_obra,
                "order": step.ordem,
            }
            for step in sorted(root.etapas, key=lambda step: (step.ordem, str(step.id)))
            if not step.deleted_at
        ]
    data["version"] = fingerprint(data)
    return data
