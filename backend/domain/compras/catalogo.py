"""Cadastro comercial independente de saldos e receitas."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from domain.compras.comercial_schemas import (
    FornecedorCriar,
    FornecedorEditar,
    FornecedorResponse,
    PaginaFornecedores,
    PaginaProdutos,
    ProdutoCriar,
    ProdutoDados,
    ProdutoEditar,
    ProdutoResponse,
    VinculoEditar,
    VinculoResponse,
)
from domain.compras.repository import ComprasRepository
from domain.estoque.service import EstoqueService
from domain.estoque.unidades import converter_para_principal
from domain.exceptions import ConflictError, ValidationError
from infrastructure.database.compras_models import FornecedorCompra, ProdutoCompra


class CatalogoCompras:
    """Valida referências próprias e revisões antes de qualquer alteração comercial."""

    def __init__(self, repo: ComprasRepository, estoque: EstoqueService) -> None:
        self.repo, self.estoque = repo, estoque

    async def validar_produto(self, tenant: UUID, data: ProdutoDados, ingrediente: UUID) -> None:
        material = await self.estoque.buscar(ingrediente, tenant)
        self.fator(data, material.unidade, [u.model_dump() for u in material.unidades_alternativas])

    @staticmethod
    def fator(
        data: ProdutoDados | ProdutoCompra, principal: str, alternativas: list[dict]
    ) -> Decimal:
        """Resolve conteúdo por produto sem sobrescrever equivalência métrica exata."""
        try:
            exato = converter_para_principal(
                Decimal("1"), data.unidade_conteudo, principal, alternativas
            )
        except ValidationError:
            if data.fator_para_principal is None:
                raise ValidationError(
                    "Informe a conversão do conteúdo para a unidade do material."
                ) from None
            return data.fator_para_principal
        if data.fator_para_principal is not None and data.fator_para_principal != exato:
            raise ValidationError("A conversão informada difere da equivalência já confirmada.")
        return exato

    async def produto_response(self, tenant: UUID, row: ProdutoCompra) -> ProdutoResponse:
        return ProdutoResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            ingrediente_id=row.ingrediente_id,
            nome=row.nome,
            marca=row.marca,
            fabricante=row.fabricante,
            variante=row.variante,
            conteudo_embalagem=row.conteudo_embalagem,
            unidade_conteudo=row.unidade_conteudo,
            fator_para_principal=row.fator_para_principal,
            gtin=row.gtin,
            aprovado=row.aprovado,
            revisao=row.revisao,
            created_at=row.created_at,
            updated_at=row.updated_at,
            fornecedores_aprovados=await self.repo.aprovados(tenant, row.id),
        )

    async def listar_produtos(
        self, tenant: UUID, ingrediente: UUID | None, aprovado: bool | None, limit: int, offset: int
    ) -> PaginaProdutos:
        if ingrediente:
            await self.estoque.buscar(ingrediente, tenant)
        rows = [
            p
            for p in await self.repo.produtos(tenant)
            if (ingrediente is None or p.ingrediente_id == ingrediente)
            and (aprovado is None or p.aprovado == aprovado)
        ]
        return PaginaProdutos(
            itens=[await self.produto_response(tenant, p) for p in rows[offset : offset + limit]],
            total=len(rows),
        )

    async def criar_produto(self, tenant: UUID, data: ProdutoCriar) -> ProdutoCompra:
        await self.repo.travar(tenant)
        await self.validar_produto(tenant, data, data.ingrediente_id)
        if data.gtin and any(p.gtin == data.gtin for p in await self.repo.produtos(tenant)):
            raise ConflictError("Este GTIN já está associado a outro produto.")
        for id in data.fornecedores_aprovados:
            await self.repo.fornecedor(tenant, id)
        row = ProdutoCompra(tenant_id=tenant, **data.model_dump(exclude={"fornecedores_aprovados"}))
        self.repo.db.add(row)
        await self.repo.db.flush()
        await self.repo.aprovar(tenant, row.id, data.fornecedores_aprovados)
        return row

    async def editar_produto(self, tenant: UUID, id: UUID, data: ProdutoEditar) -> ProdutoCompra:
        await self.repo.travar(tenant)
        row = await self.repo.produto(tenant, id)
        if row.revisao != data.revisao:
            raise ConflictError("O produto foi alterado. Atualize antes de salvar.")
        changes = data.model_dump(exclude_unset=True, exclude={"revisao", "fornecedores_aprovados"})
        merged = ProdutoDados.model_validate(
            {field: changes.get(field, getattr(row, field)) for field in ProdutoDados.model_fields}
        )
        await self.validar_produto(tenant, merged, row.ingrediente_id)
        if merged.gtin and any(
            p.gtin == merged.gtin and p.id != id for p in await self.repo.produtos(tenant)
        ):
            raise ConflictError("Este GTIN já está associado a outro produto.")
        if data.fornecedores_aprovados is not None:
            await self.repo.aprovar(tenant, id, data.fornecedores_aprovados)
        for field, value in merged.model_dump().items():
            setattr(row, field, value)
        if "aprovado" in changes:
            if changes["aprovado"] is None:
                raise ValidationError("Informe a aprovação do produto.")
            row.aprovado = changes["aprovado"]
        row.revisao += 1
        await self.repo.db.flush()
        return row

    async def apagar_produto(self, tenant: UUID, id: UUID, revisao: int) -> None:
        await self.repo.travar(tenant)
        row = await self.repo.produto(tenant, id)
        if row.revisao != revisao:
            raise ConflictError("O produto foi alterado. Atualize antes de remover.")
        row.deleted_at = datetime.now(UTC)
        await self.repo.db.flush()

    async def listar_fornecedores(
        self, tenant: UUID, q: str | None, limit: int, offset: int
    ) -> PaginaFornecedores:
        rows = [
            f
            for f in await self.repo.fornecedores(tenant)
            if not q or q.casefold() in f.nome.casefold()
        ]
        return PaginaFornecedores(
            itens=[
                FornecedorResponse.model_validate(f, from_attributes=True)
                for f in rows[offset : offset + limit]
            ],
            total=len(rows),
        )

    async def criar_fornecedor(self, tenant: UUID, data: FornecedorCriar) -> FornecedorCompra:
        await self.repo.travar(tenant)
        if data.cnpj and any(f.cnpj == data.cnpj for f in await self.repo.fornecedores(tenant)):
            raise ConflictError(
                "Já existe um fornecedor com este CNPJ. Selecione o cadastro existente."
            )
        row = FornecedorCompra(tenant_id=tenant, **data.model_dump())
        self.repo.db.add(row)
        await self.repo.db.flush()
        return row

    async def editar_fornecedor(
        self, tenant: UUID, id: UUID, data: FornecedorEditar
    ) -> FornecedorCompra:
        await self.repo.travar(tenant)
        row = await self.repo.fornecedor(tenant, id)
        if row.revisao != data.revisao:
            raise ConflictError("O fornecedor foi alterado. Atualize antes de salvar.")
        if data.cnpj and any(
            f.cnpj == data.cnpj and f.id != id for f in await self.repo.fornecedores(tenant)
        ):
            raise ConflictError("Já existe um fornecedor com este CNPJ.")
        for field, value in data.model_dump(exclude_unset=True, exclude={"revisao"}).items():
            if field == "nome" and value is None:
                raise ValidationError("Informe o nome do fornecedor.")
            setattr(row, field, value)
        row.revisao += 1
        await self.repo.db.flush()
        return row

    async def apagar_fornecedor(self, tenant: UUID, id: UUID, revisao: int) -> None:
        await self.repo.travar(tenant)
        row = await self.repo.fornecedor(tenant, id)
        if row.revisao != revisao:
            raise ConflictError("O fornecedor foi alterado. Atualize antes de remover.")
        row.deleted_at = datetime.now(UTC)
        await self.repo.db.flush()

    async def editar_vinculo(self, tenant: UUID, id: UUID, data: VinculoEditar) -> VinculoResponse:
        await self.repo.travar(tenant)
        row = await self.repo.alias(tenant, id)
        product = await self.repo.produto(tenant, data.produto_id)
        await self.repo.fornecedor(tenant, row.fornecedor_id)
        await self.estoque.buscar(product.ingrediente_id, tenant)
        if row.revisao != data.revisao or product.revisao != data.produto_revisao:
            raise ConflictError("Vínculo ou produto alterado. Atualize antes de corrigir.")
        if not product.aprovado:
            raise ValidationError("Aprove o produto antes de guardar o vínculo.")
        row.produto_id, row.produto_revisao_confirmada = product.id, product.revisao
        row.revisao += 1
        await self.repo.db.flush()
        return VinculoResponse(
            **{
                field: getattr(row, field)
                for field in VinculoResponse.model_fields
                if field != "ativo"
            },
            ativo=True,
        )

    async def apagar_vinculo(self, tenant: UUID, id: UUID, revisao: int) -> None:
        await self.repo.travar(tenant)
        row = await self.repo.alias(tenant, id)
        if row.revisao != revisao:
            raise ConflictError("O vínculo foi alterado. Atualize antes de remover.")
        row.deleted_at = datetime.now(UTC)
        await self.repo.db.flush()
