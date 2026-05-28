from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DECIMAL,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
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
