from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from domain.compras.decisions import CatalogMatcher
from domain.compras.extraction import ReceiptExtractor, validate_receipt
from domain.compras.lista import calcular_sugestao_reposicao
from domain.compras.matching import IngredienteRef
from domain.compras.schemas import (
    ConfirmarCompraRequest,
    ConfirmarCompraResponse,
    ItemCompraSugerido,
    ItemListaCompras,
    ListaComprasResponse,
    OcrComprasResponse,
)
from domain.estoque.service import EstoqueService
from domain.exceptions import ValidationError

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from domain.compras.comercial import ComprasComerciais
    from domain.compras.comercial_schemas import LeituraCompra


class ComprasService:
    """
    Orquestra a entrada de compras via OCR de cupom fiscal.

    Lê a imagem com o adapter de OCR, sugere o vínculo de cada item com os
    ingredientes já cadastrados e, após a confirmação da usuária, delega ao
    EstoqueService a entrada de estoque (que recalcula o custo médio).
    """

    def __init__(
        self,
        estoque_service: EstoqueService,
        ocr_adapter: ReceiptExtractor,
        matcher: CatalogMatcher | None = None,
    ) -> None:
        self._estoque = estoque_service
        self._ocr = ocr_adapter
        self._matcher = matcher or CatalogMatcher()

    def comercial(self, db: AsyncSession) -> "ComprasComerciais":
        """Compartilha o núcleo de compras com os adaptadores web e WhatsApp."""
        from domain.compras.comercial import ComprasComerciais
        from domain.compras.repository import ComprasRepository

        return ComprasComerciais(ComprasRepository(db), self._estoque)

    async def ler_comercial(
        self, db: AsyncSession, tenant_id: UUID, content: bytes, mime: str
    ) -> "LeituraCompra":
        from domain.compras.reconhecimento import ReconhecimentoCompras

        return await ReconhecimentoCompras(self.comercial(db), self._ocr).ler(
            tenant_id, content, mime
        )

    async def processar_ocr(
        self, tenant_id: UUID, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> OcrComprasResponse:
        """Extrai itens do cupom e sugere o match com ingredientes cadastrados."""
        resultado = validate_receipt(await self._ocr.processar_imagem(image_bytes, mime_type))

        ingredientes = await self._estoque.listar(tenant_id)
        refs = [
            IngredienteRef(id=str(i.id), nome=i.nome, unidade=i.unidade, tipo=i.tipo)
            for i in ingredientes
        ]

        itens_sugeridos: list[ItemCompraSugerido] = []
        for item in resultado.itens:
            sugestao = await self._matcher.suggest(item.descricao, item.unidade, refs)
            itens_sugeridos.append(
                ItemCompraSugerido(
                    descricao=item.descricao,
                    quantidade=item.quantidade,
                    unidade=item.unidade,
                    preco_unitario=item.preco_unitario,
                    preco_total=item.preco_total,
                    ingrediente_id=UUID(sugestao.ingrediente_id)
                    if sugestao.ingrediente_id
                    else None,
                    nome_match=sugestao.nome_match,
                    score=sugestao.score,
                    tipo_sugerido=sugestao.tipo_sugerido,
                    unidade_sugerida=sugestao.unidade_sugerida,
                )
            )

        logger.info(
            "ocr_compras_processado",
            tenant_id=str(tenant_id),
            action="ocr",
            entity="compra",
            fonte=resultado.fonte,
            itens=len(itens_sugeridos),
            com_match=sum(1 for i in itens_sugeridos if i.ingrediente_id is not None),
        )

        return OcrComprasResponse(
            itens=itens_sugeridos,
            total=resultado.total,
            estabelecimento=resultado.estabelecimento,
            fonte=resultado.fonte,
            confianca=resultado.confianca,
            avisos=resultado.avisos,
        )

    async def confirmar(
        self,
        tenant_id: UUID,
        data: ConfirmarCompraRequest,
        *,
        chave: UUID | None = None,
        usuario: UUID | None = None,
        operador: UUID | None = None,
        origem: str = "legado",
    ) -> ConfirmarCompraResponse:
        """Adapta consumidores existentes ao núcleo atômico com histórico básico."""
        from decimal import ROUND_HALF_UP
        from uuid import uuid4

        from domain.compras.comercial import ComprasComerciais
        from domain.compras.comercial_schemas import CompraRevisada, ItemRevisado
        from domain.compras.repository import ComprasRepository

        revisados: list[ItemRevisado] = []
        for item in data.itens:
            if not item.criar_novo and item.ingrediente_id is None:
                raise ValidationError(
                    f"O item '{item.nome}' precisa ser vinculado a um ingrediente "
                    "existente ou marcado para cadastro."
                )
            revisados.append(
                ItemRevisado(
                    ingrediente_id=item.ingrediente_id,
                    criar_novo=item.criar_novo,
                    nome=item.nome,
                    tipo=item.tipo,
                    unidade=item.unidade,
                    descricao_original=item.descricao_original or item.nome,
                    quantidade=item.quantidade,
                    custo_unitario=item.custo_unitario,
                    preco_total=(item.quantidade * item.custo_unitario).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    ),
                    aceitar_excecao=True,
                )
            )
        request = CompraRevisada(
            itens=revisados, estabelecimento=data.estabelecimento, data_compra=data.data_compra
        )
        service = ComprasComerciais(ComprasRepository(self._estoque._repo._db), self._estoque)
        result = await service.confirmar(
            tenant_id,
            request,
            chave or uuid4(),
            usuario=usuario,
            operador=operador,
            origem=origem,
            legado=not all(i.descricao_original for i in data.itens),
        )
        return ConfirmarCompraResponse.model_validate(result.model_dump())

    async def lista_reposicao(self, tenant_id: UUID) -> ListaComprasResponse:
        """
        Lista inteligente de compras: ingredientes cujo saldo atingiu ou ficou
        abaixo do estoque mínimo, com quantidade sugerida e custo estimado.
        """
        ingredientes = await self._estoque.listar(tenant_id)

        itens: list[ItemListaCompras] = []
        total = Decimal("0")
        for ing in ingredientes:
            sugestao = calcular_sugestao_reposicao(
                saldo=ing.saldo,
                estoque_minimo=ing.estoque_minimo,
                custo_medio=ing.custo_medio,
            )
            if sugestao is None:
                continue
            quantidade, custo = sugestao
            total += custo
            itens.append(
                ItemListaCompras(
                    ingrediente_id=ing.id,
                    nome=ing.nome,
                    unidade=ing.unidade,
                    saldo=ing.saldo,
                    estoque_minimo=ing.estoque_minimo,
                    status_estoque=ing.status_estoque,
                    quantidade_sugerida=quantidade,
                    custo_estimado=custo,
                )
            )

        # Mais urgente primeiro: zerado > critico > baixo; desempate por nome.
        ordem = {"zerado": 0, "critico": 1, "baixo": 2, "ok": 3}
        itens.sort(key=lambda i: (ordem.get(i.status_estoque, 9), i.nome))

        return ListaComprasResponse(
            itens=itens,
            custo_total_estimado=total.quantize(Decimal("0.01")),
        )
