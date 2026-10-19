"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMudarStatusOP } from "@/hooks/use-producao";
import { api } from "@/lib/api";
import { getSupportSession } from "@/lib/admin-session";
import { toDateKey, formatHora } from "@/lib/agenda";
import { formatQuantidade, formatDataHora } from "@/lib/utils";
import { errorMessage } from "@/lib/validation";
import { useAuthStore } from "@/stores/use-auth-store";
import { DecimalInput } from "@/components/shared/decimal-input";
import { OpStatusBadge } from "@/components/shared/op-status-badge";
import type { IfoodMonitor } from "@/hooks/use-ifood-monitor";
import type { AgendaItem, OrdemProducao, Venda } from "@/types";

const actionClass = "inline-flex min-h-12 items-center justify-center rounded-xl border px-4 font-semibold hover:bg-muted disabled:opacity-40";

function useKitchenResource<T>(resource: string, path: string, params?: Record<string, string>) {
  const user = useAuthStore(state => state.usuario);
  const authenticated = useAuthStore(state => state.isAuthenticated);
  const support = getSupportSession();
  return useQuery<T>({
    queryKey: ["cozinha-operacao", user?.tenant_id, user?.id, support?.id, resource, params],
    enabled: authenticated && Boolean(user),
    queryFn: async () => (await api.get<T>(path, { params })).data,
    refetchInterval: 15000,
    retry: 1,
  });
}

