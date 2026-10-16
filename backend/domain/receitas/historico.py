"""Durable recipe versions, written in the same transaction as the edit."""

from copy import deepcopy
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from domain.exceptions import NotFoundError
from infrastructure.database.models import Receita, ReceitaIngrediente, ReceitaVersao


class HistoricoReceita:
    """Keep saved content rather than recomputing historical costs or recipes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def receita(self, receita_id: UUID, tenant_id: UUID) -> Receita:
        result = await self.db.execute(
            select(Receita)
            .where(Receita.id == receita_id, Receita.tenant_id == tenant_id,
                   Receita.deleted_at.is_(None))
            .options(joinedload(Receita.ingredientes).joinedload(ReceitaIngrediente.ingrediente),
                     joinedload(Receita.etapas))
            .execution_options(populate_existing=True)
        )
        row = result.unique().scalar_one_or_none()
        if row is None:
            raise NotFoundError("Receita")
        return row

    @staticmethod
    def documento(row: Receita) -> dict:
        """Freeze editable values, decimals and source text without rounding."""
        return {
            "nome": row.nome, "categoria": row.categoria,
            "rendimento": str(row.rendimento), "rendimento_unidade": row.rendimento_unidade,
            "margem_desejada": str(row.margem_desejada),
            "preco_de_venda_real": (
                str(row.preco_de_venda_real) if row.preco_de_venda_real is not None else None
            ),
            "modo_preparo": row.modo_preparo, "foto_url": row.foto_url,
            "ficha_tecnica": deepcopy(row.ficha_tecnica), "ficha_revisao": row.ficha_revisao,
            "ingredientes": [
                {"ingrediente_id": str(item.ingrediente_id),
                 "nome": item.ingrediente.nome if item.ingrediente and
                         item.ingrediente.tenant_id == row.tenant_id else "Indisponível",
                 "quantidade": str(item.quantidade), "unidade": item.unidade}
                for item in sorted(row.ingredientes, key=lambda item: (item.created_at, str(item.id)))
                if not item.deleted_at
            ],
            "etapas": [
                {"nome": step.nome, "duracao_minutos": step.duracao_minutos,
                 "tipo_mao_obra": step.tipo_mao_obra, "ordem": step.ordem}
                for step in sorted(row.etapas, key=lambda step: (step.ordem, str(step.id)))
                if not step.deleted_at
            ],
        }

    async def inicial(self, receita_id: UUID, tenant_id: UUID,
                      usuario_id: UUID | None = None, origem: str = "criacao") -> None:
        """Existing records receive a truthful baseline before their first edit."""
        row = await self.receita(receita_id, tenant_id)
        existing = await self.db.scalar(select(ReceitaVersao.id).where(
            ReceitaVersao.tenant_id == tenant_id, ReceitaVersao.receita_id == receita_id,
            ReceitaVersao.versao == row.versao,
        ))
        if existing is None:
            self.db.add(ReceitaVersao(tenant_id=tenant_id, receita_id=receita_id,
                                     versao=row.versao, usuario_id=usuario_id, origem=origem,
                                     snapshot=self.documento(row)))
            await self.db.flush()

    async def registrar(self, receita_id: UUID, tenant_id: UUID,
                        usuario_id: UUID | None, origem: str) -> None:
        """Caller holds the tenant composition lock for baseline and mutation."""
        row = await self.receita(receita_id, tenant_id)
        row.versao += 1
        self.db.add(ReceitaVersao(tenant_id=tenant_id, receita_id=receita_id,
                                 versao=row.versao, usuario_id=usuario_id, origem=origem,
                                 snapshot=self.documento(row)))
        await self.db.flush()
