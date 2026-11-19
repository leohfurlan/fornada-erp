from decimal import Decimal, ROUND_HALF_UP
from dataclasses import replace
from uuid import UUID

import structlog

from domain.exceptions import NotFoundError, ValidationError, ConflictError
from domain.receitas.calculos import (
    ConfiguracaoCustoCalculo,
    ItemIngredienteCalculo,
    calcular_custo_por_hora_produzida,
    calcular_custo_total,
    calcular_lucro_estimado,
    calcular_lucro_por_minuto,
    calcular_margem_real,
    calcular_preco_recomendado,
    calcular_preco_recomendado_com_taxas,
    minutos_para_horas,
)
from domain.receitas.historico import HistoricoReceita
from domain.receitas.repository import ReceitaRepository
from domain.receitas.composicao import converter_quantidade
from domain.estoque.unidades import converter_para_principal
from domain.receitas.schemas import (
    AtualizarReceitaRequest,
    CriarReceitaRequest,
    CustoDetalhadoResponse,
    IngredienteInput,
    IngredienteReceitaResponse,
    ReceitaResponse,
)
from infrastructure.database.models import ConfiguracaoCusto, Receita, ReceitaIngrediente
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ReceitaService:
    def __init__(self, repo: ReceitaRepository, db: AsyncSession) -> None:
        self._repo = repo
        self._db = db

    async def criar(self, tenant_id: UUID, data: CriarReceitaRequest, usuario_id: UUID | None = None) -> ReceitaResponse:
        """Cria receita e retorna com custo já calculado."""
        await self._validar_ingredientes(tenant_id, data.ingredientes)

        receita = await self._repo.criar(tenant_id, data)
        await HistoricoReceita(self._db).inicial(receita.id, tenant_id, usuario_id)

        logger.info(
            "receita_criada",
            tenant_id=str(tenant_id),
            action="create",
            entity="receita",
            entity_id=str(receita.id),
        )

        return await self._montar_response(receita, tenant_id)

    async def buscar(self, receita_id: UUID, tenant_id: UUID) -> ReceitaResponse:
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        return await self._montar_response(receita, tenant_id)

    async def listar(self, tenant_id: UUID) -> list[ReceitaResponse]:
        receitas = await self._repo.listar(tenant_id)
        return [await self._montar_response(r, tenant_id) for r in receitas]

    async def atualizar(
        self, receita_id: UUID, tenant_id: UUID, data: AtualizarReceitaRequest,
        usuario_id: UUID | None = None,
    ) -> ReceitaResponse:
        """Atualiza receita. Ingredientes/etapas substituem a lista inteira se enviados."""
        await self._repo.travar_composicao(tenant_id)
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        if data.rendimento is not None and data.rendimento <= 0:
            raise ValidationError("Rendimento deve ser maior que zero", field="rendimento")
        if data.rendimento_unidade is not None and data.rendimento_unidade != receita.rendimento_unidade:
            if await self._repo.unidade_rendimento_em_uso(receita_id, tenant_id):
                raise ConflictError("Esta receita-base está em uso. Preserve a unidade de rendimento ou crie outra receita.")

        if data.ingredientes is not None:
            await self._validar_ingredientes(
                tenant_id, data.ingredientes, receita_id=receita_id
            )

        if data.versao is not None and data.versao != receita.versao:
            raise ConflictError("Esta receita foi alterada. Recarregue antes de salvar.")
        historico = HistoricoReceita(self._db)
        await historico.inicial(receita_id, tenant_id, origem="base_anterior")
        campos_atualizaveis = data.model_dump(
            exclude_unset=True,
            exclude={"ingredientes", "etapas", "versao"},
        )
        campos_simples = {
            k: v for k, v in campos_atualizaveis.items() if k != "preco_de_venda_real"
        }
        # preco_de_venda_real precisa permitir None explícito (limpar valor),
        # então é tratado separadamente do filtro "valor is not None" do repo.
        if "preco_de_venda_real" in campos_atualizaveis:
            receita.preco_de_venda_real = campos_atualizaveis["preco_de_venda_real"]

        await self._repo.atualizar(
            receita,
            campos_simples=campos_simples,
            ingredientes=data.ingredientes,
            etapas=data.etapas,
        )

        await historico.registrar(receita_id, tenant_id, usuario_id, "edicao")

        # Recarrega com relationships atualizados
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))

        logger.info(
            "receita_atualizada",
            tenant_id=str(tenant_id),
            action="update",
            entity="receita",
            entity_id=str(receita_id),
        )
        return await self._montar_response(receita, tenant_id)

    async def _validar_ingredientes(
        self,
        tenant_id: UUID,
        ingredientes: list[IngredienteInput],
        receita_id: UUID | None = None,
    ) -> None:
        """Valida materiais e receitas-base dentro do tenant e suas unidades."""
        componentes: list[UUID] = []
        for index, item in enumerate(ingredientes):
            if item.ingrediente_id is not None:
                ingrediente = await self._repo.buscar_ingrediente(
                    item.ingrediente_id, tenant_id
                )
                if not ingrediente:
                    raise ValidationError(
                        f"Material {item.ingrediente_id} não encontrado no estoque",
                        field=f"ingredientes.{index}.ingrediente_id",
                    )
                try:
                    converter_para_principal(
                        item.quantidade,
                        item.unidade,
                        ingrediente.unidade,
                        ingrediente.unidades_alternativas,
                    )
                except ValidationError as exc:
                    raise ValidationError(
                        exc.message, field=f"ingredientes.{index}.unidade"
                    ) from exc
                continue

            componente_id = item.receita_componente_id
            if componente_id is None:
                raise ValidationError(
                    "Selecione um material ou uma receita-base",
                    field=f"ingredientes.{index}.receita_componente_id",
                )
            componente = await self._repo.buscar_por_id(componente_id, tenant_id)
            if not componente:
                raise ValidationError(
                    "Receita-base não encontrada nesta loja",
                    field=f"ingredientes.{index}.receita_componente_id",
                )
            try:
                converter_quantidade(
                    item.quantidade, item.unidade, componente.rendimento_unidade
                )
            except ValidationError as exc:
                raise ValidationError(
                    exc.message, field=f"ingredientes.{index}.unidade"
                ) from exc
            componentes.append(componente_id)

        if receita_id is not None and componentes:
            await self._validar_ciclo_componentes(receita_id, componentes, tenant_id)

    async def _validar_ciclo_componentes(
        self, receita_id: UUID, componentes: list[UUID], tenant_id: UUID
    ) -> None:
        """Impede ciclos e composições com mais de 20 receitas encadeadas."""
        visitados: set[UUID] = set()

        async def percorrer(alvo: UUID, caminho: frozenset[UUID]) -> None:
            if alvo in caminho:
                raise ValidationError("A composição contém um ciclo")
            if len(caminho) >= 20:
                raise ValidationError("A composição pode ter no máximo 20 níveis")
            if alvo in visitados:
                return
            base = await self._repo.buscar_por_id(alvo, tenant_id)
            if base is None:
                raise ValidationError("Receita-base não encontrada nesta loja")
            referencias = {
                item.receita_componente_id
                for item in base.ingredientes
                if item.receita_componente_id is not None
            }
            ficha = base.ficha_tecnica or {}
            referencias.update(
                UUID(passo["receita_base_id"])
                for passo in ficha.get("passos", [])
                if passo.get("receita_base_id")
            )
            for referencia in referencias:
                await percorrer(referencia, caminho | {alvo})
            visitados.add(alvo)

        for componente_id in componentes:
            await percorrer(componente_id, frozenset({receita_id}))

    async def duplicar(self, receita_id: UUID, tenant_id: UUID, usuario_id: UUID | None = None) -> ReceitaResponse:
        """Duplica receita inteira (campos + ingredientes + etapas) com nome único."""
        original = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not original:
            raise NotFoundError("Receita", str(receita_id))

        nova = await self._repo.duplicar(original, tenant_id)
        await HistoricoReceita(self._db).inicial(nova.id, tenant_id, usuario_id, "copia")

        logger.info(
            "receita_duplicada",
            tenant_id=str(tenant_id),
            action="duplicate",
            entity="receita",
            entity_id=str(nova.id),
            origem_id=str(receita_id),
        )
        return await self._montar_response(nova, tenant_id)

    async def deletar(self, receita_id: UUID, tenant_id: UUID) -> None:
        await self._repo.travar_composicao(tenant_id)
        receita = await self._repo.buscar_por_id(receita_id, tenant_id)
        if not receita:
            raise NotFoundError("Receita", str(receita_id))
        if await self._repo.referencia_em_uso(receita_id, tenant_id, "receita_base_id"):
            raise ConflictError("Esta receita-base está em outra receita, ficha técnica ou produção. Remova o vínculo antes de excluir.")
        await self._repo.deletar(receita)

        logger.info(
            "receita_deletada",
            tenant_id=str(tenant_id),
            action="delete",
            entity="receita",
            entity_id=str(receita_id),
        )

    async def _montar_response(self, receita: Receita, tenant_id: UUID, caminho: frozenset[UUID] = frozenset()) -> ReceitaResponse:
        """Monta o response completo com custo calculado."""
        if receita.id in caminho or len(caminho) >= 20:
            raise ValidationError("A composição contém um ciclo ou mais de 20 níveis")
        caminho = caminho | {receita.id}
        config = await self._buscar_config(tenant_id)
        usuario = await self._buscar_valor_hora(tenant_id)
        ficha = receita.ficha_tecnica or {}
        componentes_calculados: dict[UUID, tuple[Receita, ReceitaResponse, Decimal]] = {}

        # Separa ingredientes "de receita" de embalagens — embalagem aparece
        # como linha distinta no breakdown e o usuário enxerga o custo isolado.
        itens_ingredientes: list[ItemIngredienteCalculo] = []
        itens_embalagem: list[ItemIngredienteCalculo] = []
        for item in receita.ingredientes:
            if item.ingrediente_id is not None:
                material = item.ingrediente
                if material is None or material.tenant_id != tenant_id:
                    raise ValidationError("Um material da receita não pertence a esta loja")
                quantidade = converter_para_principal(
                    item.quantidade,
                    item.unidade,
                    material.unidade,
                    material.unidades_alternativas,
                )
                if not ficha.get("composicao_ativa"):
                    calculo = ItemIngredienteCalculo(
                        nome=material.nome,
                        quantidade=quantidade,
                        custo_medio_por_unidade=material.custo_medio,
                    )
                    (itens_embalagem if material.tipo == "embalagem" else itens_ingredientes).append(calculo)
                continue

            componente_id = item.receita_componente_id
            if componente_id is None:
                continue
            componente = await self._repo.buscar_por_id(componente_id, tenant_id)
            if componente is None:
                raise ValidationError("Uma receita-base foi removida. Revise os ingredientes.")
            resposta = await self._montar_response(componente, tenant_id, caminho)
            quantidade = converter_quantidade(
                item.quantidade, item.unidade, componente.rendimento_unidade
            )
            componentes_calculados[item.id] = (componente, resposta, quantidade)
            if not ficha.get("composicao_ativa"):
                itens_ingredientes.append(
                    ItemIngredienteCalculo(
                        nome=componente.nome,
                        quantidade=quantidade,
                        custo_medio_por_unidade=resposta.custo.custo_por_unidade,
                    )
                )

        tempo_total_min = sum(e.duracao_minutos for e in receita.etapas)
        tempo_ativo_min = sum(
            e.duracao_minutos for e in receita.etapas if e.tipo_mao_obra == "direta"
        )
        tempo_passivo_min = tempo_total_min - tempo_ativo_min

        custo = calcular_custo_total(
            ingredientes=itens_ingredientes,
            embalagens=itens_embalagem,
            config=config,
            tempo_ativo_horas=minutos_para_horas(tempo_ativo_min),
            tempo_total_horas=minutos_para_horas(tempo_total_min),
            valor_hora=usuario,
            rendimento=receita.rendimento,
        )
        if ficha.get("composicao_ativa"):
            # Ficha descreve UMA unidade. Substitui ingredientes tradicionais;
            # tempo das etapas locais representa somente a montagem do produto.
            totais = {"custo_ingredientes": Decimal("0"), "custo_embalagem": Decimal("0"),
                      "custo_operacional": custo.custo_operacional,
                      "custo_mao_obra_direta": custo.custo_mao_obra_direta}
            for passo in ficha["passos"]:
                quantidade = Decimal(passo["quantidade"]) * receita.rendimento
                if passo.get("receita_base_id"):
                    base = await self._repo.buscar_por_id(UUID(passo["receita_base_id"]), tenant_id)
                    if not base:
                        raise ValidationError("Uma receita-base foi removida. Revise a ficha técnica.")
                    fator = converter_quantidade(quantidade, passo["unidade"], base.rendimento_unidade) / base.rendimento
                    resposta_base = await self._montar_response(base, tenant_id, caminho)
                    for campo in totais:
                        totais[campo] += getattr(resposta_base.custo, campo) * fator
                else:
                    material = await self._repo.buscar_ingrediente(UUID(passo["ingrediente_id"]), tenant_id)
                    if not material:
                        raise ValidationError("Um material foi removido. Revise a ficha técnica.")
                    consumo = converter_para_principal(quantidade, passo["unidade"], material.unidade, material.unidades_alternativas)
                    campo = "custo_embalagem" if material.tipo == "embalagem" else "custo_ingredientes"
                    totais[campo] += consumo * material.custo_medio
            custo = replace(custo, **{campo: valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for campo, valor in totais.items()})
        preco_recomendado = calcular_preco_recomendado(custo.custo_por_unidade, receita.margem_desejada)

        # Preço sugerido para venda via iFood: cobre a margem mesmo após a
        # comissão do marketplace + a taxa do cartão. None quando não há taxas
        # configuradas (evita exibir um valor idêntico ao preço direto).
        taxa_ifood_total = config.taxa_ifood + config.taxa_cartao
        preco_recomendado_ifood: Decimal | None = None
        if taxa_ifood_total > 0 and custo.custo_por_unidade > 0:
            try:
                preco_recomendado_ifood = calcular_preco_recomendado_com_taxas(
                    custo.custo_por_unidade, receita.margem_desejada, taxa_ifood_total
                )
            except ValueError:
                # Margem + taxas ≥ 100%: não há preço viável; deixa None.
                preco_recomendado_ifood = None

        # Métricas que dependem do preço de venda real informado pela usuária.
        lucro_estimado: Decimal | None = None
        margem_real: Decimal | None = None
        lucro_por_minuto: Decimal | None = None
        if receita.preco_de_venda_real is not None and receita.preco_de_venda_real > 0:
            lucro_estimado = calcular_lucro_estimado(
                receita.preco_de_venda_real, custo.custo_por_unidade
            )
            margem_real = calcular_margem_real(
                receita.preco_de_venda_real, custo.custo_por_unidade
            )
            lucro_por_minuto = calcular_lucro_por_minuto(
                lucro_estimado, receita.rendimento, tempo_ativo_min
            )

        custo_por_hora_produzida = calcular_custo_por_hora_produzida(
            custo.custo_total, minutos_para_horas(tempo_ativo_min)
        )

        ingredientes_resp: list[IngredienteReceitaResponse] = []
        for item in receita.ingredientes:
            if item.ingrediente_id is not None:
                material = item.ingrediente
                nome = material.nome if material and material.tenant_id == tenant_id else "Indisponível"
                custo_item = Decimal("0")
                if material and material.tenant_id == tenant_id:
                    quantidade = converter_para_principal(
                        item.quantidade,
                        item.unidade,
                        material.unidade,
                        material.unidades_alternativas,
                    )
                    custo_item = (quantidade * material.custo_medio).quantize(Decimal("0.01"))
                ingredientes_resp.append(IngredienteReceitaResponse(
                    id=item.id,
                    ingrediente_id=item.ingrediente_id,
                    receita_componente_id=None,
                    tipo_origem="material",
                    tipo_material=material.tipo if material and material.tenant_id == tenant_id else None,
                    nome_ingrediente=nome,
                    quantidade=item.quantidade,
                    unidade=item.unidade,
                    custo_total=custo_item,
                ))
                continue

            calculado = componentes_calculados.get(item.id)
            if calculado is None:
                ingredientes_resp.append(IngredienteReceitaResponse(
                    id=item.id,
                    ingrediente_id=None,
                    receita_componente_id=item.receita_componente_id,
                    tipo_origem="receita_base",
                    tipo_material=None,
                    nome_ingrediente="Indisponível",
                    quantidade=item.quantidade,
                    unidade=item.unidade,
                    custo_total=Decimal("0"),
                ))
                continue
            componente, resposta, quantidade = calculado
            ingredientes_resp.append(IngredienteReceitaResponse(
                id=item.id,
                ingrediente_id=None,
                receita_componente_id=componente.id,
                tipo_origem="receita_base",
                tipo_material=None,
                nome_ingrediente=componente.nome,
                quantidade=item.quantidade,
                unidade=item.unidade,
                custo_total=(quantidade * resposta.custo.custo_por_unidade).quantize(Decimal("0.01")),
            ))

        custo_resp = CustoDetalhadoResponse(
            custo_ingredientes=custo.custo_ingredientes,
            custo_embalagem=custo.custo_embalagem,
            custo_operacional=custo.custo_operacional,
            custo_mao_obra_direta=custo.custo_mao_obra_direta,
            custo_total=custo.custo_total,
            custo_por_unidade=custo.custo_por_unidade,
            preco_minimo=custo.preco_minimo,
            preco_recomendado=preco_recomendado,
            preco_recomendado_ifood=preco_recomendado_ifood,
            tempo_total_minutos=tempo_total_min,
            tempo_ativo_minutos=tempo_ativo_min,
            tempo_passivo_minutos=tempo_passivo_min,
            lucro_estimado=lucro_estimado,
            margem_real=margem_real,
            custo_por_hora_produzida=custo_por_hora_produzida,
            lucro_por_minuto=lucro_por_minuto,
        )

        return ReceitaResponse(
            id=receita.id,
            tenant_id=receita.tenant_id,
            nome=receita.nome,
            categoria=receita.categoria,
            rendimento=receita.rendimento,
            rendimento_unidade=receita.rendimento_unidade,
            margem_desejada=receita.margem_desejada,
            preco_de_venda_real=receita.preco_de_venda_real,
            modo_preparo=receita.modo_preparo,
            foto_url=receita.foto_url,
            created_at=receita.created_at,
            updated_at=receita.updated_at,
            ingredientes=ingredientes_resp,
            etapas=[e for e in receita.etapas],
            custo=custo_resp,
            versao=receita.versao,
            tipo_cadastro=(
                "produto"
                if ficha.get("composicao_ativa")
                or any(item.receita_componente_id for item in receita.ingredientes)
                else "receita_base"
            ),
        )

    async def _buscar_config(self, tenant_id: UUID) -> ConfiguracaoCustoCalculo:
        result = await self._db.execute(
            select(ConfiguracaoCusto).where(
                ConfiguracaoCusto.tenant_id == tenant_id,
                ConfiguracaoCusto.deleted_at.is_(None),
            )
        )
        config = result.scalar_one_or_none()
        if config:
            return ConfiguracaoCustoCalculo(
                custo_operacional_mensal=config.custo_operacional_mensal,
                horas_mensais=config.horas_mensais,
                taxa_ifood=config.taxa_ifood,
                taxa_cartao=config.taxa_cartao,
            )
        return ConfiguracaoCustoCalculo(
            custo_operacional_mensal=Decimal("0"),
            horas_mensais=Decimal("160"),
        )

    async def _buscar_valor_hora(self, tenant_id: UUID) -> Decimal:
        from infrastructure.database.models import Usuario

        result = await self._db.execute(
            select(Usuario.valor_hora).where(
                Usuario.tenant_id == tenant_id,
                Usuario.deleted_at.is_(None),
                Usuario.ativo.is_(True),
            ).limit(1)
        )
        valor = result.scalar_one_or_none()
        return valor or Decimal("0")
