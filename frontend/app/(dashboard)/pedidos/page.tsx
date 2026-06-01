"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Calendar, Plus, Search, ShoppingCart } from "lucide-react";
import { usePedidos } from "@/hooks/use-pedidos";
import { MoneyDisplay } from "@/components/shared/money-display";
import { PedidoStatusBadge, STATUS_LABEL } from "@/components/shared/pedido-status-badge";
import type { StatusPedido } from "@/types";

const FILTROS_STATUS: { value: StatusPedido | ""; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "orcamento", label: STATUS_LABEL.orcamento },
  { value: "aprovado", label: STATUS_LABEL.aprovado },
  { value: "em_producao", label: STATUS_LABEL.em_producao },
  { value: "finalizado", label: STATUS_LABEL.finalizado },
  { value: "entregue", label: STATUS_LABEL.entregue },
];

export default function PedidosPage() {
  const [filtroStatus, setFiltroStatus] = useState<StatusPedido | "">("");
  const [busca, setBusca] = useState("");

  const { data: pedidos, isLoading, error } = usePedidos(
    filtroStatus ? { status: filtroStatus } : {}
  );

  const filtrados = useMemo(() => {
    if (!pedidos) return [];
    const q = busca.trim().toLowerCase();
    if (!q) return pedidos;
    return pedidos.filter(
      (p) =>
        p.cliente_nome?.toLowerCase().includes(q) ||
        String(p.numero) === q ||
        p.itens.some((i) => i.nome_receita.toLowerCase().includes(q))
    );
  }, [pedidos, busca]);

  if (error) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar os pedidos.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Pedidos</h1>
        <Link
          href="/pedidos/novo"
          className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
        >
          <Plus className="h-4 w-4" />
          Novo
        </Link>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Buscar por número, cliente ou receita..."
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          className="w-full rounded-lg border pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
        {FILTROS_STATUS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFiltroStatus(f.value)}
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filtroStatus === f.value
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
            <div key={i} className="h-24 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !pedidos?.length ? (
        <EmptyState />
      ) : filtrados.length === 0 ? (
        <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          Nenhum pedido encontrado com esses filtros
        </div>
      ) : (
        <div className="space-y-2">
          {filtrados.map((p) => (
            <Link
              key={p.id}
              href={`/pedidos/${p.id}`}
              className="block rounded-xl border bg-card p-4 hover:bg-accent transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-muted-foreground">
                      #{String(p.numero).padStart(3, "0")}
                    </span>
                    <PedidoStatusBadge status={p.status} />
                    <PrazoBadge data={p.data_entrega} status={p.status} />
                  </div>
                  <p className="font-medium mt-1">
                    {p.cliente_nome ?? "Sem cliente"}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {p.itens.map((i) => i.nome_receita).join(", ")}
                  </p>
                  {p.data_entrega && (
                    <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      Entrega: {formatarData(p.data_entrega)}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <MoneyDisplay value={p.valor_total} size="md" />
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
      <p className="font-medium">Nenhum pedido ainda</p>
      <p className="text-sm mt-1">Registre seu primeiro pedido e acompanhe a produção</p>
      <Link
        href="/pedidos/novo"
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        <Plus className="h-4 w-4" />
        Novo pedido
      </Link>
    </div>
  );
}

function formatarData(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function PrazoBadge({
  data,
  status,
}: {
  data: string | null;
  status: StatusPedido;
}) {
  if (!data || status === "entregue" || status === "cancelado") return null;
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const entrega = new Date(data + "T00:00:00");
  const diff = Math.floor((entrega.getTime() - hoje.getTime()) / 86400000);

  if (diff < 0) {
    return (
      <span className="rounded-full bg-red-100 text-red-800 px-2 py-0.5 text-xs font-medium">
        Atrasado
      </span>
    );
  }
  if (diff <= 2) {
    return (
      <span className="rounded-full bg-orange-100 text-orange-800 px-2 py-0.5 text-xs font-medium">
        {diff === 0 ? "Hoje" : diff === 1 ? "Amanhã" : `Em ${diff} dias`}
      </span>
    );
  }
  return null;
}
