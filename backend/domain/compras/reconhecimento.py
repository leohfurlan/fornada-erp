"""Reconhecimento conservador: vínculo confirmado antes de similaridade textual."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from domain.compras.comercial import ComprasComerciais
from domain.compras.comercial_schemas import (
    Candidato,
    FornecedorResponse,
    ItemLido,
    ItemObservado,
    LeituraCompra,
    ReconhecerResponse,
)
from domain.compras.extraction import ReceiptExtractor
from domain.compras.identificadores import (
    normalizar_descricao,
    validar_cnpj,
    validar_evidencia,
    validar_gtin,
    variante_texto,
)
from domain.compras.matching import IngredienteRef, sugerir_match
from domain.exceptions import ValidationError


def data_lida(value: str | None) -> date | None:
    """Conserva ausência e texto ilegível sem usar a data do scan."""
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def decimal_lido(value: object) -> Decimal | None:
    """Aceita somente números finitos extraídos, preservando ausências."""
    if value is None:
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (ValueError, ArithmeticError):
        return None


class ReconhecimentoCompras:
    """Não grava catálogo ou estoque durante a leitura."""

    def __init__(self, compras: ComprasComerciais, ocr: ReceiptExtractor) -> None:
        self.compras, self.ocr = compras, ocr
        self.repo = compras.repo

    async def reconhecer(
        self, tenant: UUID, fornecedor: UUID | None, observados: list[ItemObservado]
    ) -> ReconhecerResponse:
        if fornecedor:
            await self.repo.fornecedor(tenant, fornecedor)
        materiais = {m.id: m for m in await self.compras.estoque.listar(tenant)}
        produtos = {
            p.id: p
            for p in await self.repo.produtos(tenant)
            if p.aprovado and p.ingrediente_id in materiais
        }
        aliases = await self.repo.aliases(tenant)
        items: list[ItemLido] = []
        for observed in observados:
            item = ItemLido(**observed.model_dump())
            if item.quantidade is None or item.quantidade <= 0 or not item.unidade:
                item.pendencias.append("Confira a quantidade e a unidade lidas.")
            if item.preco_unitario is None or item.preco_total is None:
                item.pendencias.append("Confira os valores do item.")
            found: list[tuple[UUID, str, object | None]] = []
            if observed.gtin and observed.gtin_confirmado:
                found.extend(
                    (p.id, "gtin_confirmado", None)
                    for p in produtos.values()
                    if p.gtin == observed.gtin
                )
            for alias in aliases:
                if alias.fornecedor_id != fornecedor or alias.produto_id not in produtos:
                    continue
                produto = produtos[alias.produto_id]
                chave = (
                    (observed.codigo_loja or "").casefold().strip()
                    if alias.tipo == "codigo_loja"
                    else normalizar_descricao(observed.descricao)
                )
                if alias.valor_normalizado != chave:
                    continue
                if alias.produto_revisao_confirmada != produto.revisao:
                    item.pendencias.append("O produto foi alterado. Confirme o vínculo novamente.")
                    item.vinculo_id, item.vinculo_revisao = alias.id, alias.revisao
                    continue
                found.append((produto.id, alias.tipo, alias))
            ids = list(dict.fromkeys(id for id, _, _ in found))
            conflict = len(ids) > 1
            for id in ids:
                produto = produtos[id]
                try:
                    validar_evidencia(
                        observed.descricao,
                        produto.variante or produto.nome,
                        produto.conteudo_embalagem,
                        produto.unidade_conteudo,
                    )
                    if observed.variante_observada:
                        validar_evidencia(
                            observed.variante_observada,
                            produto.variante or produto.nome,
                            produto.conteudo_embalagem,
                            produto.unidade_conteudo,
                        )
                    if observed.conteudo_observado and observed.unidade_conteudo_observada:
                        validar_evidencia(
                            f"{observed.conteudo_observado} {observed.unidade_conteudo_observada}",
                            produto.variante or produto.nome,
                            produto.conteudo_embalagem,
                            produto.unidade_conteudo,
                        )
                except ValidationError as exc:
                    conflict = True
                    item.pendencias.append(exc.message)
                item.candidatos.append(
                    Candidato(
                        produto_id=id,
                        produto_revisao=produto.revisao,
                        ingrediente_id=produto.ingrediente_id,
                        nome_produto=produto.nome,
                        nome_material=materiais[produto.ingrediente_id].nome,
                    )
                )
            if ids and not conflict:
                produto = produtos[ids[0]]
                _, method, alias = found[0]
                material = materiais[produto.ingrediente_id]
                item.ingrediente_id, item.nome_match = material.id, material.nome
                item.produto_id, item.produto_revisao = produto.id, produto.revisao
                item.reconhecimento, item.score = method, 1
                item.tipo_sugerido, item.unidade_sugerida = material.tipo, material.unidade
                item.explicacao = (
                    "Identificador universal que você confirmou."
                    if method == "gtin_confirmado"
                    else "Produto que você já confirmou nesta loja."
                )
                if alias:
                    item.vinculo_id, item.vinculo_revisao = alias.id, alias.revisao
                if not fornecedor or fornecedor not in await self.repo.aprovados(
                    tenant, produto.id
                ):
                    item.pendencias.append("Confira a aprovação desta loja para o produto.")
            elif conflict:
                item.reconhecimento = "conflito"
                item.explicacao = "Há informações conflitantes. Escolha e confira o produto."
            else:
                variante = variante_texto(observed.variante_observada or observed.descricao)
                refs = [
                    IngredienteRef(id=str(m.id), nome=m.nome, unidade=m.unidade, tipo=m.tipo)
                    for m in materiais.values()
                    if not variante_texto(m.nome) or variante_texto(m.nome) == variante
                ]
                suggested = sugerir_match(observed.descricao, observed.unidade or "", refs)
                item.score = suggested.score
                item.tipo_sugerido, item.unidade_sugerida = (
                    suggested.tipo_sugerido,
                    suggested.unidade_sugerida,
                )
                if suggested.ingrediente_id:
                    # Empate não seleciona pela ordem dos materiais.
                    from domain.compras.matching import score_similaridade

                    ties = [
                        r
                        for r in refs
                        if score_similaridade(observed.descricao, r.nome) == suggested.score
                    ]
                    if len(ties) == 1:
                        item.ingrediente_id = UUID(suggested.ingrediente_id)
                        item.nome_match = suggested.nome_match
                        item.reconhecimento = "similaridade"
                        item.explicacao = "Sugestão pelo nome. Confira o produto e a embalagem."
            items.append(item)
        return ReconhecerResponse(itens=items)

    async def ler(
        self, tenant: UUID, image: bytes, mime: str, fornecedor: UUID | None = None
    ) -> LeituraCompra:
        """Expõe valores originais e contexto da nota sem presumir variante."""
        result = await self.ocr.processar_imagem(image, mime)
        suppliers = await self.repo.fornecedores(tenant)
        cnpj = getattr(result, "cnpj", None)
        try:
            confirmed_cnpj = validar_cnpj(cnpj)
        except ValueError:
            confirmed_cnpj = None
        if fornecedor:
            await self.repo.fornecedor(tenant, fornecedor)
        elif confirmed_cnpj:
            fornecedor = next((f.id for f in suppliers if f.cnpj == confirmed_cnpj), None)
        candidates = [
            FornecedorResponse.model_validate(f, from_attributes=True)
            for f in suppliers
            if (confirmed_cnpj and f.cnpj == confirmed_cnpj)
            or (
                result.estabelecimento
                and normalizar_descricao(f.nome) == normalizar_descricao(result.estabelecimento)
            )
        ]
        observations = []
        for idx, original in enumerate(result.itens):
            missing = getattr(original, "campos_pendentes", [])
            gtin = getattr(original, "gtin", None)
            try:
                gtin = validar_gtin(gtin)
            except ValueError:
                gtin = None
            observations.append(
                ItemObservado(
                    indice=idx,
                    descricao=original.descricao,
                    quantidade=None
                    if "quantidade" in missing
                    else decimal_lido(original.quantidade),
                    unidade=None if "unidade" in missing else original.unidade,
                    preco_unitario=None
                    if "preco_unitario" in missing
                    else decimal_lido(original.preco_unitario),
                    preco_total=None
                    if "preco_total" in missing
                    else decimal_lido(original.preco_total),
                    desconto_item=decimal_lido(getattr(original, "desconto_item", None)),
                    marca_observada=getattr(original, "marca", None),
                    fabricante_observado=getattr(original, "fabricante", None),
                    variante_observada=getattr(original, "variante", None),
                    conteudo_observado=decimal_lido(getattr(original, "conteudo_embalagem", None)),
                    unidade_conteudo_observada=getattr(original, "unidade_conteudo", None),
                    codigo_loja=getattr(original, "codigo_loja", None),
                    gtin=gtin,
                )
            )
        if not observations or len(observations) > 100:
            raise ValidationError("Não conseguimos revisar os itens. Envie outra foto.")
        recognized = await self.reconhecer(tenant, fornecedor, observations)
        return LeituraCompra(
            itens=recognized.itens,
            total_nota=decimal_lido(result.total),
            estabelecimento=result.estabelecimento,
            data_compra=data_lida(result.data),
            data_original=result.data,
            fornecedor_id=fornecedor,
            fornecedores_candidatos=candidates,
            cnpj_observado=cnpj,
            identidade_nota=getattr(result, "identidade_nota", None),
            fonte=result.fonte,
            confianca=result.confianca,
            avisos=getattr(result, "avisos", []),
            aviso_mock=result.fonte == "mock",
        )
