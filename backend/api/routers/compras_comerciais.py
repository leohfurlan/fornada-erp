"""Interfaces tenant-scoped do catálogo e do fluxo comercial de compras."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_authenticated_actor, get_current_user, get_tenant_id
from api.routers.compras import MIMES_ACEITOS, TAMANHO_MAX_BYTES
from core.rate_limit import limiter
from domain.compras.comercial import ComprasComerciais
from domain.compras.comercial_schemas import (
    CompraDetalhada,
    CompraRevisada,
    FornecedorCriar,
    FornecedorEditar,
    FornecedorResponse,
    LeituraCompra,
    PaginaCompras,
    PaginaFornecedores,
    PaginaProdutos,
    PaginaVinculos,
    PreviaCompra,
    ProdutoCriar,
    ProdutoEditar,
    ProdutoResponse,
    ReconhecerRequest,
    ReconhecerResponse,
    ResultadoCompra,
    VinculoEditar,
    VinculoResponse,
)
from domain.compras.reconhecimento import ReconhecimentoCompras
from domain.compras.repository import ComprasRepository
from domain.estoque.repository import EstoqueRepository
from domain.estoque.service import EstoqueService
from domain.exceptions import ValidationError
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db
from infrastructure.ocr.factory import get_receipt_extractor

router = APIRouter(prefix="/compras", tags=["Compras"])


def get_comerciais(db: AsyncSession = Depends(get_db)) -> ComprasComerciais:
    return ComprasComerciais(ComprasRepository(db), EstoqueService(EstoqueRepository(db)))


def get_reconhecimento(
    service: ComprasComerciais = Depends(get_comerciais),
) -> ReconhecimentoCompras:
    return ReconhecimentoCompras(service, get_receipt_extractor())


@router.get("/produtos", response_model=PaginaProdutos)
async def produtos(
    ingrediente_id: UUID | None = None,
    aprovado: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
) -> PaginaProdutos:
    return await service.catalogo.listar_produtos(tenant, ingrediente_id, aprovado, limit, offset)


@router.post("/produtos", response_model=ProdutoResponse, status_code=201)
async def criar_produto(
    data: ProdutoCriar,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> ProdutoResponse:
    row = await service.catalogo.criar_produto(tenant, data)
    result = await service.catalogo.produto_response(tenant, row)
    await db.commit()
    return result


@router.get("/produtos/{id}", response_model=ProdutoResponse)
async def produto(
    id: UUID,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
) -> ProdutoResponse:
    return await service.catalogo.produto_response(tenant, await service.repo.produto(tenant, id))


@router.patch("/produtos/{id}", response_model=ProdutoResponse)
async def editar_produto(
    id: UUID,
    data: ProdutoEditar,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> ProdutoResponse:
    row = await service.catalogo.editar_produto(tenant, id, data)
    await db.refresh(row)
    result = await service.catalogo.produto_response(tenant, row)
    await db.commit()
    return result


@router.delete("/produtos/{id}", status_code=204)
async def apagar_produto(
    id: UUID,
    revisao: int = Query(ge=1),
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.catalogo.apagar_produto(tenant, id, revisao)
    await db.commit()


@router.get("/fornecedores", response_model=PaginaFornecedores)
async def fornecedores(
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
) -> PaginaFornecedores:
    return await service.catalogo.listar_fornecedores(tenant, q, limit, offset)


@router.post("/fornecedores", response_model=FornecedorResponse, status_code=201)
async def criar_fornecedor(
    data: FornecedorCriar,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> FornecedorResponse:
    row = await service.catalogo.criar_fornecedor(tenant, data)
    result = FornecedorResponse.model_validate(row, from_attributes=True)
    await db.commit()
    return result


@router.patch("/fornecedores/{id}", response_model=FornecedorResponse)
async def editar_fornecedor(
    id: UUID,
    data: FornecedorEditar,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> FornecedorResponse:
    row = await service.catalogo.editar_fornecedor(tenant, id, data)
    result = FornecedorResponse.model_validate(row, from_attributes=True)
    await db.commit()
    return result


@router.delete("/fornecedores/{id}", status_code=204)
async def apagar_fornecedor(
    id: UUID,
    revisao: int = Query(ge=1),
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.catalogo.apagar_fornecedor(tenant, id, revisao)
    await db.commit()


@router.get("/vinculos", response_model=PaginaVinculos)
async def vinculos(
    fornecedor_id: UUID | None = None,
    produto_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
) -> PaginaVinculos:
    if fornecedor_id:
        await service.repo.fornecedor(tenant, fornecedor_id)
    if produto_id:
        await service.repo.produto(tenant, produto_id)
    rows = [
        r
        for r in await service.repo.aliases(tenant)
        if (not fornecedor_id or r.fornecedor_id == fornecedor_id)
        and (not produto_id or r.produto_id == produto_id)
    ]
    return PaginaVinculos(
        itens=[
            VinculoResponse(
                **{
                    field: getattr(row, field)
                    for field in VinculoResponse.model_fields
                    if field != "ativo"
                },
                ativo=True,
            )
            for row in rows[offset : offset + limit]
        ],
        total=len(rows),
    )


@router.patch("/vinculos/{id}", response_model=VinculoResponse)
async def editar_vinculo(
    id: UUID,
    data: VinculoEditar,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> VinculoResponse:
    result = await service.catalogo.editar_vinculo(tenant, id, data)
    await db.commit()
    return result


@router.delete("/vinculos/{id}", status_code=204)
async def apagar_vinculo(
    id: UUID,
    revisao: int = Query(ge=1),
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.catalogo.apagar_vinculo(tenant, id, revisao)
    await db.commit()


@router.post("/v2/prever", response_model=PreviaCompra)
async def prever(
    data: CompraRevisada,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
) -> PreviaCompra:
    return await service.prever(tenant, data)


@router.post("/v2/confirmar", response_model=ResultadoCompra)
async def confirmar(
    data: CompraRevisada,
    chave: UUID = Header(alias="Idempotency-Key"),
    tenant: UUID = Depends(get_tenant_id),
    usuario: Usuario = Depends(get_current_user),
    operador: Usuario = Depends(get_authenticated_actor),
    service: ComprasComerciais = Depends(get_comerciais),
    db: AsyncSession = Depends(get_db),
) -> ResultadoCompra:
    result = await service.confirmar(tenant, data, chave, usuario=usuario.id, operador=operador.id)
    await db.commit()
    return result


@router.post("/v2/ocr", response_model=LeituraCompra)
@limiter.limit("20/minute")
async def ocr(
    request: Request,
    arquivo: UploadFile = File(...),
    fornecedor_id: UUID | None = None,
    tenant: UUID = Depends(get_tenant_id),
    service: ReconhecimentoCompras = Depends(get_reconhecimento),
) -> LeituraCompra:
    if arquivo.content_type and arquivo.content_type not in MIMES_ACEITOS:
        raise ValidationError("Formato não suportado. Envie uma imagem JPG, PNG ou WebP.")
    image = await arquivo.read(TAMANHO_MAX_BYTES + 1)
    if not image or len(image) > TAMANHO_MAX_BYTES:
        raise ValidationError("Envie uma imagem de até 8 MB.")
    return await service.ler(tenant, image, arquivo.content_type or "image/jpeg", fornecedor_id)


@router.post("/v2/reconhecer", response_model=ReconhecerResponse)
async def reconhecer(
    data: ReconhecerRequest,
    tenant: UUID = Depends(get_tenant_id),
    service: ReconhecimentoCompras = Depends(get_reconhecimento),
) -> ReconhecerResponse:
    return await service.reconhecer(tenant, data.fornecedor_id, data.itens)


@router.get("/historico", response_model=PaginaCompras)
async def historico(
    ingrediente_id: UUID | None = None,
    produto_id: UUID | None = None,
    fornecedor_id: UUID | None = None,
    marca: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
) -> PaginaCompras:
    return await service.historico(
        tenant,
        ingrediente_id=ingrediente_id,
        produto_id=produto_id,
        fornecedor_id=fornecedor_id,
        marca=marca,
        inicio=data_inicio,
        fim=data_fim,
        limit=limit,
        offset=offset,
    )


@router.get("/historico/{id}", response_model=CompraDetalhada)
async def detalhe(
    id: UUID,
    tenant: UUID = Depends(get_tenant_id),
    service: ComprasComerciais = Depends(get_comerciais),
) -> CompraDetalhada:
    return await service.detalhe(tenant, id)
