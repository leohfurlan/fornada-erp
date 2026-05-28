"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ChevronDown, ChevronUp, Plus, Search } from "lucide-react";
import { useIngredientes } from "@/hooks/use-estoque";
import { EstoqueBadge } from "@/components/shared/estoque-badge";
import { MoneyDisplay } from "@/components/shared/money-display";
import { TabelaEstoqueDesktop } from "@/components/shared/tabela-estoque-desktop";
import { formatDataHora, formatQuantidade } from "@/lib/utils";
import { TIPOS_PRODUTO } from "@/lib/unidades";
import type { Ingrediente } from "@/types";

type SortKeyMobile = "codigo" | "nome" | "saldo" | "custo_medio" | "data_custo_atualizado";
type SortDir = "asc" | "desc";

export default function EstoquePage() {
  const { data: ingredientes, isLoading, error } = useIngredientes();
  const [busca, setBusca] = useState("");
  const [filtroTipo, setFiltroTipo] = useState<string>("");
  const [filtroStatus, setFiltroStatus] = useState<string>("");

  // Ordenação só para o layout mobile (desktop usa o controle da própria tabela)
  const [sortKeyMobile, setSortKeyMobile] = useState<SortKeyMobile>("codigo");
  const [sortDirMobile, setSortDirMobile] = useState<SortDir>("asc");

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
      const av = a[sortKeyMobile];
      const bv = b[sortKeyMobile];
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
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-bold">Estoque</h1>
        <Link
          href="/estoque/novo"
          className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shrink-0"
        >
          <Plus className="h-4 w-4" />
          Novo
        </Link>
      </div>

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

      {/* Filtros */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por nome ou código..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="w-full rounded-lg border pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div className="flex gap-2">
          <select
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value)}
            className="flex-1 rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
          >
            <option value="">Todos os tipos</option>
            {TIPOS_PRODUTO.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <select
            value={filtroStatus}
            onChange={(e) => setFiltroStatus(e.target.value)}
            className="flex-1 rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
          >
            <option value="">Todos os status</option>
            <option value="ok">Estoque OK</option>
            <option value="baixo">Baixo</option>
            <option value="critico">Crítico</option>
            <option value="zerado">Zerado</option>
          </select>
        </div>
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
            <OrdenacaoMobile
              sortKey={sortKeyMobile}
              sortDir={sortDirMobile}
              onMudar={(k, d) => {
                setSortKeyMobile(k);
                setSortDirMobile(d);
              }}
            />
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
        value={sortKey}
        onChange={(e) => onMudar(e.target.value as SortKeyMobile, sortDir)}
        className="flex-1 rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
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
        className="p-2 rounded-lg border hover:bg-muted"
        aria-label="Inverter ordem"
      >
        {sortDir === "asc" ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
      </button>
    </div>
  );
}

function CardEstoque({ item }: { item: Ingrediente }) {
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
          <MoneyDisplay value={item.custo_medio} size="sm" />
          <p className="text-xs text-muted-foreground">/{item.unidade}</p>
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
          <DetalheLinha label="Custo médio" valor={<MoneyDisplay value={item.custo_medio} size="sm" />} />
          <DetalheLinha label="Custo atualizado em" valor={formatDataHora(item.data_custo_atualizado)} />
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

