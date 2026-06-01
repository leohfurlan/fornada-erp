"use client";

import Link from "next/link";
import { useState } from "react";
import { Plus, ShoppingCart } from "lucide-react";
import { useVendas } from "@/hooks/use-vendas";
import { CanalVendaBadge, CANAIS_VENDA } from "@/components/shared/canal-venda-icon";
import { MoneyDisplay } from "@/components/shared/money-display";
import { formatDataHora, formatQuantidade } from "@/lib/utils";
import type { CanalVenda } from "@/types";

const FILTROS_CANAL: { value: CanalVenda | ""; label: string }[] = [
  { value: "", label: "Todos" },
  ...CANAIS_VENDA.map((c) => ({ value: c.value, label: c.label })),
];

export default function VendasPage() {
  const [filtroCanal, setFiltroCanal] = useState<CanalVenda | "">("");
  const { data: vendas, isLoading, error } = useVendas(
    filtroCanal ? { canal: filtroCanal } : {}
  );

  const totalPeriodo =
    vendas?.reduce((sum, v) => sum + parseFloat(v.valor_total), 0) ?? 0;

  if (error) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar as vendas.
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Vendas</h1>
        <Link
          href="/vendas/nova"
          className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
        >
          <Plus className="h-4 w-4" />
          Nova
        </Link>
      </div>

      <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
        {FILTROS_CANAL.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFiltroCanal(f.value)}
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filtroCanal === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {!!vendas?.length && (
        <div className="rounded-xl bg-primary/5 border border-primary/20 p-3 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Total {filtroCanal ? "do canal" : "do período"}
          </span>
          <MoneyDisplay value={totalPeriodo} size="lg" className="text-primary" />
        </div>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !vendas?.length ? (
        <EmptyState />
      ) : (
        <div className="space-y-2">
          {vendas.map((v) => (
            <Link
              key={v.id}
              href={`/vendas/${v.id}`}
              className="block rounded-xl border bg-card p-4 hover:bg-accent transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-muted-foreground">
                      #{String(v.numero).padStart(3, "0")}
                    </span>
                    <CanalVendaBadge canal={v.canal} />
                  </div>
                  <p className="text-sm mt-1 truncate">
                    {v.itens
                      .map((i) => `${formatQuantidade(i.quantidade)}× ${i.nome_receita}`)
                      .join(", ")}
                  </p>
                  {v.cliente_nome && (
                    <p className="text-xs text-muted-foreground mt-0.5">{v.cliente_nome}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatDataHora(v.data_venda)}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <MoneyDisplay value={v.valor_total} size="md" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
      <ShoppingCart className="h-10 w-10 mx-auto mb-2 text-muted-foreground/40" />
      <p className="font-medium">Nenhuma venda registrada</p>
      <p className="text-sm mt-1">Anote suas vendas por canal: WhatsApp, loja, iFood...</p>
      <Link
        href="/vendas/nova"
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        <Plus className="h-4 w-4" />
        Nova venda
      </Link>
    </div>
  );
}
