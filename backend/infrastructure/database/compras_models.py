"""Catálogo comercial e compras, isolados por conta e com histórico preservado."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models import TenantMixin, TimestampMixin
from infrastructure.database.session import Base


class ProdutoCompra(TenantMixin, TimestampMixin, Base):
    __tablename__ = "produtos_compra"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    ingrediente_id: Mapped[UUID] = mapped_column(ForeignKey("ingredientes.id"), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    marca: Mapped[str] = mapped_column(String(200))
    fabricante: Mapped[str | None] = mapped_column(String(200))
    variante: Mapped[str | None] = mapped_column(String(200))
    conteudo_embalagem: Mapped[Decimal] = mapped_column(Numeric(16, 8))
    unidade_conteudo: Mapped[str] = mapped_column(String(40))
    fator_para_principal: Mapped[Decimal | None] = mapped_column(Numeric(16, 8))
    gtin: Mapped[str | None] = mapped_column(String(14))
    aprovado: Mapped[bool] = mapped_column(Boolean, default=False)
    revisao: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        Index(
            "uq_produtos_compra_gtin_ativo",
            "tenant_id",
            "gtin",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND gtin IS NOT NULL"),
        ),
    )


class FornecedorCompra(TenantMixin, TimestampMixin, Base):
    __tablename__ = "fornecedores_compra"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    nome: Mapped[str] = mapped_column(String(200))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    revisao: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        Index(
            "uq_fornecedores_compra_cnpj_ativo",
            "tenant_id",
            "cnpj",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND cnpj IS NOT NULL"),
        ),
    )


class AprovacaoFornecedorProduto(TenantMixin, TimestampMixin, Base):
    __tablename__ = "aprovacoes_fornecedor_produto"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    fornecedor_id: Mapped[UUID] = mapped_column(ForeignKey("fornecedores_compra.id"), index=True)
    produto_id: Mapped[UUID] = mapped_column(ForeignKey("produtos_compra.id"), index=True)
    __table_args__ = (UniqueConstraint("tenant_id", "fornecedor_id", "produto_id"),)


class AliasCompra(TenantMixin, TimestampMixin, Base):
    __tablename__ = "aliases_compra"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    fornecedor_id: Mapped[UUID] = mapped_column(ForeignKey("fornecedores_compra.id"), index=True)
    produto_id: Mapped[UUID] = mapped_column(ForeignKey("produtos_compra.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    valor_original: Mapped[str] = mapped_column(String(500))
    valor_normalizado: Mapped[str] = mapped_column(String(500))
    revisao: Mapped[int] = mapped_column(Integer, default=1)
    produto_revisao_confirmada: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        Index(
            "uq_aliases_compra_ativo",
            "tenant_id",
            "fornecedor_id",
            "tipo",
            "valor_normalizado",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Compra(TenantMixin, TimestampMixin, Base):
    __tablename__ = "compras"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    chave: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    fingerprint: Mapped[str] = mapped_column(String(64))
    usuario_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    operador_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    fornecedor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("fornecedores_compra.id"), index=True
    )
    fornecedor_nome_snapshot: Mapped[str | None] = mapped_column(String(200))
    estabelecimento_original: Mapped[str | None] = mapped_column(String(200))
    data_compra: Mapped[date | None] = mapped_column(Date, index=True)
    origem: Mapped[str] = mapped_column(String(30))
    identidade_nota: Mapped[str | None] = mapped_column(String(44), index=True)
    total_nota: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    total_selecionado: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    metadados_completos: Mapped[bool] = mapped_column(Boolean)
    resultado: Mapped[dict] = mapped_column(JSONB, default=dict)
    __table_args__ = (UniqueConstraint("tenant_id", "chave"),)


class CompraItem(TenantMixin, TimestampMixin, Base):
    __tablename__ = "compra_itens"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    compra_id: Mapped[UUID] = mapped_column(ForeignKey("compras.id"), index=True)
    ingrediente_id: Mapped[UUID] = mapped_column(ForeignKey("ingredientes.id"), index=True)
    produto_id: Mapped[UUID | None] = mapped_column(ForeignKey("produtos_compra.id"), index=True)
    movimentacao_id: Mapped[UUID] = mapped_column(
        ForeignKey("movimentacoes_estoque.id"), unique=True
    )
    indice: Mapped[int] = mapped_column(Integer)
    quantidade_principal: Mapped[Decimal] = mapped_column(Numeric(16, 8))
    custo_normalizado: Mapped[Decimal] = mapped_column(Numeric(16, 8))
    preco_total: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    snapshot: Mapped[dict] = mapped_column(JSONB)
