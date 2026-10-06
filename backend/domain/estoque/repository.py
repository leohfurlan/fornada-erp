from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.estoque.schemas import CriarIngredienteRequest
from infrastructure.database.models import Ingrediente, MovimentacaoEstoque, ReceitaIngrediente, Receita


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
            unidades_alternativas=[item.model_dump(mode="json") for item in data.unidades_alternativas],
            estoque_atual=data.estoque_inicial,
            quantidade_reservada=Decimal("0"),
            estoque_minimo=data.estoque_minimo,
            custo_medio=data.custo_inicial,
            data_custo_atualizado=data_custo,
        )
        self._db.add(ingrediente)
        await self._db.flush()
        return ingrediente

    async def buscar_por_id(self, ingrediente_id: UUID, tenant_id: UUID, *, for_update: bool = False) -> Ingrediente | None:
        stmt = select(Ingrediente).where(
            Ingrediente.id == ingrediente_id, Ingrediente.tenant_id == tenant_id,
            Ingrediente.deleted_at.is_(None),
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        result = await self._db.execute(stmt)
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

    async def unidades_receitas(self, ingrediente_id: UUID, tenant_id: UUID) -> list[str]:
        """Unidades usadas em receitas/fichas ativas do mesmo tenant."""
        result = await self._db.execute(select(ReceitaIngrediente.unidade).join(Receita).where(Receita.tenant_id == tenant_id, Receita.deleted_at.is_(None), ReceitaIngrediente.ingrediente_id == ingrediente_id))
        unidades = list(result.scalars().all())
        fichas = await self._db.execute(select(Receita.ficha_tecnica).where(Receita.tenant_id == tenant_id, Receita.deleted_at.is_(None)))
        for ficha in fichas.scalars():
            if ficha and ficha.get("composicao_ativa"):
                unidades.extend(p["unidade"] for p in ficha.get("passos", []) if p.get("ingrediente_id") == str(ingrediente_id))
        return unidades

    async def unidade_em_uso(self, ingrediente_id: UUID, tenant_id: UUID) -> bool:
        """Preserva unidade após histórico, uso em receitas ou produções."""
        from domain.receitas.repository import ReceitaRepository
        movimento = await self._db.execute(select(MovimentacaoEstoque.id).where(MovimentacaoEstoque.tenant_id == tenant_id, MovimentacaoEstoque.ingrediente_id == ingrediente_id).limit(1))
        return movimento.scalar_one_or_none() is not None or bool(await self.unidades_receitas(ingrediente_id, tenant_id)) or await ReceitaRepository(self._db).referencia_em_uso(ingrediente_id, tenant_id, "ingrediente_id")

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
