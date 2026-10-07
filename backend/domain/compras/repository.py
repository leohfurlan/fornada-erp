"""Persistência de catálogo, vínculos e compras sempre filtrada pela conta."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import NotFoundError
from infrastructure.database.compras_models import (
    AliasCompra,
    AprovacaoFornecedorProduto,
    Compra,
    CompraItem,
    FornecedorCompra,
    ProdutoCompra,
)
from infrastructure.database.models import Tenant


class ComprasRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def travar(self, tenant_id: UUID) -> None:
        """Serializa compras e catálogo com o lock da conta já usado na produção."""
        row = await self.db.scalar(
            select(Tenant.id).where(Tenant.id == tenant_id).with_for_update()
        )
        if row is None:
            raise NotFoundError("Conta")

    async def produto(self, tenant: UUID, id: UUID) -> ProdutoCompra:
        row = await self.db.scalar(
            select(ProdutoCompra)
            .where(
                ProdutoCompra.tenant_id == tenant,
                ProdutoCompra.id == id,
                ProdutoCompra.deleted_at.is_(None),
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise NotFoundError("Produto")
        return row

    async def fornecedor(self, tenant: UUID, id: UUID) -> FornecedorCompra:
        row = await self.db.scalar(
            select(FornecedorCompra)
            .where(
                FornecedorCompra.tenant_id == tenant,
                FornecedorCompra.id == id,
                FornecedorCompra.deleted_at.is_(None),
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise NotFoundError("Fornecedor")
        return row

    async def produtos(self, tenant: UUID) -> list[ProdutoCompra]:
        return list(
            (
                await self.db.scalars(
                    select(ProdutoCompra)
                    .where(ProdutoCompra.tenant_id == tenant, ProdutoCompra.deleted_at.is_(None))
                    .order_by(ProdutoCompra.nome, ProdutoCompra.id)
                )
            ).all()
        )

    async def fornecedores(self, tenant: UUID) -> list[FornecedorCompra]:
        return list(
            (
                await self.db.scalars(
                    select(FornecedorCompra)
                    .where(
                        FornecedorCompra.tenant_id == tenant, FornecedorCompra.deleted_at.is_(None)
                    )
                    .order_by(FornecedorCompra.nome, FornecedorCompra.id)
                )
            ).all()
        )

    async def aprovados(self, tenant: UUID, produto: UUID) -> list[UUID]:
        return list(
            (
                await self.db.scalars(
                    select(AprovacaoFornecedorProduto.fornecedor_id)
                    .join(
                        FornecedorCompra,
                        FornecedorCompra.id == AprovacaoFornecedorProduto.fornecedor_id,
                    )
                    .where(
                        AprovacaoFornecedorProduto.tenant_id == tenant,
                        AprovacaoFornecedorProduto.produto_id == produto,
                        AprovacaoFornecedorProduto.deleted_at.is_(None),
                        FornecedorCompra.tenant_id == tenant,
                        FornecedorCompra.deleted_at.is_(None),
                    )
                )
            ).all()
        )

    async def aprovar(self, tenant: UUID, produto: UUID, fornecedores: list[UUID]) -> None:
        """Substitui aprovações, preservando relações retiradas com soft delete."""
        await self.produto(tenant, produto)
        for fornecedor in fornecedores:
            await self.fornecedor(tenant, fornecedor)
        rows = list(
            (
                await self.db.scalars(
                    select(AprovacaoFornecedorProduto).where(
                        AprovacaoFornecedorProduto.tenant_id == tenant,
                        AprovacaoFornecedorProduto.produto_id == produto,
                    )
                )
            ).all()
        )
        existentes = {row.fornecedor_id: row for row in rows}
        for row in rows:
            row.deleted_at = None if row.fornecedor_id in fornecedores else datetime.now(UTC)
        for fornecedor in set(fornecedores) - existentes.keys():
            self.db.add(
                AprovacaoFornecedorProduto(
                    tenant_id=tenant, produto_id=produto, fornecedor_id=fornecedor
                )
            )
        await self.db.flush()

    async def aliases(self, tenant: UUID) -> list[AliasCompra]:
        return list(
            (
                await self.db.scalars(
                    select(AliasCompra)
                    .where(AliasCompra.tenant_id == tenant, AliasCompra.deleted_at.is_(None))
                    .order_by(AliasCompra.created_at, AliasCompra.id)
                )
            ).all()
        )

    async def alias(self, tenant: UUID, id: UUID) -> AliasCompra:
        row = await self.db.scalar(
            select(AliasCompra)
            .where(
                AliasCompra.tenant_id == tenant,
                AliasCompra.id == id,
                AliasCompra.deleted_at.is_(None),
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise NotFoundError("Vínculo")
        return row

    async def por_chave(self, tenant: UUID, chave: UUID) -> Compra | None:
        return await self.db.scalar(
            select(Compra).where(Compra.tenant_id == tenant, Compra.chave == chave)
        )

    async def duplicadas(self, tenant: UUID, identidade: str | None) -> list[Compra]:
        if not identidade:
            return []
        return list(
            (
                await self.db.scalars(
                    select(Compra).where(
                        Compra.tenant_id == tenant,
                        Compra.identidade_nota == identidade,
                        Compra.deleted_at.is_(None),
                    )
                )
            ).all()
        )

    async def compra(self, tenant: UUID, id: UUID) -> Compra:
        row = await self.db.scalar(
            select(Compra).where(
                Compra.tenant_id == tenant, Compra.id == id, Compra.deleted_at.is_(None)
            )
        )
        if row is None:
            raise NotFoundError("Compra")
        return row

    async def itens(self, tenant: UUID, compra: UUID) -> list[CompraItem]:
        return list(
            (
                await self.db.scalars(
                    select(CompraItem)
                    .where(
                        CompraItem.tenant_id == tenant,
                        CompraItem.compra_id == compra,
                        CompraItem.deleted_at.is_(None),
                    )
                    .order_by(CompraItem.indice)
                )
            ).all()
        )

    async def historico(
        self,
        tenant: UUID,
        *,
        ingrediente_id: UUID | None = None,
        produto_id: UUID | None = None,
        fornecedor_id: UUID | None = None,
        marca: str | None = None,
        inicio: date | None = None,
        fim: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Compra], int]:
        """Filtra compras sem perder a fotografia comercial de cadastros inativados."""
        predicates = [Compra.tenant_id == tenant, Compra.deleted_at.is_(None)]
        if fornecedor_id:
            predicates.append(Compra.fornecedor_id == fornecedor_id)
        if inicio:
            predicates.append(Compra.data_compra >= inicio)
        if fim:
            predicates.append(Compra.data_compra <= fim)
        item_predicates = [
            CompraItem.tenant_id == tenant,
            CompraItem.compra_id == Compra.id,
            CompraItem.deleted_at.is_(None),
        ]
        if ingrediente_id:
            item_predicates.append(CompraItem.ingrediente_id == ingrediente_id)
        if produto_id:
            item_predicates.append(CompraItem.produto_id == produto_id)
        if marca:
            item_predicates.append(func.lower(CompraItem.snapshot["marca"].astext) == marca.lower())
        if ingrediente_id or produto_id or marca:
            predicates.append(select(CompraItem.id).where(*item_predicates).exists())
        count = await self.db.scalar(select(func.count()).select_from(Compra).where(*predicates))
        rows = list(
            (
                await self.db.scalars(
                    select(Compra)
                    .where(*predicates)
                    .order_by(
                        Compra.data_compra.desc().nulls_last(),
                        Compra.created_at.desc(),
                        Compra.id.desc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        return rows, int(count or 0)
