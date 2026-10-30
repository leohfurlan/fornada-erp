"""The web response must retain the item and field from purchase validation."""

from types import SimpleNamespace

import pytest

from domain.compras.review_errors import PurchaseReviewError, review_item
from main import error_detail


@pytest.mark.parametrize("product_id,field", [
    (None, "produto_novo.unidade_conteudo"),
    ("existing-product", "produto_id"),
])
def test_conversion_error_identifies_item_and_field(product_id, field):
    """A failure in the fifth submitted item highlights its own control."""
    with pytest.raises(PurchaseReviewError) as caught:
        with review_item(4, SimpleNamespace(produto_id=product_id)):
            raise PurchaseReviewError("content_conversion_required")

    response = error_detail(caught.value)
    assert response["field_errors"] == [{
        "path": f"itens.4.{field}",
        "message": caught.value.message,
    }]
    assert "Conversão específica do conteúdo" in response["detail"]
