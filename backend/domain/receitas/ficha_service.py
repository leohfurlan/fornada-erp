from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import ConflictError, NotFoundError, ValidationError
from domain.receitas.repository import ReceitaRepository
from domain.receitas.composicao import converter_quantidade
from domain.estoque.unidades import converter_para_principal
from domain.receitas.ficha_tecnica import FichaTecnicaInput, FichaTecnicaResponse
from infrastructure.database.models import Receita, Tenant

logger = structlog.get_logger(__name__)


class FichaTecnicaService:
    """Ficha editorial de montagem, com isolamento e revisão otimista."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def buscar(self, receita_id: UUID, tenant_id: UUID) -> FichaTecnicaResponse:
        """Retorna ficha ou estrutura vazia para uma receita existente."""
        result = await self._db.execute(select(Receita.ficha_tecnica, Receita.ficha_revisao).where(
            Receita.id == receita_id, Receita.tenant_id == tenant_id,
            Receita.deleted_at.is_(None),
        ))
        row = result.first()
        if row is None:
            raise NotFoundError("Receita")
        return FichaTecnicaResponse(**(row.ficha_tecnica or {}), revisao=row.ficha_revisao)

    async def salvar(
        self, receita_id: UUID, tenant_id: UUID, data: FichaTecnicaInput,
    ) -> FichaTecnicaResponse:
        """Grava revisão apenas se ainda corresponder à versão recebida."""
        # Serializa alterações no grafo do tenant para impedir ciclos concorrentes.
        await self._db.execute(select(Tenant.id).where(Tenant.id == tenant_id).with_for_update())
        await self.buscar(receita_id, tenant_id)
        repo = ReceitaRepository(self._db)
        if data.composicao_ativa:
            visitados: set[UUID] = set()
            async def validar_base(base_id: UUID, caminho: set[UUID]) -> None:
                if base_id in caminho or len(caminho) >= 20:
                    raise ValidationError("A composição contém um ciclo ou mais de 20 níveis")
                if base_id in visitados:
                    return
                base = await repo.buscar_por_id(base_id, tenant_id)
                if not base:
                    raise ValidationError("Receita-base não encontrada nesta loja")
                if base.rendimento <= 0:
                    raise ValidationError("Informe um rendimento positivo para a receita-base")
                ficha = base.ficha_tecnica or {}
                if ficha.get("composicao_ativa"):
                    for item in ficha.get("passos", []):
                        if item.get("receita_base_id"):
                            await validar_base(UUID(item["receita_base_id"]), caminho | {base_id})
                visitados.add(base_id)
            for passo in data.passos:
                if passo.receita_base_id:
                    await validar_base(passo.receita_base_id, {receita_id})
                    base = await repo.buscar_por_id(passo.receita_base_id, tenant_id)
                    converter_quantidade(passo.quantidade, passo.unidade, base.rendimento_unidade)
                else:
                    material = await repo.buscar_ingrediente(passo.ingrediente_id, tenant_id)
                    if not material:
                        raise ValidationError("Material não encontrado nesta loja")
                    converter_para_principal(passo.quantidade, passo.unidade, material.unidade, material.unidades_alternativas)
                    if (passo.tipo == "embalagem") != (material.tipo == "embalagem"):
                        raise ValidationError("O tipo da etapa deve corresponder ao cadastro da embalagem")
        documento = data.model_dump(mode="json", exclude={"revisao"})
        result = await self._db.execute(update(Receita).where(
            Receita.id == receita_id, Receita.tenant_id == tenant_id,
            Receita.deleted_at.is_(None), Receita.ficha_revisao == data.revisao,
        ).values(ficha_tecnica=documento, ficha_revisao=Receita.ficha_revisao + 1)
          .returning(Receita.ficha_revisao))
        revisao = result.scalar_one_or_none()
        if revisao is None:
            raise ConflictError("Esta ficha foi alterada. Recarregue antes de salvar novamente.")
        logger.info("ficha_tecnica_salva", tenant_id=str(tenant_id), entity="receita",
                    entity_id=str(receita_id), action="update", revisao=revisao)
        return FichaTecnicaResponse(**documento, revisao=revisao)
