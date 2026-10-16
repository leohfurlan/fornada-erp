"""Versioned partial purchase drafts; no catalog or stock effects."""

import copy
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal
from uuid import uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

ITEM_FIELDS = {
    "descricao_original",
    "quantidade",
    "unidade",
    "custo_unitario",
    "desconto_item",
    "preco_total",
    "nome",
    "tipo",
    "unidade_principal",
    "criar_novo",
    "ingrediente_id",
    "produto_id",
    "produto_revisao",
    "aprovar_produto",
    "aprovar_fornecedor",
    "aceitar_excecao",
    "produto_novo.nome",
    "produto_novo.marca",
    "produto_novo.variante",
    "produto_novo.conteudo_embalagem",
    "produto_novo.unidade_conteudo",
    "produto_novo.fator_para_principal",
    "produto_novo.fabricante",
}
PURCHASE_FIELDS = {"estabelecimento", "data_compra", "fornecedor_id", "fornecedor_novo.nome"}
BOOL_FIELDS = {"criar_novo", "aprovar_produto", "aprovar_fornecedor", "aceitar_excecao"}
NUMERIC_FIELDS = {
    "quantidade",
    "custo_unitario",
    "desconto_item",
    "preco_total",
    "produto_novo.conteudo_embalagem",
    "produto_novo.fator_para_principal",
}


class Edit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    op: Literal["set_item", "remove_item", "set_purchase"]
    item_ref: str | None = Field(default=None, min_length=1, max_length=36)
    field: str | None = Field(default=None, max_length=60)
    value: str | bool | int | None = None

    @model_validator(mode="after")
    def typed_operation(self):
        if self.op == "remove_item":
            if not self.item_ref or self.field is not None or self.value is not None:
                raise ValueError("Remoção inválida")
        else:
            allowed = ITEM_FIELDS if self.op == "set_item" else PURCHASE_FIELDS
            if self.field not in allowed or ((self.op == "set_item") != bool(self.item_ref)):
                raise ValueError("Operação ou campo inválido")
            if self.field in BOOL_FIELDS:
                if not isinstance(self.value, bool):
                    raise ValueError("Campo booleano inválido")
            elif self.field == "produto_revisao":
                if self.value is not None and (type(self.value) is not int or self.value < 1):
                    raise ValueError("Revisão inválida")
            elif self.value is not None and not isinstance(self.value, str):
                raise ValueError("Campo deve ser texto")
        return self


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def grouping_identity(item):
    """Normalize representation, never brand, packaging or measurement dimensions."""

    def normalized(key, value):
        if isinstance(value, dict):
            return {k: normalized(k, v) for k, v in value.items()}
        if isinstance(value, str):
            if key in {"custo_unitario", "conteudo_embalagem", "fator_para_principal"}:
                try:
                    return Decimal(value)
                except InvalidOperation:
                    return value
            return " ".join(value.split()).casefold()
        return value

    return {
        k: normalized(k, v)
        for k, v in item.items()
        if k not in {"quantidade", "preco_total", "desconto_item", "item_ref", "occurrences"}
    }


def seed(row):
    if row.dialogo:
        return copy.deepcopy(row.dialogo)
    if row.revisada:
        draft = copy.deepcopy(row.revisada)
    else:
        reading = row.leitura
        draft = {
            "estabelecimento": reading.get("estabelecimento"),
            "data_compra": reading.get("data_compra"),
            "itens": [],
        }
        for key in ("total_nota", "identidade_nota", "identidade_confirmada", "fornecedor_id"):
            if reading.get(key) is not None:
                draft[key] = reading[key]
        if reading.get("estabelecimento") and not reading.get("fornecedor_id"):
            draft["fornecedor_novo"] = {"nome": reading["estabelecimento"]}
        for observed in reading.get("itens", []):
            unit = observed.get("unidade")
            item = {
                "descricao_original": observed.get("descricao") or "",
                "nome": observed.get("descricao") or "",
                "tipo": observed.get("tipo_sugerido") or "ingrediente",
                "criar_novo": not bool(observed.get("ingrediente_id")),
                "ingrediente_id": observed.get("ingrediente_id"),
                "produto_id": observed.get("produto_id"),
                "produto_revisao": observed.get("produto_revisao"),
                "quantidade": observed.get("quantidade"),
                "unidade": unit,
                "custo_unitario": observed.get("preco_unitario"),
                "preco_total": observed.get("preco_total"),
                "desconto_item": observed.get("desconto_item") or "0",
                "unidade_principal": {"g": "kg", "ml": "l"}.get(unit, unit),
                "codigo_loja": observed.get("codigo_loja"),
                "aprovar_produto": True,
                "aprovar_fornecedor": True,
            }
            if not item["produto_id"]:
                item["produto_novo"] = {
                    "nome": observed.get("descricao") or "",
                    "marca": observed.get("marca_observada"),
                    "variante": observed.get("variante_observada"),
                    "conteudo_embalagem": observed.get("conteudo_observado"),
                    "unidade_conteudo": observed.get("unidade_conteudo_observada"),
                }
            draft["itens"].append(item)
    for index, item in enumerate(draft["itens"]):
        item["item_ref"] = str(uuid5(row.id, str(index)))
        item["occurrences"] = 1
    draft["itens"] = group_items(draft["itens"])
    return {"draft": draft, "applied": {}}


