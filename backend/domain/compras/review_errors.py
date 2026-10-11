"""Public, value-free purchase diagnostics. Never serialize exception/input text."""

from contextlib import contextmanager

from domain.exceptions import ConflictError, NotFoundError, ValidationError

# code: field, action, operator instruction. Only these literals cross the boundary.
ISSUES = {
    "supplier_required": (
        "fornecedor_id",
        "select_supplier",
        "Selecione uma loja ou prepare o cadastro de uma nova antes de aprová-la.",
    ),
    "product_required": (
        "produto_id",
        "select_product",
        "Selecione um produto ou prepare seu cadastro antes de aprová-lo.",
    ),
    "product_approval_required": (
        "aprovar_produto",
        "review_approval",
        "Inclua a aprovação do produto no resumo ou marque somente esta compra como exceção.",
    ),
    "supplier_approval_required": (
        "aprovar_fornecedor",
        "review_approval",
        "Inclua a aprovação da loja para este produto ou marque somente esta compra como exceção.",
    ),
    "product_version_changed": (
        "produto_revisao",
        "refresh_catalog",
        "Atualize o catálogo e selecione novamente o produto; confira os dados antes de salvar.",
    ),
    "proposal_version_changed": (
        "expected_version",
        "refresh_proposal",
        "Atualize a proposta e confira a revisão antes de salvar novamente.",
    ),
    "proposal_expired": (
        "proposal_id",
        "review_in_fornada",
        "A proposta expirou. Revise a compra diretamente no Fornada.",
    ),
    "product_material_mismatch": (
        "produto_id",
        "select_product",
        "Escolha um produto pertencente ao material selecionado.",
    ),
    "material_unavailable": (
        "ingrediente_id",
        "refresh_catalog",
        "Selecione um material disponível no catálogo autorizado.",
    ),
    "product_unavailable": (
        "produto_id",
        "refresh_catalog",
        "Selecione um produto disponível no catálogo autorizado.",
    ),
    "supplier_unavailable": (
        "fornecedor_id",
        "refresh_catalog",
        "Selecione uma loja disponível no catálogo autorizado.",
    ),
    "supplier_exists": (
        "fornecedor_novo",
        "select_supplier",
        "A loja já está cadastrada; selecione a loja existente no catálogo autorizado.",
    ),
    "content_conversion_required": (
        "produto_novo.unidade_conteudo",
        "configure_conversion",
        "Confira a unidade do conteúdo e configure sua conversão para a unidade de "
        "estoque no Fornada.",
    ),
    "content_conversion_conflict": (
        "produto_novo.fator_para_principal",
        "configure_conversion",
        "A conversão deve coincidir com a equivalência já confirmada no material.",
    ),
    "fiscal_conversion_required": (
        "unidade",
        "configure_conversion",
        "Confira a unidade fiscal e configure sua conversão para a unidade de estoque no Fornada.",
    ),
    "variant_mismatch": (
        "produto_novo.variante",
        "check_package",
        "A variante descrita no cupom difere do produto; confira a seleção e a descrição.",
    ),
    "package_mismatch": (
        "produto_novo.conteudo_embalagem",
        "check_package",
        "O conteúdo descrito no cupom difere do produto; confira a embalagem selecionada.",
    ),
    "gtin_mismatch": (
        "gtin_confirmado",
        "select_product",
        "Confira o GTIN e o produto selecionado; os códigos não coincidem.",
    ),
    "gtin_exists": (
        "gtin_confirmado",
        "select_product",
        "O GTIN já pertence a outro produto; confira o catálogo autorizado.",
    ),
    "item_total_mismatch": (
        "preco_total",
        "check_amounts",
        "Confira quantidade × preço unitário − desconto = total. Em grupos, "
        "quantidade, desconto e total já estão somados.",
    ),
    "stock_precision_exceeded": (
        "quantidade",
        "check_amounts",
        "A quantidade convertida precisa caber na precisão do estoque (quatro casas decimais).",
    ),
    "stock_limit_exceeded": (
        "quantidade",
        "check_amounts",
        "A entrada excede o limite do estoque; confira a quantidade e a conversão.",
    ),
    "cost_limit_exceeded": (
        "custo_unitario",
        "check_amounts",
        "O custo convertido excede o limite do estoque; confira os valores e a conversão.",
    ),
    "future_purchase_date": (
        "data_compra",
        "check_date",
        "A data da compra não pode estar no futuro.",
    ),
    "duplicate_review_required": (
        "confirmar_duplicidade",
        "review_in_fornada",
        "Confira a possível duplicidade diretamente no Fornada.",
    ),
    "link_requirements": (
        "guardar_vinculo",
        "review_approval",
        "Para guardar o vínculo, selecione e inclua a aprovação do produto e da loja.",
    ),
    "review_conflict": (
        "conflito_vinculo",
        "refresh_catalog",
        "O vínculo mudou ou está em conflito; confira o catálogo no Fornada.",
    ),
    "review_invalid": ("reviewed", "check_fields", "Confira os campos da revisão no Fornada."),
    "material_selection_invalid": (
        "ingrediente_id",
        "select_material",
        "Escolha um material existente ou prepare um novo, sem combinar os dois modos.",
    ),
    "product_selection_invalid": (
        "produto_id",
        "select_product",
        "Selecione um produto com sua revisão atual ou prepare um novo produto, sem "
        "combinar os modos.",
    ),
    "exception_link_conflict": (
        "guardar_vinculo",
        "review_approval",
        "Uma compra excepcional não pode guardar aprovação permanente.",
    ),
    "supplier_selection_invalid": (
        "fornecedor_id",
        "select_supplier",
        "Escolha uma loja existente ou prepare uma nova, sem combinar os modos.",
    ),
    "receipt_identity_required": (
        "identidade_nota",
        "check_fields",
        "Informe a identidade da nota antes de confirmá-la.",
    ),
    "field_required": ("reviewed", "check_fields", "Preencha o campo obrigatório."),
    "invalid_value": (
        "reviewed",
        "check_fields",
        "Confira o formato, o valor e os limites do campo.",
    ),
    "brand_required": (
        "produto_novo.marca",
        "check_fields",
        "Informe a marca confirmada do novo produto; não invente uma marca para salvar.",
    ),
    "invalid_gtin": (
        "gtin",
        "check_fields",
        "Informe um GTIN válido e confira o dígito verificador.",
    ),
    "invalid_cnpj": (
        "fornecedor_novo.cnpj",
        "check_fields",
        "Informe um CNPJ válido e confira os dígitos verificadores.",
    ),
}


