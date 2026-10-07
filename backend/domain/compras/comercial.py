"""Confirmação atômica, conversão por embalagem e histórico comercial."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import structlog
from sqlalchemy import select

from domain.compras.catalogo import CatalogoCompras
from domain.compras.comercial_schemas import (
    CompraDetalhada,
    CompraItemResponse,
    CompraResumo,
    CompraRevisada,
    Duplicidade,
    ItemPrevia,
    ItemRevisado,
    PaginaCompras,
    PreviaCompra,
    ProdutoCriar,
    ResultadoCompra,
)
from domain.compras.identificadores import normalizar_descricao, validar_evidencia
from domain.compras.repository import ComprasRepository
from domain.estoque.schemas import (
    CriarIngredienteRequest,
    EntradaEstoqueRequest,
    IngredienteResponse,
)
from domain.estoque.service import EstoqueService
from domain.estoque.unidades import converter_para_principal
from domain.exceptions import ConflictError, NotFoundError, ValidationError
from infrastructure.database.compras_models import (
    AliasCompra,
    Compra,
    CompraItem,
    FornecedorCompra,
    ProdutoCompra,
)
from infrastructure.database.models import Ingrediente

logger = structlog.get_logger(__name__)
PRECISAO = Decimal("0.00000001")
LIMITE_ESTOQUE = Decimal("99999999.9999")
EMBALAGENS = {"un", "cx", "pct", "fardo"}


@dataclass
class Resolvido:
    item: ItemRevisado
    material: IngredienteResponse | None
    produto: ProdutoCompra | None
    previa: ItemPrevia


def fingerprint(data: CompraRevisada, usuario: UUID | None, origem: str, legado: bool) -> str:
    """Representação canônica impede retries com o mesmo ID e conteúdo diferente."""

    def encode(value: object) -> str:
        if isinstance(value, Decimal):
            texto = format(value, "f")
            return texto.rstrip("0").rstrip(".") if "." in texto else texto
        return str(value)

    value = {"compra": data.model_dump(), "usuario": usuario, "origem": origem, "legado": legado}
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=encode, ensure_ascii=False).encode()
    ).hexdigest()


class ComprasComerciais:
    """Mantém catálogo, aprendizados, histórico e estoque na mesma transação."""

    def __init__(self, repo: ComprasRepository, estoque: EstoqueService) -> None:
        self.repo, self.estoque = repo, estoque
        self.catalogo = CatalogoCompras(repo, estoque)

    async def resolver(
        self, tenant: UUID, data: CompraRevisada
    ) -> tuple[FornecedorCompra | None, list[Resolvido], list[Duplicidade]]:
        hoje = datetime.now(UTC).astimezone(timezone(timedelta(hours=-3))).date()
        if data.data_compra and data.data_compra > hoje:
            raise ValidationError("A data da compra está no futuro. Confira a nota.")
        fornecedor = (
            await self.repo.fornecedor(tenant, data.fornecedor_id) if data.fornecedor_id else None
        )
        if data.fornecedor_novo and data.fornecedor_novo.cnpj:
            if any(
                f.cnpj == data.fornecedor_novo.cnpj for f in await self.repo.fornecedores(tenant)
            ):
                raise ConflictError(
                    "Esta loja já está cadastrada. Selecione o fornecedor existente."
                )
        rows: list[Resolvido] = []
        acumulado: dict[UUID, Decimal] = {}
        for idx, item in enumerate(data.itens):
            material = (
                await self.estoque.buscar(item.ingrediente_id, tenant)
                if item.ingrediente_id
                else None
            )
            principal = (
                material.unidade if material else (item.unidade_principal or item.unidade).lower()
            )
            alternativas = (
                [u.model_dump() for u in material.unidades_alternativas] if material else []
            )
            produto = await self.repo.produto(tenant, item.produto_id) if item.produto_id else None
            comercial = produto or item.produto_novo
            if produto and (produto.revisao != item.produto_revisao):
                raise ConflictError("O produto mudou desde a leitura. Atualize a seleção.")
            if produto and produto.ingrediente_id != item.ingrediente_id:
                raise ValidationError("O produto pertence a outro material. Confira a seleção.")
            if comercial:
                fator_conteudo = self.catalogo.fator(comercial, principal, alternativas)
                validar_evidencia(
                    item.descricao_original,
                    comercial.variante or comercial.nome,
                    comercial.conteudo_embalagem,
                    comercial.unidade_conteudo,
                )
                if (
                    item.gtin_confirmado
                    and comercial.gtin
                    and item.gtin_confirmado != comercial.gtin
                ):
                    raise ValidationError("O GTIN informado difere do produto selecionado.")
                if item.gtin_confirmado or comercial.gtin:
                    gtin = item.gtin_confirmado or comercial.gtin
                    if any(
                        p.gtin == gtin and (not produto or p.id != produto.id)
                        for p in await self.repo.produtos(tenant)
                    ):
                        raise ConflictError("O GTIN já pertence a outro produto.")
            unidade = item.unidade.lower().strip()
            if comercial and unidade in EMBALAGENS:
                fator = comercial.conteudo_embalagem * fator_conteudo
            else:
                fator = converter_para_principal(Decimal("1"), unidade, principal, alternativas)
            quantidade = item.quantidade * fator
            if quantidade > LIMITE_ESTOQUE or quantidade != quantidade.quantize(Decimal("0.0001")):
                raise ValidationError("A quantidade convertida não cabe na precisão do estoque.")
            if material:
                acumulado[material.id] = acumulado.get(material.id, Decimal("0")) + quantidade
                if material.estoque_atual + acumulado[material.id] > LIMITE_ESTOQUE:
                    raise ValidationError("A entrada excede o limite do estoque.")
            total = (item.quantidade * item.custo_unitario - item.desconto_item).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if total != item.preco_total:
                raise ValidationError(
                    "Quantidade, preço e desconto não conferem com o total do item."
                )
            custo = item.preco_total / quantidade
            if custo > LIMITE_ESTOQUE:
                raise ValidationError("O custo convertido excede o limite do estoque.")
            pendencias: list[str] = []
            produto_aprovado = bool(produto and produto.aprovado) or item.aprovar_produto
            if not comercial and item.aprovar_produto:
                raise ValidationError("Informe o produto antes de aprová-lo.")
            if not produto_aprovado and not item.aceitar_excecao:
                pendencias.append("Aprove o produto ou confirme apenas esta compra.")
            fornecedor_aprovado = bool(
                produto
                and fornecedor
                and fornecedor.id in await self.repo.aprovados(tenant, produto.id)
            )
            if item.aprovar_fornecedor and not (fornecedor or data.fornecedor_novo):
                raise ValidationError("Escolha ou cadastre a loja antes de aprová-la.")
            if item.aprovar_fornecedor and not comercial:
                raise ValidationError("Informe o produto para aprovar a loja para esse uso.")
            if not fornecedor_aprovado and not item.aprovar_fornecedor and not item.aceitar_excecao:
                pendencias.append("Aprove a loja para este produto ou confirme uma exceção.")
            if item.guardar_vinculo:
                if (
                    not comercial
                    or not produto_aprovado
                    or not (fornecedor or data.fornecedor_novo)
                ):
                    raise ValidationError(
                        "Para lembrar o produto, informe e aprove o produto e a loja."
                    )
                if not fornecedor_aprovado and not item.aprovar_fornecedor:
                    raise ValidationError("Aprove a loja antes de guardar o vínculo.")
                if fornecedor and produto:
                    await self.validar_vinculos(tenant, fornecedor.id, produto, item)
            rows.append(
                Resolvido(
                    item,
                    material,
                    produto,
                    ItemPrevia(
                        indice=idx,
                        ingrediente_id=item.ingrediente_id,
                        nome_material=material.nome if material else item.nome,
                        produto_id=item.produto_id,
                        quantidade_principal=quantidade,
                        unidade_principal=principal,
                        fator_aplicado=fator,
                        custo_normalizado=custo.quantize(PRECISAO, rounding=ROUND_HALF_UP),
                        preco_total=item.preco_total,
                        pendencias=pendencias,
                    ),
                )
            )
        duplicadas = await self.repo.duplicadas(
            tenant, data.identidade_nota if data.identidade_confirmada else None
        )
        return (
            fornecedor,
            rows,
            [Duplicidade(compra_id=c.id, data_registro=c.created_at) for c in duplicadas],
        )

    async def prever(self, tenant: UUID, data: CompraRevisada) -> PreviaCompra:
        _, rows, duplicates = await self.resolver(tenant, data)
        return PreviaCompra(
            itens=[r.previa for r in rows],
            total_selecionado=sum((r.item.preco_total for r in rows), Decimal("0")),
            duplicidade=duplicates,
            pode_confirmar=not any(r.previa.pendencias for r in rows)
            and (not duplicates or data.confirmar_duplicidade),
        )

    @staticmethod
    def chaves(item: ItemRevisado) -> list[tuple[str, str, str]]:
        keys = [
            (
                "descricao_loja",
                item.descricao_original,
                normalizar_descricao(item.descricao_original),
            )
        ]
        if item.codigo_loja:
            keys.append(("codigo_loja", item.codigo_loja, item.codigo_loja.strip().casefold()))
        return keys

    async def validar_vinculos(
        self, tenant: UUID, fornecedor: UUID, produto: ProdutoCompra, item: ItemRevisado
    ) -> None:
        aliases = await self.repo.aliases(tenant)
        if item.conflito_vinculo:
            current = await self.repo.alias(tenant, item.conflito_vinculo.id)
            if (
                current.fornecedor_id != fornecedor
                or current.revisao != item.conflito_vinculo.revisao
            ):
                raise ConflictError("O vínculo foi alterado. Atualize antes de corrigir.")
        for tipo, _, chave in self.chaves(item):
            for alias in aliases:
                if (
                    alias.fornecedor_id == fornecedor
                    and alias.tipo == tipo
                    and alias.valor_normalizado == chave
                ):
                    if alias.produto_id != produto.id and (
                        not item.conflito_vinculo
                        or item.conflito_vinculo.id != alias.id
                        or item.conflito_vinculo.revisao != alias.revisao
                    ):
                        raise ConflictError(
                            "Esta descrição ou código aponta para outro produto. "
                            "Corrija o vínculo explicitamente."
                        )

    async def aprender(
        self, tenant: UUID, fornecedor: UUID, produto: ProdutoCompra, item: ItemRevisado
    ) -> None:
        await self.validar_vinculos(tenant, fornecedor, produto, item)
        aliases = await self.repo.aliases(tenant)
        for tipo, original, chave in self.chaves(item):
            alias = next(
                (
                    a
                    for a in aliases
                    if a.fornecedor_id == fornecedor
                    and a.tipo == tipo
                    and a.valor_normalizado == chave
                ),
                None,
            )
            if alias:
                alias.produto_id = produto.id
                alias.produto_revisao_confirmada = produto.revisao
                alias.revisao += 1
            else:
                self.repo.db.add(
                    AliasCompra(
                        tenant_id=tenant,
                        fornecedor_id=fornecedor,
                        produto_id=produto.id,
                        tipo=tipo,
                        valor_original=original,
                        valor_normalizado=chave,
                        produto_revisao_confirmada=produto.revisao,
                    )
                )
        await self.repo.db.flush()

    async def confirmar(
        self,
        tenant: UUID,
        data: CompraRevisada,
        chave: UUID,
        *,
        usuario: UUID | None = None,
        operador: UUID | None = None,
        origem: str | None = None,
        legado: bool = False,
    ) -> ResultadoCompra:
        """Confirma com savepoint; o chamador é responsável pelo commit externo."""
        source = origem or data.origem
        digest = fingerprint(data, usuario, source, legado)
        async with self.repo.db.begin_nested():
            await self.repo.travar(tenant)
            prior = await self.repo.por_chave(tenant, chave)
            if prior:
                if prior.fingerprint != digest:
                    raise ConflictError(
                        "Esta confirmação já foi usada com outros dados. Revise a compra."
                    )
                return ResultadoCompra.model_validate(prior.resultado)
            fornecedor, rows, duplicates = await self.resolver(tenant, data)
            if duplicates and not data.confirmar_duplicidade:
                raise ConflictError(
                    "Esta nota já foi registrada. Confira o histórico antes de repetir."
                )
            if any(r.previa.pendencias for r in rows):
                raise ValidationError(
                    "Revise as aprovações ou escolha registrar apenas esta compra."
                )
            if data.fornecedor_novo:
                fornecedor = await self.catalogo.criar_fornecedor(tenant, data.fornecedor_novo)
            complete = bool(
                fornecedor
                and data.data_compra
                and not legado
                and all(r.produto or r.item.produto_novo for r in rows)
            )
            compra = Compra(
                tenant_id=tenant,
                chave=chave,
                fingerprint=digest,
                usuario_id=usuario,
                operador_id=operador,
                fornecedor_id=fornecedor.id if fornecedor else None,
                fornecedor_nome_snapshot=fornecedor.nome if fornecedor else None,
                estabelecimento_original=data.estabelecimento,
                data_compra=data.data_compra,
                origem=source,
                identidade_nota=data.identidade_nota if data.identidade_confirmada else None,
                total_nota=data.total_nota,
                total_selecionado=sum((r.item.preco_total for r in rows), Decimal("0")),
                metadados_completos=complete,
            )
            self.repo.db.add(compra)
            await self.repo.db.flush()
            results: list[IngredienteResponse] = []
            criados = 0
            for idx, resolved in enumerate(rows):
                item, previa, produto = resolved.item, resolved.previa, resolved.produto
                if resolved.material:
                    material = resolved.material
                else:
                    material = await self.estoque.criar_ingrediente(
                        tenant,
                        CriarIngredienteRequest(
                            nome=item.nome, tipo=item.tipo, unidade=previa.unidade_principal
                        ),
                    )
                    criados += 1
                if item.produto_novo:
                    produto = await self.catalogo.criar_produto(
                        tenant,
                        ProdutoCriar(
                            **item.produto_novo.model_dump(),
                            ingrediente_id=material.id,
                            aprovado=item.aprovar_produto,
                        ),
                    )
                if produto and item.aprovar_produto and not produto.aprovado:
                    produto.aprovado = True
                    produto.revisao += 1
                if produto and item.gtin_confirmado and not produto.gtin:
                    produto.gtin = item.gtin_confirmado
                    produto.revisao += 1
                await self.repo.db.flush()
                if produto and fornecedor and item.aprovar_fornecedor:
                    aprovados = await self.repo.aprovados(tenant, produto.id)
                    await self.repo.aprovar(tenant, produto.id, [*aprovados, fornecedor.id])
                updated, movimento = await self.estoque.registrar_entrada_com_movimento(
                    tenant,
                    EntradaEstoqueRequest(
                        ingrediente_id=material.id,
                        quantidade=previa.quantidade_principal,
                        custo_unitario=item.preco_total / previa.quantidade_principal,
                        unidade=previa.unidade_principal,
                        origem="compra",
                    ),
                )
                results.append(updated)
                original = None if legado else item.descricao_original
                snapshot = {
                    "nome_material": material.nome,
                    "unidade_principal": previa.unidade_principal,
                    "nome_produto": produto.nome if produto else None,
                    "marca": produto.marca if produto else None,
                    "fabricante": produto.fabricante if produto else None,
                    "variante": produto.variante if produto else None,
                    "revisao_produto": produto.revisao if produto else None,
                    "descricao_original": original,
                    "codigo_loja": item.codigo_loja,
                    "gtin": item.gtin_confirmado or (produto.gtin if produto else None),
                    "quantidade_original": str(item.quantidade) if not legado else None,
                    "unidade_original": item.unidade if not legado else None,
                    "custo_unitario_original": str(item.custo_unitario) if not legado else None,
                    "desconto_item": str(item.desconto_item) if not legado else None,
                    "conteudo_embalagem": str(produto.conteudo_embalagem) if produto else None,
                    "unidade_conteudo": produto.unidade_conteudo if produto else None,
                    "fator_aplicado": str(previa.fator_aplicado),
                    "aprovacao_excepcional": item.aceitar_excecao,
                    "dados_completos": complete,
                }
                self.repo.db.add(
                    CompraItem(
                        tenant_id=tenant,
                        compra_id=compra.id,
                        indice=idx,
                        ingrediente_id=material.id,
                        produto_id=produto.id if produto else None,
                        movimentacao_id=movimento,
                        quantidade_principal=previa.quantidade_principal,
                        custo_normalizado=previa.custo_normalizado,
                        preco_total=item.preco_total,
                        snapshot=snapshot,
                    )
                )
                if item.guardar_vinculo and produto and fornecedor:
                    await self.aprender(tenant, fornecedor.id, produto, item)
            response = ResultadoCompra(
                ingredientes_criados=criados,
                ingredientes_atualizados=len(rows) - criados,
                itens=results,
                compra_id=compra.id,
                data_compra=compra.data_compra,
                fornecedor_id=compra.fornecedor_id,
                data_registro=compra.created_at,
                total_selecionado=compra.total_selecionado,
            )
            compra.resultado = json.loads(response.model_dump_json())
            await self.repo.db.flush()
            logger.info(
                "compra_comercial_confirmada",
                tenant_id=str(tenant),
                user_id=str(usuario),
                action="confirmar",
                entity="compra",
                entity_id=str(compra.id),
                itens=len(rows),
                origem=source,
            )
            return response

    async def resumo(self, tenant: UUID, row: Compra) -> CompraResumo:
        return CompraResumo(
            id=row.id,
            data_compra=row.data_compra,
            data_registro=row.created_at,
            estabelecimento_original=row.estabelecimento_original,
            fornecedor_id=row.fornecedor_id,
            fornecedor_nome_snapshot=row.fornecedor_nome_snapshot,
            origem=row.origem,
            total_selecionado=row.total_selecionado,
            metadados_completos=row.metadados_completos,
            quantidade_itens=len(await self.repo.itens(tenant, row.id)),
        )

    async def detalhe(self, tenant: UUID, id: UUID) -> CompraDetalhada:
        row = await self.repo.compra(tenant, id)
        summary = await self.resumo(tenant, row)
        return CompraDetalhada(
            **summary.model_dump(),
            itens=[
                CompraItemResponse.model_validate(i, from_attributes=True)
                for i in await self.repo.itens(tenant, id)
            ],
        )

    async def historico(
        self,
        tenant: UUID,
        *,
        ingrediente_id: UUID | None,
        produto_id: UUID | None,
        fornecedor_id: UUID | None,
        marca: str | None,
        inicio: date | None,
        fim: date | None,
        limit: int,
        offset: int,
    ) -> PaginaCompras:
        if inicio and fim and inicio > fim:
            raise ValidationError("A data inicial deve ser anterior à data final.")
        for model, id in (
            (Ingrediente, ingrediente_id),
            (ProdutoCompra, produto_id),
            (FornecedorCompra, fornecedor_id),
        ):
            if id and not await self.repo.db.scalar(
                select(model.id).where(model.tenant_id == tenant, model.id == id)
            ):
                raise NotFoundError("Filtro")
        rows, count = await self.repo.historico(
            tenant,
            ingrediente_id=ingrediente_id,
            produto_id=produto_id,
            fornecedor_id=fornecedor_id,
            marca=marca,
            inicio=inicio,
            fim=fim,
            limit=limit,
            offset=offset,
        )
        return PaginaCompras(itens=[await self.resumo(tenant, row) for row in rows], total=count)
