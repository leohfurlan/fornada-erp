"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowDown, ArrowUp, ChevronDown, ChevronUp, History, Pencil, Plus, Search, SlidersHorizontal, XCircle } from "lucide-react";
import { useEstoqueFilters, type EstoqueSortKey, type EstoqueSortDir } from "@/hooks/use-estoque-filters";
import { useIngredientes } from "@/hooks/use-estoque";
import { EstoqueBadge } from "@/components/shared/estoque-badge";
import { AjustarEstoqueDialog } from "@/components/shared/ajustar-estoque-dialog";
import { MoneyDisplay } from "@/components/shared/money-display";
import { TabelaEstoqueDesktop } from "@/components/shared/tabela-estoque-desktop";
import { TabEstoquePA } from "@/components/shared/tab-estoque-pa";
import { cn, formatDataHora, formatQuantidade } from "@/lib/utils";
import { custoReferencia } from "@/lib/custo-referencia";
import { TIPOS_PRODUTO } from "@/lib/unidades";
import type { Ingrediente } from "@/types";

type SortKeyMobile = EstoqueSortKey;
type SortDir = EstoqueSortDir;
type Tab = "ingredientes" | "pa";

export default function EstoquePage() {
  const searchParams = useSearchParams();
  const tabInicial = (searchParams.get("tab") === "pa" ? "pa" : "ingredientes") as Tab;
  const [tab, setTab] = useState<Tab>(tabInicial);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Estoque</h1>
        {tab === "ingredientes" && (
          <Link
            href="/estoque/novo"
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shrink-0"
          >
            <Plus className="h-4 w-4" />
            Novo
          </Link>
        )}
      </div>

      <div className="flex border-b">
        <button
          type="button"
          onClick={() => setTab("ingredientes")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            tab === "ingredientes"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          Ingredientes
        </button>
        <button
          type="button"
          onClick={() => setTab("pa")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            tab === "pa"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          Produtos prontos
        </button>
      </div>

      {tab === "ingredientes" ? <TabIngredientes /> : <TabEstoquePA />}
    </div>
  );
}

function TabIngredientes() {
  const { data: ingredientes, isLoading, error } = useIngredientes();
  const { filters, update, clear } = useEstoqueFilters();
  const { busca, tipo: filtroTipo, status: filtroStatus, sortKey: sortKeyMobile, sortDir: sortDirMobile } = filters;
  const [filtersOpen, setFiltersOpen] = useState(false);
  const searchInput = useRef<HTMLInputElement>(null);
  const activeFilters = Number(Boolean(filtroTipo)) + Number(Boolean(filtroStatus));
  const hasOptions = activeFilters > 0 || sortKeyMobile !== "codigo" || sortDirMobile !== "asc";

  const filtrados = useMemo(() => {
    if (!ingredientes) return [];
    const buscaLower = busca.trim().toLowerCase();
    return ingredientes.filter((i) => {
      if (filtroTipo && i.tipo !== filtroTipo) return false;
      if (filtroStatus && i.status_estoque !== filtroStatus) return false;
      if (
        buscaLower &&
        !i.nome.toLowerCase().includes(buscaLower) &&
        String(i.codigo) !== buscaLower
      )
        return false;
      return true;
    });
  }, [ingredientes, busca, filtroTipo, filtroStatus]);

  // Ordenação mobile aplicada sobre a lista filtrada
  const filtradosMobile = useMemo(() => {
    return [...filtrados].sort((a, b) => {
      const av = sortKeyMobile === "custo_medio" ? custoReferencia(a).valor : a[sortKeyMobile];
      const bv = sortKeyMobile === "custo_medio" ? custoReferencia(b).valor : b[sortKeyMobile];
      const cmp = compararValores(av, bv);
      return sortDirMobile === "asc" ? cmp : -cmp;
    });
  }, [filtrados, sortKeyMobile, sortDirMobile]);

  if (error) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar o estoque. Tente novamente.
      </div>
    );
  }

  const alertas = ingredientes?.filter(
    (i) =>
      i.status_estoque === "baixo" ||
      i.status_estoque === "critico" ||
      i.status_estoque === "zerado"
  );

  return (
    <div className="space-y-4">
      {!!alertas?.length && (
        <div className="rounded-xl bg-orange-50 border border-orange-200 p-3 text-sm">
          <p className="font-medium text-orange-800">
            {alertas.length} item{alertas.length > 1 ? "s" : ""} com estoque baixo
          </p>
          <p className="text-orange-700 text-xs mt-0.5">
            {alertas.map((a) => a.nome).join(", ")}
          </p>
        </div>
      )}

      <div className="space-y-3">
        <div className="relative">
          <label className="sr-only" htmlFor="estoque-busca">Buscar por nome ou código</label>
          <Search aria-hidden="true" className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input ref={searchInput} id="estoque-busca" type="text" placeholder="Buscar por nome ou código..." value={busca}
            onChange={event => update({ busca: event.target.value })}
            className="min-h-12 w-full rounded-lg border py-2 pl-9 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
          {busca && <button type="button" aria-label="Limpar busca" onClick={() => { update({ busca: "" }); searchInput.current?.focus(); }} className="absolute right-0 top-0 flex h-full min-h-12 min-w-12 items-center justify-center rounded-r-lg text-muted-foreground hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"><XCircle aria-hidden="true" className="h-5 w-5" /></button>}
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" aria-expanded={filtersOpen} aria-controls="filtros-estoque" onClick={() => setFiltersOpen(current => !current)}
            className={cn("inline-flex min-h-12 items-center gap-2 rounded-lg border px-4 text-sm font-semibold hover:bg-muted", (filtersOpen || activeFilters > 0) && "border-primary text-primary")}>
            <SlidersHorizontal aria-hidden="true" className="h-4 w-4" />Filtros{activeFilters > 0 && <span className="rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">{activeFilters}</span>}
          </button>
          <button type="button" disabled={!hasOptions} onClick={clear} className="min-h-12 rounded-lg border px-4 text-sm font-semibold hover:bg-muted disabled:opacity-40">Limpar filtros</button>
        </div>
        {filtersOpen && <section id="filtros-estoque" aria-label="Filtros do estoque" className="space-y-4 rounded-xl border bg-card p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-2 text-sm font-medium">Tipo de item
              <select value={filtroTipo} onChange={event => update({ tipo: event.target.value })} className="mt-2 min-h-12 w-full rounded-lg border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
                <option value="">Todos os tipos</option>
                {TIPOS_PRODUTO.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="space-y-2 text-sm font-medium">Situação do estoque
              <select value={filtroStatus} onChange={event => update({ status: event.target.value })} className="mt-2 min-h-12 w-full rounded-lg border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
                <option value="">Todos os status</option><option value="ok">Estoque OK</option><option value="baixo">Baixo</option><option value="critico">Crítico</option><option value="zerado">Zerado</option>
              </select>
            </label>
          </div>
          <div className="md:hidden"><p className="mb-2 text-sm font-medium">Ordenação</p><OrdenacaoMobile sortKey={sortKeyMobile} sortDir={sortDirMobile} onMudar={(sortKey, sortDir) => update({ sortKey, sortDir })} /></div>
        </section>}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !ingredientes?.length ? (
        <EmptyState />
      ) : filtrados.length === 0 ? (
        <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          Nenhum item encontrado com esses filtros
        </div>
      ) : (
        <>
          {/* DESKTOP: Tabela com sort, resize, reorder e visibility */}
          <div className="hidden md:block">
            <TabelaEstoqueDesktop ingredientes={filtrados} />
          </div>

          {/* MOBILE: Cards expansíveis */}
          <div className="md:hidden">
            <div className="space-y-2 mt-3">
              {filtradosMobile.map((i) => (
                <CardEstoque key={i.id} item={i} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// -------- Helpers --------

function compararValores(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === "string" && typeof b === "string") {
    const na = parseFloat(a);
    const nb = parseFloat(b);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.localeCompare(b, "pt-BR");
  }
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "pt-BR");
}

function tipoLabel(value: string): string {
  return TIPOS_PRODUTO.find((t) => t.value === value)?.label ?? value;
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
      <p className="font-medium">Nenhum item cadastrado</p>
      <p className="text-sm mt-1">Adicione ingredientes, embalagens e insumos para calcular custos</p>
      <Link
        href="/estoque/novo"
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        <Plus className="h-4 w-4" />
        Adicionar item
      </Link>
    </div>
  );
}

// -------- Mobile: Ordenação + Cards --------

const OPCOES_ORDENACAO: { key: SortKeyMobile; label: string }[] = [
  { key: "codigo", label: "Código" },
  { key: "nome", label: "Descrição" },
  { key: "saldo", label: "Saldo" },
  { key: "custo_medio", label: "Custo" },
  { key: "data_custo_atualizado", label: "Data custo" },
];

function OrdenacaoMobile({
  sortKey,
  sortDir,
  onMudar,
}: {
  sortKey: SortKeyMobile;
  sortDir: SortDir;
  onMudar: (k: SortKeyMobile, d: SortDir) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <select
        aria-label="Ordenar itens"
        value={sortKey}
        onChange={(e) => onMudar(e.target.value as SortKeyMobile, sortDir)}
        className="min-h-12 min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
      >
        {OPCOES_ORDENACAO.map((o) => (
          <option key={o.key} value={o.key}>
            Ordenar por {o.label.toLowerCase()}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => onMudar(sortKey, sortDir === "asc" ? "desc" : "asc")}
        className="flex min-h-12 min-w-12 items-center justify-center rounded-lg border hover:bg-muted"
        aria-label="Inverter ordem"
      >
        {sortDir === "asc" ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
      </button>
    </div>
  );
}

function CardEstoque({ item }: { item: Ingrediente }) {
  const custo = custoReferencia(item);
  const [aberto, setAberto] = useState(false);
  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent/50"
      >
        <span className="font-mono text-xs text-muted-foreground shrink-0 w-10 text-right">
          {String(item.codigo).padStart(3, "0")}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-medium text-sm truncate">{item.nome}</p>
            <EstoqueBadge status={item.status_estoque} />
          </div>
          <p className="text-xs text-muted-foreground">
            Saldo:{" "}
            <span className="font-medium text-foreground">
              {formatQuantidade(item.saldo)} {item.unidade}
            </span>{" "}
            · {tipoLabel(item.tipo)}
          </p>
        </div>
        <div className="text-right shrink-0">
          <MoneyDisplay value={custo.valor} size="sm" />
          <p className="text-xs text-muted-foreground">/{custo.unidade}</p>
        </div>
        {aberto ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
      </button>

      {aberto && (
        <div className="border-t bg-muted/20 px-4 py-3 space-y-2 text-sm">
          <DetalheLinha
            label="Estoque"
            valor={`${formatQuantidade(item.estoque_atual)} ${item.unidade}`}
          />
          <DetalheLinha
            label="Reservado"
            valor={`${formatQuantidade(item.quantidade_reservada)} ${item.unidade}`}
          />
          <DetalheLinha
            label="Estoque mínimo"
            valor={`${formatQuantidade(item.estoque_minimo)} ${item.unidade}`}
          />
          <DetalheLinha label={`Custo médio por ${custo.unidade}`} valor={<MoneyDisplay value={custo.valor} size="sm" />} />
          <DetalheLinha label="Custo atualizado em" valor={formatDataHora(item.data_custo_atualizado)} />

          <div className="flex gap-2 pt-2">
            <Link
              href={`/estoque/${item.id}/historico`}
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              <History className="h-3.5 w-3.5" />
              Histórico
            </Link>
            <Link
              href={`/estoque/${item.id}/editar`}
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              <Pencil className="h-3.5 w-3.5" />
              Editar
            </Link>
          </div>
          <AjustarEstoqueDialog item={item} variant="button" />
        </div>
      )}
    </div>
  );
}

function DetalheLinha({ label, valor }: { label: string; valor: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{valor}</span>
    </div>
  );
}