def group_items(items):
    grouped = []
    valid_refs = set()
    for item in items:
        identity = grouping_identity(item)
        match = next(
            (
                g
                for g in grouped
                if g["item_ref"] in valid_refs and grouping_identity(g) == identity
            ),
            None,
        )
        try:
            values = {
                k: Decimal(str(item[k])) for k in ("quantidade", "preco_total", "desconto_item")
            }
            if not all(v.is_finite() for v in values.values()):
                raise InvalidOperation()
            price = Decimal(str(item["custo_unitario"]))
            if (
                values["quantidade"] <= 0
                or values["preco_total"] <= 0
                or values["desconto_item"] < 0
                or price <= 0
                or not price.is_finite()
            ) or (values["quantidade"] * price - values["desconto_item"]).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ) != values["preco_total"]:
                raise InvalidOperation()
            if match:
                sums = {k: str(Decimal(str(match[k])) + v) for k, v in values.items()}
                match.update(sums)
                match["occurrences"] += item["occurrences"]
            else:
                grouped.append(item)
                valid_refs.add(item["item_ref"])
        except (InvalidOperation, KeyError, TypeError):
            grouped.append(item)
    return grouped


def reviewed(dialog):
    value = copy.deepcopy(dialog["draft"])
    for item in value["itens"]:
        item.pop("item_ref", None)
        item.pop("occurrences", None)
    return value


def patch(dialog, edits, catalog):
    value = copy.deepcopy(dialog)
    materials = {str(m["id"]): m for m in catalog["materials"]}
    products = {str(p["id"]): p for p in catalog["products"]}
    suppliers = {str(s["id"]): s for s in catalog["suppliers"]}
    for edit in edits:
        if edit.op == "set_purchase":
            if edit.item_ref is not None or edit.field not in PURCHASE_FIELDS:
                raise ValueError("Campo da compra inválido")
            target = value["draft"]
            if edit.field == "fornecedor_id":
                if edit.value is not None and edit.value not in suppliers:
                    raise ValueError("Loja fora do catálogo autorizado")
                target.pop("fornecedor_novo", None)
        else:
            target = next(
                (i for i in value["draft"]["itens"] if i["item_ref"] == edit.item_ref), None
            )
            if target is None:
                raise ValueError("Item não existe na revisão atual")
            if edit.op == "remove_item":
                if edit.field is not None or edit.value is not None:
                    raise ValueError("Remoção inválida")
                value.setdefault("removed", []).append(copy.deepcopy(target))
                value["draft"]["itens"].remove(target)
                continue
            if edit.field not in ITEM_FIELDS:
                raise ValueError("Campo do item inválido")
            if edit.field == "ingrediente_id" and edit.value is not None:
                if edit.value not in materials:
                    raise ValueError("Material fora do catálogo autorizado")
                target.pop("produto_novo", None)
                target.update(
                    criar_novo=False,
                    produto_id=None,
                    produto_revisao=None,
                    unidade_principal=materials[edit.value]["unit"],
                )
            if edit.field == "produto_id" and edit.value is not None:
                if edit.value not in products:
                    raise ValueError("Produto fora do catálogo autorizado")
                product = products[edit.value]
                target.update(
                    ingrediente_id=product["ingrediente_id"],
                    produto_revisao=product["revisao"],
                    criar_novo=False,
                    unidade_principal=materials[str(product["ingrediente_id"])]["unit"],
                )
                target.pop("produto_novo", None)
            if edit.field == "criar_novo" and edit.value is True:
                target.update(ingrediente_id=None, produto_id=None, produto_revisao=None)
        if edit.field in BOOL_FIELDS and not isinstance(edit.value, bool):
            raise ValueError("Campo booleano inválido")
        if edit.field in NUMERIC_FIELDS and edit.value is not None:
            if not isinstance(edit.value, str):
                raise ValueError("Informe decimal como texto")
            try:
                number = Decimal(edit.value.replace(",", "."))
                if (
                    not number.is_finite()
                    or number < 0
                    or (number == 0 and edit.field != "desconto_item")
                ):
                    raise ValueError("Decimal inválido")
            except InvalidOperation as exc:
                raise ValueError("Decimal inválido") from exc
        normalized = edit.value
        if edit.field in NUMERIC_FIELDS and edit.value is not None:
            normalized = str(number)
        if isinstance(edit.value, str) and len(edit.value) > 500:
            raise ValueError("Texto acima do limite")
        if edit.field.startswith("produto_novo.") and target.get("produto_id"):
            product = products.get(target["produto_id"])
            if not product:
                raise ValueError("Produto fora do catálogo autorizado")
            target["produto_novo"] = {
                k: product.get(k)
                for k in (
                    "nome",
                    "marca",
                    "fabricante",
                    "variante",
                    "conteudo_embalagem",
                    "unidade_conteudo",
                    "fator_para_principal",
                    "gtin",
                )
            }
            target.update(produto_id=None, produto_revisao=None)
        if "." in edit.field:
            parent, key = edit.field.split(".")
            if parent == "fornecedor_novo":
                target["fornecedor_id"] = None
            if not isinstance(target.get(parent), dict):
                target[parent] = {}
            target[parent][key] = normalized
        else:
            target[edit.field] = normalized
    before = copy.deepcopy(value["draft"]["itens"])
    value["draft"]["itens"] = group_items(value["draft"]["itens"])
    retained = {i["item_ref"] for i in value["draft"]["itens"]}
    value.setdefault("merged", []).extend(i for i in before if i["item_ref"] not in retained)
    return value
