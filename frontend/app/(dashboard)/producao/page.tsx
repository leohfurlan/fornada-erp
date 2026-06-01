"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Calendar, ChefHat, Plus } from "lucide-react";
import { useOrdensProducao } from "@/hooks/use-producao";
import { OpStatusBadge, STATUS_OP_LABEL } from "@/components/shared/op-status-badge";
import { cn, formatDataOP, formatQuantidade } from "@/lib/utils";
import type { OrdemProducao, StatusOP } from "@/types";

const FILTROS_STATUS: { value: StatusOP | ""; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "planejada", label: STATUS_OP_LABEL.planejada },
  { value: "em_producao", label: STATUS_OP_LABEL.em_producao },
  { value: "finalizada", label: STATUS_OP_LABEL.finalizada },
];

export default function ProducaoPage() {
  const [filtro, setFiltro] = useState<StatusOP | "">("");
  const { data: ordens, isLoading, error } = useOrdensProducao(
    filtro ? { status: filtro } : {}
  );

  const grupos = useMemo(() => agruparPorData(ordens ?? []), [ordens]);

  if (error) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar as ordens de produção.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Produção</h1>
        <Link
          href="/producao/nova"
          className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
        >
          <Plus className="h-4 w-4" />
          Nova OP
        </Link>
      </div>

      <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
        {FILTROS_STATUS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFiltro(f.value)}
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filtro === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !ordens?.length ? (
        <EmptyState />
      ) : (
        <div className="space-y-5">
          {grupos.map(({ titulo, items }) => (
            <section key={titulo} className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                {titulo}
                <span className="text-muted-foreground/60">({items.length})</span>
              </h2>
              <div className="space-y-2">
                {items.map((op) => (
                  <CardOP key={op.id} op={op} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function CardOP({ op }: { op: OrdemProducao }) {
  const fornadas = parseFloat(op.qtd_planejada);
  const rendimento = parseFloat(op.receita_rendimento) || 1;
  const unidade = op.receita_rendimento_unidade || "un";
  const unidadesPlanejadas = fornadas * rendimento;
  const dataLabel = formatDataOP(op.data_prevista);

  return (
    <Link
      href={`/producao/${op.id}`}
      className={cn(
        "block rounded-xl border bg-card p-4 transition-all hover:bg-accent active:scale-[0.99]",
        op.status === "finalizada" && "opacity-60",
        op.status === "cancelada" && "opacity-40"
      )}
    >
      {/* Linha 1: número + badges + data */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">
            #{String(op.numero).padStart(3, "0")}
          </span>
          <OpStatusBadge status={op.status} />
          {op.pedido_id && (
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700">
              Pedido #{op.pedido_numero}
            </span>
          )}
        </div>
        {dataLabel && (
          <span className="shrink-0 text-xs text-muted-foreground">{dataLabel}</span>
        )}
      </div>

      {/* Linha 2: nome da receita */}
      <p className="mb-1 text-base font-semibold">{op.nome_receita}</p>

      {/* Linha 3: quantidades */}
      <p className="text-sm text-muted-foreground">
        Planejado:{" "}
        <span className="font-medium text-foreground">
          {formatQuantidade(unidadesPlanejadas)} {unidade}
        </span>{" "}
        ({formatQuantidade(fornadas)} {fornadas === 1 ? "fornada" : "fornadas"})
        {op.qtd_produzida && (
          <>
            {" "}· Produzido:{" "}
            <span className="font-medium text-foreground">
              {formatQuantidade(op.qtd_produzida)} {unidade}
            </span>
          </>
        )}
      </p>

      {/* Barra de progresso — somente para "em_producao" */}
      {op.status === "em_producao" && (
        <div className="mt-3">
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div className="h-full w-1/2 rounded-full bg-primary" />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Em andamento</p>
        </div>
      )}
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
      <ChefHat className="h-10 w-10 mx-auto mb-2 text-muted-foreground/40" />
      <p className="font-medium">Nenhuma ordem de produção</p>
      <p className="text-sm mt-1">
        Planeje sua produção para controlar ingredientes e estoque
      </p>
      <Link
        href="/producao/nova"
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        <Plus className="h-4 w-4" />
        Nova OP
      </Link>
    </div>
  );
}

interface Grupo {
  titulo: string;
  items: OrdemProducao[];
}

function agruparPorData(ordens: OrdemProducao[]): Grupo[] {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const amanha = new Date(hoje);
  amanha.setDate(hoje.getDate() + 1);
  const em7 = new Date(hoje);
  em7.setDate(hoje.getDate() + 7);

  const grupos: Record<string, OrdemProducao[]> = {
    Atrasado: [],
    Hoje: [],
    Amanhã: [],
    "Próximos 7 dias": [],
    Futuro: [],
    "Sem data": [],
  };

  ordens.forEach((op) => {
    if (!op.data_prevista) {
      grupos["Sem data"].push(op);
      return;
    }
    const d = new Date(op.data_prevista + "T00:00:00");
    if (d < hoje && op.status !== "finalizada" && op.status !== "cancelada") {
      grupos["Atrasado"].push(op);
    } else if (mesmoDia(d, hoje)) {
      grupos["Hoje"].push(op);
    } else if (mesmoDia(d, amanha)) {
      grupos["Amanhã"].push(op);
    } else if (d > amanha && d <= em7) {
      grupos["Próximos 7 dias"].push(op);
    } else if (d > em7) {
      grupos["Futuro"].push(op);
    } else {
      // Já passou e está finalizada/cancelada
      grupos["Sem data"].push(op);
    }
  });

  return Object.entries(grupos)
    .filter(([, items]) => items.length > 0)
    .map(([titulo, items]) => ({ titulo, items }));
}

function mesmoDia(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}