def issue(code, item_index=None, field=None):
    default, action, message = ISSUES[code]
    return {
        "code": code,
        "item_index": item_index,
        "field": field or default,
        "action": action,
        "message": message,
    }


def detail(errors):
    return {
        "code": "purchase_review_invalid",
        "message": "Confira os campos indicados antes de preparar o resumo.",
        "errors": errors,
    }


class PurchaseReviewError(ValidationError):
    def __init__(self, code, *, item_index=None, status_code=422):
        self.issue = issue(code, item_index)
        self.status_code = status_code
        super().__init__(self.issue["message"])
        self.code = code


class PurchaseReviewConflict(ConflictError):
    def __init__(self, code, *, item_index=None):
        self.issue = issue(code, item_index)
        self.status_code = 409
        super().__init__(self.issue["message"])
        self.code = code


class PurchaseReviewUnavailable(NotFoundError):
    def __init__(self, code):
        self.issue = issue(code)
        self.status_code = 422
        super().__init__("Referência autorizada")
        self.code = code


@contextmanager
def review_item(index, item):
    try:
        yield
    except (PurchaseReviewError, PurchaseReviewConflict, PurchaseReviewUnavailable) as exc:
        exc.issue["item_index"] = index
        if item.produto_id and exc.issue["field"].startswith("produto_novo."):
            exc.issue["field"] = "produto_id"
        raise
    except (ConflictError, NotFoundError, ValidationError) as exc:
        if isinstance(exc, ConflictError):
            raise PurchaseReviewConflict("review_conflict", item_index=index) from None
        if isinstance(exc, NotFoundError):
            error = PurchaseReviewUnavailable("review_invalid")
            error.issue["item_index"] = index
            raise error from None
        raise PurchaseReviewError("review_invalid", item_index=index) from None


def schema_issues(errors):
    """Paths are restricted to contract fields, never unknown keys or input values."""
    from domain.compras.comercial_schemas import (
        CompraRevisada,
        FornecedorCriar,
        ItemRevisado,
        ProdutoDados,
    )

    allowed = (
        set(CompraRevisada.model_fields)
        | set(ItemRevisado.model_fields)
        | set(ProdutoDados.model_fields)
        | set(FornecedorCriar.model_fields)
        | {"expected_version", "proposal_id"}
    )
    result = []
    for error in errors[:100]:
        loc = list(error["loc"])
        index = None
        if "itens" in loc:
            pos = loc.index("itens") + 1
            if pos < len(loc) and type(loc[pos]) is int:
                index = loc[pos]
                loc = loc[pos + 1 :]
        fields = [part for part in loc if isinstance(part, str) and part in allowed]
        field = ".".join(part for part in fields if part != "reviewed") or None
        code = (
            error["type"]
            if error["type"] in ISSUES
            else "field_required"
            if error["type"] == "missing"
            else "invalid_value"
        )
        if fields and fields[-1] in {"gtin", "gtin_confirmado", "cnpj"}:
            code = "invalid_cnpj" if fields[-1] == "cnpj" else "invalid_gtin"
        if fields and fields[-1] == "marca":
            code = "brand_required"
        result.append(issue(code, index, field))
    return result
