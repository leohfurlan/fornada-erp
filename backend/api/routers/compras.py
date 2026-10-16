from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_id
from core.rate_limit import limiter
from domain.compras.schemas import (
    ConfirmarCompraRequest,
    ConfirmarCompraResponse,
    ListaComprasResponse,
    OcrComprasResponse,
)
from domain.compras.service import ComprasService
from domain.estoque.repository import EstoqueRepository
from domain.estoque.service import EstoqueService
from domain.exceptions import ValidationError
from infrastructure.database.session import get_db
from infrastructure.ocr.factory import get_receipt_extractor

router = APIRouter(prefix="/compras", tags=["Compras"])

# Limite de tamanho do upload do cupom (evita abuso e estouro de memória).
TAMANHO_MAX_BYTES = 8 * 1024 * 1024  # 8 MB
MIMES_ACEITOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "application/xml",
    "text/xml",
}


def get_compras_service(db: AsyncSession = Depends(get_db)) -> ComprasService:
    estoque_service = EstoqueService(EstoqueRepository(db))
    return ComprasService(estoque_service, get_receipt_extractor())


@router.post("/ocr", response_model=OcrComprasResponse)
@limiter.limit("20/minute")
async def processar_cupom(
    request: Request,
    arquivo: UploadFile = File(...),
    tenant_id: UUID = Depends(get_tenant_id),
    service: ComprasService = Depends(get_compras_service),
) -> OcrComprasResponse:
    """
    Recebe a foto do cupom fiscal, extrai os itens via OCR e sugere o vínculo
    de cada item com os ingredientes já cadastrados. Não grava nada — apenas
    devolve a prévia para a usuária revisar e confirmar.
    """
    if arquivo.content_type and arquivo.content_type not in MIMES_ACEITOS:
        raise ValidationError(
            "Formato não suportado. Envie uma foto em JPG/PNG ou um XML NF-e/NFC-e."
        )

    conteudo = await arquivo.read(TAMANHO_MAX_BYTES + 1)
    if not conteudo:
        raise ValidationError("Não recebemos a imagem. Tente tirar a foto novamente.")
    if len(conteudo) > TAMANHO_MAX_BYTES:
        raise ValidationError("A imagem é muito grande. Use uma foto de até 8 MB.")

    mime = arquivo.content_type or "image/jpeg"
    return await service.processar_ocr(tenant_id, conteudo, mime)


@router.post("/confirmar", response_model=ConfirmarCompraResponse)
async def confirmar_compra(
    data: ConfirmarCompraRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    service: ComprasService = Depends(get_compras_service),
    db: AsyncSession = Depends(get_db),
) -> ConfirmarCompraResponse:
    """
    Grava a compra revisada: cria ingredientes novos e dá entrada nos
    existentes, recalculando o custo médio de cada um.
    """
    result = await service.confirmar(tenant_id, data)
    await db.commit()
    return result


@router.get("/lista-sugerida", response_model=ListaComprasResponse)
async def lista_sugerida(
    tenant_id: UUID = Depends(get_tenant_id),
    service: ComprasService = Depends(get_compras_service),
) -> ListaComprasResponse:
    """
    Lista inteligente de compras: ingredientes que atingiram o estoque mínimo,
    com quantidade sugerida de recompra e custo total estimado.
    """
    return await service.lista_reposicao(tenant_id)
