from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import structlog

from domain.exceptions import ConflictError, NotFoundError
from domain.estoque.repository import EstoqueRepository
from domain.estoque.schemas import (
    AtualizarIngredienteRequest,
    CriarIngredienteRequest,
    EntradaEstoqueRequest,
    IngredienteResponse,
    MovimentacaoResponse,
)
from domain.receitas.calculos import calcular_custo_medio_novo
from infrastructure.database.models import Ingrediente

logger = structlog.get_logger(__name__)


def _status_estoque(ingrediente: Ingrediente) -> str:
    saldo = ingrediente.estoque_atual - ingrediente.quantidade_reservada
    if saldo <= 0:
        return "zerado"
    if ingrediente.estoque_minimo > 0:
        ratio = saldo / ingrediente.estoque_minimo
        if ratio <= Decimal("0.5"):
            return "critico"
        if ratio <= Decimal("1"):
            return "baixo"
    return "ok"


def _to_response(ingrediente: Ingrediente) -> IngredienteResponse:
    saldo = ingrediente.estoque_atual - ingrediente.quantidade_reservada
    return IngredienteResponse(
        id=ingrediente.id,
        tenant_id=ingrediente.tenant_id,
        codigo=ingrediente.codigo,
        tipo=ingrediente.tipo,
        nome=ingrediente.nome,
        unidade=ingrediente.unidade,
        estoque_atual=ingrediente.estoque_atual,
        quantidade_reservada=ingrediente.quantidade_reservada,
        saldo=saldo,
        estoque_minimo=ingrediente.estoque_minimo,
        custo_medio=ingrediente.custo_medio,
        data_custo_atualizado=ingrediente.data_custo_atualizado,
        status_estoque=_status_estoque(ingrediente),
    )


class EstoqueService:
    def __init__(self, repo: EstoqueRepository) -> None:
        self._repo = repo

    async def criar_ingrediente(
        self, tenant_id: UUID, data: CriarIngredienteRequest
    ) -> IngredienteResponse:
        """Cadastra novo ingrediente. Se houver estoque inicial, registra entrada."""
        ingrediente = await self._repo.criar_ingrediente(tenant_id, data)

        if data.estoque_inicial > 0 and data.custo_inicial > 0:
            await self._repo.salvar_movimentacao(
                tenant_id=tenant_id,
                ingrediente_id=ingrediente.id,
                tipo="entrada",
                quantidade=data.estoque_inicial,
                custo_unitario=data.custo_inicial,
                origem="cadastro_inicial",
            )

        logger.info(
            "ingrediente_criado",
            tenant_id=str(tenant_id),
            action="create",
            entity="ingrediente",
            entity_id=str(ingrediente.id),
        )
        return _to_response(ingrediente)

    async def buscar(self, ingrediente_id: UUID, tenant_id: UUID) -> IngredienteResponse:
        ingrediente = await self._repo.buscar_por_id(ingrediente_id, tenant_id)
        if not ingrediente:
            raise NotFoundError("Ingrediente", str(ingrediente_id))
        return _to_response(ingrediente)

    async def listar(self, tenant_id: UUID) -> list[IngredienteResponse]:
        ingredientes = await self._repo.listar(tenant_id)
        return [_to_response(i) for i in ingredientes]

    async def atualizar_ingrediente(
        self,
        ingrediente_id: UUID,
        tenant_id: UUID,
        data: AtualizarIngredienteRequest,
    ) -> IngredienteResponse:
        """Atualiza campos descritivos. Não permite alterar estoque_atual/custo_medio."""
        ingrediente = await self._repo.buscar_por_id(ingrediente_id, tenant_id)
        if not ingrediente:
            raise NotFoundError("Ingrediente", str(ingrediente_id))

        for campo, valor in data.model_dump(exclude_unset=True).items():
            if valor is not None:
                setattr(ingrediente, campo, valor)

        logger.info(
            "ingrediente_atualizado",
            tenant_id=str(tenant_id),
            action="update",
            entity="ingrediente",
            entity_id=str(ingrediente_id),
        )
        return _to_response(ingrediente)

    async def deletar_ingrediente(self, ingrediente_id: UUID, tenant_id: UUID) -> None:
        """Soft delete. Bloqueia se ingrediente está em uso em alguma receita."""
        ingrediente = await self._repo.buscar_por_id(ingrediente_id, tenant_id)
        if not ingrediente:
            raise NotFoundError("Ingrediente", str(ingrediente_id))

        if await self._repo.ingrediente_em_uso(ingrediente_id):
            raise ConflictError(
                "Este ingrediente está sendo usado em uma ou mais receitas. "
                "Remova-o das receitas antes de excluir."
            )

        await self._repo.soft_delete(ingrediente)

        logger.info(
            "ingrediente_deletado",
            tenant_id=str(tenant_id),
            action="delete",
            entity="ingrediente",
            entity_id=str(ingrediente_id),
        )

    async def listar_movimentacoes(
        self,
        ingrediente_id: UUID,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MovimentacaoResponse]:
        """Histórico de movimentações de um ingrediente, mais recente primeiro."""
        ingrediente = await self._repo.buscar_por_id(ingrediente_id, tenant_id)
        if not ingrediente:
            raise NotFoundError("Ingrediente", str(ingrediente_id))

        movs = await self._repo.listar_movimentacoes(ingrediente_id, tenant_id, limit, offset)
        return [MovimentacaoResponse.model_validate(m) for m in movs]

    async def registrar_entrada(
        self, tenant_id: UUID, data: EntradaEstoqueRequest
    ) -> IngredienteResponse:
        """Registra entrada de estoque (compra) e recalcula custo médio."""
        ingrediente = await self._repo.buscar_por_id(data.ingrediente_id, tenant_id)
        if not ingrediente:
            raise NotFoundError("Ingrediente", str(data.ingrediente_id))

        novo_custo_medio = calcular_custo_medio_novo(
            estoque_atual=ingrediente.estoque_atual,
            custo_medio_atual=ingrediente.custo_medio,
            quantidade_nova=data.quantidade,
            preco_novo=data.custo_unitario,
        )

        ingrediente.estoque_atual += data.quantidade
        custo_anterior = ingrediente.custo_medio
        ingrediente.custo_medio = novo_custo_medio
        if novo_custo_medio != custo_anterior:
            ingrediente.data_custo_atualizado = datetime.now(UTC)

        await self._repo.salvar_movimentacao(
            tenant_id=tenant_id,
            ingrediente_id=ingrediente.id,
            tipo="entrada",
            quantidade=data.quantidade,
            custo_unitario=data.custo_unitario,
            origem=data.origem,
        )

        logger.info(
            "entrada_estoque",
            tenant_id=str(tenant_id),
            action="entrada",
            entity="ingrediente",
            entity_id=str(ingrediente.id),
            quantidade=str(data.quantidade),
            novo_custo_medio=str(novo_custo_medio),
        )
        return _to_response(ingrediente)
