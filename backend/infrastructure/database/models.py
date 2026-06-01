from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.session import Base


class TenantMixin:
    """Coluna tenant_id obrigatória em todas as tabelas de negócio."""

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )


class TimestampMixin:
    """Colunas de auditoria padrão."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    plano: Mapped[str] = mapped_column(String(20), default="starter", nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="tenant")


class Usuario(TenantMixin, TimestampMixin, Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    valor_hora: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="usuarios")


class ConfiguracaoCusto(TenantMixin, TimestampMixin, Base):
    """Configurações de custo operacional e hora trabalhada por tenant."""

    __tablename__ = "configuracoes_custo"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    custo_operacional_mensal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    horas_mensais: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("160"), nullable=False
    )


class Ingrediente(TenantMixin, TimestampMixin, Base):
    __tablename__ = "ingredientes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Código sequencial humano-friendly, único por tenant (1, 2, 3...).
    # Atribuído pelo repository ao criar.
    codigo: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Classificação: ingrediente | embalagem | insumo | descartavel | outro
    tipo: Mapped[str] = mapped_column(String(30), default="ingrediente", nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False)
    estoque_atual: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0"), nullable=False
    )
    # Comprometido em pedidos em produção (futuro). Por ora sempre 0.
    quantidade_reservada: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0"), nullable=False
    )
    estoque_minimo: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0"), nullable=False
    )
    custo_medio: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0"), nullable=False
    )
    # Atualizado SOMENTE quando o custo_medio muda (via entrada de estoque).
    # Diferente de updated_at que muda em qualquer edição do registro.
    data_custo_atualizado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    movimentacoes: Mapped[list["MovimentacaoEstoque"]] = relationship(back_populates="ingrediente")


class MovimentacaoEstoque(TenantMixin, TimestampMixin, Base):
    __tablename__ = "movimentacoes_estoque"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    ingrediente_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ingredientes.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # entrada | saida | ajuste
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    origem: Mapped[str] = mapped_column(String(50), nullable=False)  # compra | producao | ajuste

    ingrediente: Mapped["Ingrediente"] = relationship(back_populates="movimentacoes")


class Receita(TenantMixin, TimestampMixin, Base):
    __tablename__ = "receitas"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    rendimento: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    rendimento_unidade: Mapped[str] = mapped_column(String(50), nullable=False)
    foto_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    margem_desejada: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.30"), nullable=False
    )
    # Preço de venda real informado pela confeiteira. Usado para calcular lucro
    # estimado, margem real e lucro/min. Nulo quando ainda não decidido.
    preco_de_venda_real: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    # Modo de preparo em texto livre (quebras de linha preservadas na exibição).
    # Suporta markdown leve no futuro; por ora texto puro com whitespace-pre-wrap.
    modo_preparo: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingredientes: Mapped[list["ReceitaIngrediente"]] = relationship(
        back_populates="receita", cascade="all, delete-orphan"
    )
    etapas: Mapped[list["ReceitaEtapa"]] = relationship(
        back_populates="receita", cascade="all, delete-orphan", order_by="ReceitaEtapa.ordem"
    )


class ReceitaIngrediente(TimestampMixin, Base):
    __tablename__ = "receita_ingredientes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    receita_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    ingrediente_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ingredientes.id"), nullable=False
    )
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False)

    receita: Mapped["Receita"] = relationship(back_populates="ingredientes")
    ingrediente: Mapped["Ingrediente"] = relationship()


class EtapaPadrao(TenantMixin, TimestampMixin, Base):
    """
    Etapas pré-cadastradas que a confeiteira reutiliza ao montar receitas.
    Ex: "Preparo da massa" (direta, 30min), "Limpeza" (indireta, 15min).
    """

    __tablename__ = "etapas_padrao"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_mao_obra: Mapped[str] = mapped_column(String(20), default="direta", nullable=False)
    duracao_minutos_default: Mapped[int] = mapped_column(Integer, default=30, nullable=False)


class EstoqueProdutoAcabado(TenantMixin, TimestampMixin, Base):
    """Saldo de produto acabado (receita pronta para venda).

    Um registro por (tenant_id, receita_id). Saldo é alimentado por OPs
    finalizadas e debitado por Vendas e Pedidos entregues.
    """

    __tablename__ = "estoque_produto_acabado"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    receita_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    qtd_disponivel: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"), nullable=False
    )
    qtd_minima: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"), nullable=False
    )

    receita: Mapped["Receita"] = relationship()


class MovimentacaoEstoquePA(TenantMixin, TimestampMixin, Base):
    """Trilha de auditoria do estoque de produto acabado."""

    __tablename__ = "movimentacoes_estoque_pa"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    receita_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # entrada | saida | ajuste
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    # Origem: 'op:N' (ordem de produção), 'venda:N', 'pedido:N', 'ajuste'.
    origem: Mapped[str] = mapped_column(String(50), nullable=False)


class Cliente(TenantMixin, TimestampMixin, Base):
    __tablename__ = "clientes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")


class Pedido(TenantMixin, TimestampMixin, Base):
    __tablename__ = "pedidos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Número sequencial humano-friendly, único por tenant (1, 2, 3...).
    # Atribuído pelo repository ao criar.
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cliente_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True, index=True
    )
    # orcamento | aprovado | em_producao | finalizado | entregue | cancelado
    status: Mapped[str] = mapped_column(String(30), default="orcamento", nullable=False, index=True)
    data_entrega: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    foto_referencia_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    cliente: Mapped["Cliente | None"] = relationship(back_populates="pedidos")
    itens: Mapped[list["PedidoItem"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )


class PedidoItem(TenantMixin, TimestampMixin, Base):
    __tablename__ = "pedido_itens"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    pedido_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receita_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receitas.id"), nullable=False
    )
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pedido: Mapped["Pedido"] = relationship(back_populates="itens")
    receita: Mapped["Receita"] = relationship()


class Venda(TenantMixin, TimestampMixin, Base):
    """Venda imediata multicanal (loja, WhatsApp, iFood, Instagram, outro).

    Diferente do Pedido (encomenda), a venda registra saída de produto
    acabado já produzido. Cliente é opcional (loja física, venda avulsa).
    """

    __tablename__ = "vendas"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cliente_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True, index=True
    )
    canal: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    data_venda: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    cliente: Mapped["Cliente | None"] = relationship()
    itens: Mapped[list["VendaItem"]] = relationship(
        back_populates="venda", cascade="all, delete-orphan"
    )


class VendaItem(TenantMixin, TimestampMixin, Base):
    __tablename__ = "venda_itens"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    venda_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vendas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receita_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receitas.id"), nullable=False
    )
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    venda: Mapped["Venda"] = relationship(back_populates="itens")
    receita: Mapped["Receita"] = relationship()


class OrdemProducao(TenantMixin, TimestampMixin, Base):
    """Ordem de Produção (OP) — uma receita produzida em N unidades.

    Sprint 3: substitui o fluxo de produção que estava embutido em Pedido.
    Pode estar vinculada a um pedido específico (`pedido_id`) ou produzir
    para estoque (sem `pedido_id`). Sempre uma receita por OP — agrupamento
    de múltiplas produções no dia se dá por filtro de data, não por OP única.
    """

    __tablename__ = "ordens_producao"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    receita_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    # Quando preenchido, OP atende uma encomenda específica (rastreio cruzado).
    pedido_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("pedidos.id"), nullable=True, index=True
    )
    qtd_planejada: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    # Preenchida no apontamento (transição → finalizada). Pode diferir de qtd_planejada.
    qtd_produzida: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="planejada", nullable=False, index=True
    )  # planejada | em_producao | finalizada | cancelada
    data_prevista: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    receita: Mapped["Receita"] = relationship()
    pedido: Mapped["Pedido | None"] = relationship()


class AgendaItem(TenantMixin, TimestampMixin, Base):
    """Item da Agenda de Produção — planejamento livre da confeiteira.

    Diferente da OrdemProducao (documento formal com estado e efeito em estoque),
    a Agenda é só planejamento visual: receitas a produzir, pedidos a preparar e
    tarefas domésticas da confeitaria. Pode VINCULAR (referência cruzada, só
    leitura) uma receita, um pedido ou uma OP existente, mas nunca cria nem altera
    esses recursos. Sem efeito em estoque.
    """

    __tablename__ = "agenda_itens"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    # 'receita' | 'pedido' | 'tarefa'
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Nulo = dia inteiro (sem horário definido).
    hora_inicio: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    hora_fim: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    # Hex da cor customizada ex: '#f97316'. Nulo = usa cor padrão por tipo na UI.
    cor: Mapped[str | None] = mapped_column(String(7), nullable=True)
    concluido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # FKs opcionais — vínculo de leitura cruzada. ondelete='SET NULL': remover a
    # receita/pedido/OP não deve destruir o planejamento já feito na agenda.
    receita_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("receitas.id", ondelete="SET NULL"),
        nullable=True,
    )
    pedido_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pedidos.id", ondelete="SET NULL"),
        nullable=True,
    )
    ordem_producao_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ordens_producao.id", ondelete="SET NULL"),
        nullable=True,
    )

    receita: Mapped["Receita | None"] = relationship(lazy="select")
    pedido: Mapped["Pedido | None"] = relationship(lazy="select")
    ordem_producao: Mapped["OrdemProducao | None"] = relationship(lazy="select")


class ReceitaEtapa(TimestampMixin, Base):
    __tablename__ = "receita_etapas"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    receita_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("receitas.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    duracao_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    # direta = tempo direto de fabricação; indireta = limpeza, organização etc.
    tipo_mao_obra: Mapped[str] = mapped_column(String(20), default="direta", nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    receita: Mapped["Receita"] = relationship(back_populates="etapas")
