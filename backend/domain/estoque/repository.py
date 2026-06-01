from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.estoque.schemas import CriarIngredienteRequest
from infrastructure.database.models import Ingrediente, MovimentacaoEstoque, ReceitaIngrediente


class EstoqueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _proximo_codigo(self, tenant_id: UUID) -> int:
        """Próximo código sequencial dentro do tenant (1, 2, 3...)."""
        result = await self._db.execute(
            select(func.coalesce(func.max(Ingrediente.codigo), 0)).where(
                Ingrediente.tenant_id == tenant_id
            )
        )
        return int(result.scalar() or 0) + 1

    async def criar_ingrediente(
        self, tenant_id: UUID, data: CriarIngredienteRequest
    ) -> Ingrediente:
        codigo = await self._proximo_codigo(tenant_id)
        data_custo = datetime.now(UTC) if data.custo_inicial > 0 else None
        ingrediente = Ingrediente(
            tenant_id=tenant_id,
            codigo=codigo,
            tipo=data.tipo,
            nome=data.nome,
            unidade=data.unidade,
            estoque_atual=data.estoque_inicial,
            quantidade_reservada=Decimal("0"),
            estoque_minimo=data.estoque_minimo,
            custo_medio=data.custo_inicial,
            data_custo_atualizado=data_custo,
        )
        self._db.add(ingrediente)
        await self._db.flush()
        return ingrediente

    async def buscar_por_id(self, ingrediente_id: UUID, tenant_id: UUID) -> Ingrediente | None:
        result = await self._db.execute(
            select(Ingrediente).where(
                Ingrediente.id == ingrediente_id,
                Ingrediente.tenant_id == tenant_id,
                Ingrediente.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def listar(self, tenant_id: UUID) -> list[Ingrediente]:
        result = await self._db.execute(
            select(Ingrediente)
            .where(Ingrediente.tenant_id == tenant_id, Ingrediente.deleted_at.is_(None))
            .order_by(Ingrediente.nome)
        )
        return list(result.scalars().all())

    async def ingrediente_em_uso(self, ingrediente_id: UUID) -> bool:
        """Verifica se o ingrediente está referenciado em alguma receita ativa."""
        result = await self._db.execute(
            select(ReceitaIngrediente.id)
            .where(ReceitaIngrediente.ingrediente_id == ingrediente_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def soft_delete(self, ingrediente: Ingrediente) -> None:
        ingrediente.deleted_at = datetime.now(UTC)
        await self._db.flush()

    async def listar_movimentacoes(
        self,
        ingrediente_id: UUID,
        tenant_id: UUID,
        limit: int,
        offset: int,
    ) -> list[MovimentacaoEstoque]:
        result = await self._db.execute(
            select(MovimentacaoEstoque)
            .where(
                MovimentacaoEstoque.ingrediente_id == ingrediente_id,
                MovimentacaoEstoque.tenant_id == tenant_id,
                MovimentacaoEstoque.deleted_at.is_(None),
            )
            .order_by(desc(MovimentacaoEstoque.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def salvar_movimentacao(
        self,
        tenant_id: UUID,
        ingrediente_id: UUID,
        tipo: str,
        quantidade,
        custo_unitario,
        origem: str,
    ) -> MovimentacaoEstoque:
        mov = MovimentacaoEstoque(
            tenant_id=tenant_id,
            ingrediente_id=ingrediente_id,
            tipo=tipo,
            quantidade=quantidade,
            custo_unitario=custo_unitario,
            origem=origem,
        )
        self._db.add(mov)
        await self._db.flush()
        return mov