/** Read-only overview: receiving an order never starts production or acknowledges it. */
export function KitchenDayOverview({ recipeOpen }: { recipeOpen: boolean }) {
  const [today, setToday] = useState(() => toDateKey(new Date()));
  useEffect(() => {
    const timer = window.setInterval(() => setToday(toDateKey(new Date())), 60000);
    return () => window.clearInterval(timer);
  }, []);
  const agenda = useKitchenResource<AgendaItem[]>("agenda", "/agenda", { view: "dia", data: today });
  const sales = useKitchenResource<Venda[]>("vendas", "/vendas", { data_de: today, data_ate: today });
  const ifood = useKitchenResource<IfoodMonitor>("ifood", "/integracoes/ifood/monitor");
  const activities = [...(agenda.data ?? [])].sort((a, b) => (a.hora_inicio ?? "99").localeCompare(b.hora_inicio ?? "99") || a.titulo.localeCompare(b.titulo));
  const incoming = (sales.data ?? []).filter(sale => sale.canal === "whatsapp" || sale.canal === "ifood")
    .sort((a, b) => b.data_venda.localeCompare(a.data_venda));

  return <details open={!recipeOpen} className="rounded-2xl border bg-card p-5 sm:p-6">
    <summary className="min-h-12 cursor-pointer text-xl font-semibold">Programação do dia e pedidos
      <span aria-live="polite" className="mt-2 block text-sm font-normal text-muted-foreground">{ifood.data ? `Pedidos iFood: ${ifood.data.pedidos.length}` : "Consultando iFood…"} · {sales.data ? `Vendas de hoje: ${incoming.length}` : "Consultando vendas…"}</span>
    </summary>
    <nav aria-label="Acessos da cozinha" className="mt-3 flex flex-wrap gap-2">
      <Link className={actionClass} href="/agenda">Abrir agenda</Link>
      <Link className={actionClass} href="/producao">Programação de produção</Link>
      <Link className={actionClass} href="/pedidos">Pedidos</Link>
      <Link className={actionClass} href="/vendas">Vendas</Link>
    </nav>
    <div className="mt-5 grid gap-6 md:grid-cols-2">
      <section aria-label="Agenda de hoje" className="min-w-0">
        <h2 className="text-lg font-semibold">Hoje · {today.split("-").reverse().join("/")}</h2>
        {agenda.isPending && <p role="status">Carregando programação…</p>}
        {agenda.isError ? <p role="alert">Não foi possível atualizar a agenda.</p> : <>
          {!agenda.isPending && !activities.length && <p className="mt-3 text-muted-foreground">Nenhuma atividade agendada para hoje.</p>}
          <ul className="mt-3 space-y-2">{activities.map(item => <li key={item.id} className="rounded-xl border p-3">
            <p className={item.concluido ? "line-through" : "font-semibold"}>{item.hora_inicio ? `${formatHora(item.hora_inicio)} · ` : ""}{item.titulo}</p>
            <p className="text-sm text-muted-foreground">{item.concluido ? "Concluída" : "Pendente"}</p>
            {item.ordem_producao_id && <Link className={actionClass} href={`/producao/${item.ordem_producao_id}`}>Ver OP #{item.numero_op}</Link>}
          </li>)}</ul>
        </>}
      </section>
      <section aria-label="Pedidos e vendas recebidos" className="min-w-0 space-y-3">
        <h2 className="text-lg font-semibold">Pedidos e vendas recebidos</h2>
        {ifood.isPending && <p role="status">Consultando pedidos iFood…</p>}
        {ifood.isError ? <p role="alert">Não foi possível atualizar os pedidos iFood.</p> : <>
          {ifood.data?.erro && <p role="alert">O monitor iFood informou uma falha. Os pedidos abaixo podem estar desatualizados.</p>}
          {ifood.data && !ifood.data.habilitado && <p className="text-sm text-muted-foreground">Recepção iFood desativada.</p>}
          <ul className="space-y-2">{ifood.data?.pedidos.map(order => <li key={order.id} className="rounded-xl border p-3">
            <p className="font-semibold">iFood #{order.snapshot.displayId}{order.snapshot.isTest ? " · Pedido de teste" : ""}</p>
            <p className="text-sm text-muted-foreground">Último evento: {order.ultimo_evento}{order.evento_em ? ` · ${formatDataHora(order.evento_em)}` : ""}</p>
            <ul>{order.snapshot.items.map((item, index) => <li key={index}>{formatQuantidade(item.quantity)} × {item.name}</li>)}</ul>
          </li>)}</ul>
        </>}
        {sales.isPending && <p role="status">Consultando vendas de hoje…</p>}
        {sales.isError ? <p role="alert">Não foi possível atualizar as vendas.</p> : <>
          {!sales.isPending && !incoming.length && <p className="text-sm text-muted-foreground">Nenhuma venda iFood ou WhatsApp registrada hoje.</p>}
          <ul className="space-y-2">{incoming.map(sale => <li key={sale.id} className="rounded-xl border p-3">
            <Link className="inline-flex min-h-12 items-center font-semibold text-primary" href={`/vendas/${sale.id}`}>{sale.canal === "whatsapp" ? "WhatsApp" : "iFood"} · Venda #{sale.numero}</Link>
            <ul>{sale.itens.map(item => <li key={item.id}>{formatQuantidade(item.quantidade)} × {item.nome_receita}</li>)}</ul>
          </li>)}</ul>
        </>}
      </section>
    </div>
  </details>;
}

export function KitchenProductionQueue({ search, recipeOpen, disabled, onOpen }: {
  search: string; recipeOpen: boolean; disabled: boolean; onOpen: (recipeId: string) => void;
}) {
  const orders = useKitchenResource<OrdemProducao[]>("ordens", "/producao/ordens");
  const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  const term = normalize(search.trim());
  const open = (orders.data ?? []).filter(op => (op.status === "planejada" || op.status === "em_producao") &&
    (!term || normalize(`${op.nome_receita} OP #${op.numero}`).includes(term)))
    .sort((a, b) => (a.data_prevista ?? "9999").localeCompare(b.data_prevista ?? "9999") || a.numero - b.numero);
  return <details open={!recipeOpen || Boolean(term)} className="mt-5 rounded-xl border p-4">
    <summary className="min-h-12 cursor-pointer text-lg font-semibold">Ordens de produção abertas{orders.data ? ` (${open.length})` : ""}</summary>
    <p className="mt-2 text-sm text-muted-foreground">Escolha primeiro uma OP ou busque outra receita abaixo. Abrir a receita não altera o status da produção.</p>
    {orders.isPending && <p role="status">Carregando ordens de produção…</p>}
    {orders.isError ? <p role="alert">Não foi possível atualizar as OPs. <Link className="underline" href="/producao">Consultar produção</Link></p> : <>
      {!orders.isPending && !open.length && <p className="mt-3 text-muted-foreground">Nenhuma OP aberta{term ? " para esta busca" : ""}.</p>}
      <div className="mt-3 space-y-3">{open.map(op => <ProductionOrder key={op.id} op={op} disabled={disabled} onOpen={onOpen} />)}</div>
    </>}
  </details>;
}

function ProductionOrder({ op, disabled, onOpen }: { op: OrdemProducao; disabled: boolean; onOpen: (recipeId: string) => void }) {
  const cache = useQueryClient();
  const mutation = useMudarStatusOP(op.id);
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [quantity, setQuantity] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const changeStatus = async (status: "em_producao" | "finalizada") => {
    if (disabled || pending.current) return;
    if (status === "em_producao" && !window.confirm(`Iniciar OP #${op.numero}? Os materiais e componentes prontos serão reservados no estoque.`)) return;
    if (status === "finalizada" && (!Number.isFinite(quantity) || quantity < 0)) {
      setError("Informe uma quantidade produzida maior ou igual a zero."); return;
    }
    pending.current = true; setBusy(true); setError(null); setNotice(null);
    try {
      await mutation.mutateAsync({ status, ...(status === "finalizada" ? { qtd_produzida: quantity } : {}) });
      setFinishing(false);
      setNotice(`OP #${op.numero} ${status === "em_producao" ? "iniciada" : "finalizada"}.`);
    } catch (cause) {
      setError(errorMessage(cause, "Não foi possível alterar a OP. Atualize e confira o status antes de tentar novamente."));
    } finally {
      await Promise.all(["cozinha-operacao", "agenda"].map(key => cache.invalidateQueries({ queryKey: [key] })));
      pending.current = false; setBusy(false);
    }
  };
  return <article aria-label={`OP ${op.numero}`} className="rounded-xl border bg-background p-4">
    <div className="flex flex-wrap items-center gap-2"><strong>OP #{op.numero} · {op.nome_receita}</strong><OpStatusBadge status={op.status} /></div>
    <p className="mt-2 text-base text-muted-foreground">{formatQuantidade(op.qtd_planejada)} fornada(s) · {formatQuantidade(Number(op.qtd_planejada) * Number(op.receita_rendimento))} {op.receita_rendimento_unidade}{op.data_prevista ? ` · ${op.data_prevista.split("-").reverse().join("/")}` : " · Sem data"}</p>
    {op.pedido_numero != null && <p>Pedido #{op.pedido_numero}</p>}
    <div className="mt-3 flex flex-wrap gap-2">
      <button type="button" disabled={disabled || busy} className={actionClass} onClick={() => onOpen(op.receita_id)}>Abrir receita da OP #{op.numero}</button>
      {op.proximas_transicoes.includes("em_producao") && <button type="button" disabled={disabled || busy} className={actionClass} onClick={() => void changeStatus("em_producao")}>Iniciar OP #{op.numero}</button>}
      {op.proximas_transicoes.includes("finalizada") && <button type="button" disabled={disabled || busy} className={actionClass} onClick={() => { setQuantity(Number(op.qtd_planejada) * Number(op.receita_rendimento)); setFinishing(true); setError(null); }}>Finalizar OP #{op.numero}</button>}
      <Link className={actionClass} href={`/producao/${op.id}`}>Detalhes da OP #{op.numero}</Link>
    </div>
    {finishing && <form className="mt-4 space-y-3 rounded-xl border p-4" onSubmit={event => { event.preventDefault(); void changeStatus("finalizada"); }}>
      <label className="block font-semibold" htmlFor={`produzido-${op.id}`}>Quantidade produzida ({op.receita_rendimento_unidade})</label>
      <DecimalInput id={`produzido-${op.id}`} value={quantity} onChange={setQuantity} disabled={disabled || busy} className="min-h-12 bg-background text-lg" />
      <p className="text-sm text-muted-foreground">A confirmação consome os materiais reservados e registra a quantidade real no estoque de produtos prontos.</p>
      <div className="flex flex-wrap gap-2"><button type="submit" disabled={disabled || busy} className={actionClass}>Confirmar finalização da OP #{op.numero}</button><button type="button" disabled={busy} className={actionClass} onClick={() => setFinishing(false)}>Continuar preparando</button></div>
    </form>}
    {error && <p role="alert" className="mt-3 text-destructive">{error}</p>}
    {notice && <p role="status" className="mt-3 text-success">{notice}</p>}
  </article>;
}
