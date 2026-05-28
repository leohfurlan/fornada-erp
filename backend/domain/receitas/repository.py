from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.receitas.schemas import CriarReceitaRequest
from infrastructure.database.models import Ingrediente, Receita, ReceitaEtapa, ReceitaIngrediente


class ReceitaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def criar(self, tenant_id: UUID, data: CriarReceitaRequest) -> Receita:
        receita = Receita(
            tenant_id=tenant_id,
            nome=data.nome,
            categoria=data.categoria,
            rendimento=data.rendimento,
            rendimento_unidade=data.rendimento_unidade,
            margem_desejada=data.margem_desejada,
            modo_preparo=data.modo_preparo,
        )
        self._db.add(receita)
        await self._db.flush()

        for item in data.ingredientes:
            ri = ReceitaIngrediente(
                receita_id=receita.id,
                ingrediente_id=item.ingrediente_id,
                quantidade=item.quantidade,
                unidade=item.unidade,
            )
            self._db.add(ri)

        for etapa in data.etapas:
            re = ReceitaEtapa(
                receita_id=receita.id,
                nome=etapa.nome,
                duracao_minutos=etapa.duracao_minutos,
                tipo_mao_obra=etapa.tipo_mao_obra,
                ordem=etapa.ordem,
            )
            self._db.add(re)

        await self._db.flush()
        await self._db.refresh(receita)
        return await self.buscar_por_id(receita.id, tenant_id)  # type: ignore[return-value]

    async def buscar_por_id(self, receita_id: UUID, tenant_id: UUID) -> Receita | None:
        result = await self._db.execute(
            select(Receita)
            .options(
                selectinload(Receita.ingredientes).selectinload(ReceitaIngrediente.ingrediente),
                selectinload(Receita.etapas),
            )
            .where(
                Receita.id == receita_id,
                Receita.tenant_id == tenant_id,
                Receita.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def listar(self, tenant_id: UUID) -> list[Receita]:
        result = await self._db.execute(
            select(Receita)
            .options(
                selectinload(Receita.ingredientes).selectinload(ReceitaIngrediente.ingrediente),
                selectinload(Receita.etapas),
            )
            .where(Receita.tenant_id == tenant_id, Receita.deleted_at.is_(None))
            .order_by(Receita.nome)
        )
        return list(result.scalars().all())

    async def atualizar(
        self,
        receita: Receita,
        campos_simples: dict,
        ingredientes: list | None,
        etapas: list | None,
    ) -> Receita:
        """
        Atualiza campos da receita. Se ingredientes/etapas forem passados,
        substitui as listas inteiras (estratégia mais simples e previsível
        que tentar diff). Se forem None, mantém as existentes.
        """
        for campo, valor in campos_simples.items():
            if valor is not None:
                setattr(receita, campo, valor)

        if ingredientes is not None:
            # remove os atuais (cascade configurado no model) e adiciona os novos
            for ri in list(receita.ingredientes):
                await self._db.delete(ri)
            await self._db.flush()
            for item in ingredientes:
                self._db.add(
                    ReceitaIngrediente(
                        receita_id=receita.id,
                        ingrediente_id=item.ingrediente_id,
                        quantidade=item.quantidade,
                        unidade=item.unidade,
                    )
                )

        if etapas is not None:
            for et in list(receita.etapas):
                await self._db.delete(et)
            await self._db.flush()
            for et in etapas:
                self._db.add(
                    ReceitaEtapa(
                        receita_id=receita.id,
                        nome=et.nome,
                        duracao_minutos=et.duracao_minutos,
                        tipo_mao_obra=et.tipo_mao_obra,
                        ordem=et.ordem,
                    )
                )

        await self._db.flush()
        return receita

    async def deletar(self, receita: Receita) -> None:
        from datetime import datetime

        receita.deleted_at = datetime.utcnow()
        await self._db.flush()

    async def buscar_ingrediente(self, ingrediente_id: UUID, tenant_id: UUID) -> Ingrediente | None:
        result = await self._db.execute(
            select(Ingrediente).where(
                Ingrediente.id == ingrediente_id,
                Ingrediente.tenant_id == tenant_id,
                Ingrediente.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
