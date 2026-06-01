from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models import (
    EstoqueProdutoAcabado,
    MovimentacaoEstoquePA,
    Receita,
)


class EstoquePARepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def buscar_ou_criar(
        self, receita_id: UUID, tenant_id: UUID
    ) -> EstoqueProdutoAcabado:
        """Idempotente: retorna saldo existente ou cria com qtd=0.

        Usado tanto por OP finalizando (entrada) quanto por Venda/Pedido (saída).
        Na primeira referência cria um registro zerado — assim qualquer receita
        tem um saldo consultável mesmo antes de qualquer movimentação.
        """
        result = await self._db.execute(
            select(EstoqueProdutoAcabado).where(
                EstoqueProdutoAcabado.receita_id == receita_id,
                EstoqueProdutoAcabado.tenant_id == tenant_id,
                EstoqueProdutoAcabado.deleted_at.is_(None),
            )
        )
        existente = result.scalar_one_or_none()
        if existente:
            return existente

        novo = EstoqueProdutoAcabado(
            tenant_id=tenant_id,
            receita_id=receita_id,
            qtd_disponivel=Decimal("0"),
            qtd_minima=Decimal("0"),
        )
        self._db.add(novo)
        await self._db.flush()
        return novo

    async def buscar_por_receita(
        self, receita_id: UUID, tenant_id: UUID
    ) -> EstoqueProdutoAcabado | None:
        result = await self._db.execute(
            select(EstoqueProdutoAcabado).where(
                EstoqueProdutoAcabado.receita_id == receita_id,
                EstoqueProdutoAcabado.tenant_id == tenant_id,
                EstoqueProdutoAcabado.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def listar(self, tenant_id: UUID) -> list[EstoqueProdutoAcabado]:
        result = await self._db.execute(
            select(EstoqueProdutoAcabado)
            .options(selectinload(EstoqueProdutoAcabado.receita))
            .where(
                EstoqueProdutoAcabado.tenant_id == tenant_id,
                EstoqueProdutoAcabado.deleted_at.is_(None),
            )
        )
        # Ordena por nome da receita (case-insensitive em pt-BR é tratável,
        # mas pra MVP a ordem alfabética simples basta).
        registros = list(result.scalars().all())
        registros.sort(key=lambda r: (r.receita.nome if r.receita else "").lower())
        return registros

    async def salvar_movimentacao(
        self,
        receita_id: UUID,
        tenant_id: UUID,
        tipo: str,
        quantidade: Decimal,
        origem: str,
    ) -> MovimentacaoEstoquePA:
        mov = MovimentacaoEstoquePA(
            tenant_id=tenant_id,
            receita_id=receita_id,
            tipo=tipo,
            quantidade=quantidade,
            origem=origem,
        )
        self._db.add(mov)
        await self._db.flush()
        return mov

    async def listar_movimentacoes(
        self,
        receita_id: UUID,
        tenant_id: UUID,
        limit: int,
        offset: int,
    ) -> list[MovimentacaoEstoquePA]:
        result = await self._db.execute(
            select(MovimentacaoEstoquePA)
            .where(
                MovimentacaoEstoquePA.receita_id == receita_id,
                MovimentacaoEstoquePA.tenant_id == tenant_id,
                MovimentacaoEstoquePA.deleted_at.is_(None),
            )
            .order_by(desc(MovimentacaoEstoquePA.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def buscar_receita(self, receita_id: UUID, tenant_id: UUID) -> Receita | None:
        result = await self._db.execute(
            select(Receita).where(
                Receita.id == receita_id,
                Receita.tenant_id == tenant_id,
                Receita.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
