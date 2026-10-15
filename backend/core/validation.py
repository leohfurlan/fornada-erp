"""Public, localized validation issues, without submitted values or internal exceptions."""


def schema_issues(errors: list[dict]) -> list[dict]:
    issues = []
    for error in errors:
        kind = error.get("type", "")
        ctx = error.get("ctx", {})
        message = "Confira o preenchimento deste campo."
        if kind == "missing":
            message = "Preencha este campo."
        elif kind == "string_too_short":
            message = f"Informe pelo menos {ctx.get('min_length', 1)} caractere(s)."
        elif kind == "string_too_long":
            message = f"Use no máximo {ctx.get('max_length')} caracteres."
        elif kind in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
            phrases = {
                "greater_than": ("maior que", "gt"),
                "greater_than_equal": ("maior ou igual a", "ge"),
                "less_than": ("menor que", "lt"),
                "less_than_equal": ("menor ou igual a", "le"),
            }
            phrase, key = phrases[kind]
            message = f"Informe um valor {phrase} {ctx.get(key)}."
        elif any(part in kind for part in ("decimal", "float", "int_")):
            message = "Informe um número válido."
        elif "date" in kind:
            message = "Informe uma data válida."
        elif "uuid" in kind or "literal" in kind or "enum" in kind:
            message = "Selecione uma opção válida."
        elif kind == "too_short":
            message = f"Informe pelo menos {ctx.get('min_length', 1)} item(ns)."
        elif kind == "too_long":
            message = f"Use no máximo {ctx.get('max_length')} item(ns)."
        elif kind == "value_error":
            raw = str(error.get("msg", "")).removeprefix("Value error, ")
            if "email" in raw.lower() or "e-mail" in raw.lower():
                message = "Informe um e-mail válido."
            elif raw and not any(word in raw for word in ("Input ", "String ", "valid ")):
                message = raw
        location = list(error.get("loc", []))
        if location and location[0] in ("body", "query", "path"):
            location = location[1:]
        selections = {
            "material_selection_invalid": ("ingrediente_id", "Selecione um material."),
            "product_selection_invalid": (
                "produto_id",
                "Confira o produto e a embalagem selecionados.",
            ),
            "supplier_selection_invalid": (
                "fornecedor_id",
                "Selecione uma loja ou cadastre uma nova.",
            ),
            "receipt_identity_required": ("identidade_nota", "Informe a chave fiscal da nota."),
            "exception_link_conflict": (
                "guardar_vinculo",
                "Desmarque o vínculo ao registrar uma compra excepcional.",
            ),
        }
        if kind in selections:
            field, message = selections[kind]
            location.append(field)
        issues.append({"path": ".".join(map(str, location)), "message": message})
    return issues
