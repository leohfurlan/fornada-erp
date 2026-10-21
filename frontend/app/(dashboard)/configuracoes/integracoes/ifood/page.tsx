"use client";

import { useIfoodMonitor, type IfoodOption } from "@/hooks/use-ifood-monitor";
import { formatMoney, formatQuantidade } from "@/lib/utils";

function date(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" }) : "Ainda não registrado";
}

const deliveryStates: Record<string, string> = {
  pendente: "Aguardando envio", enviando: "Enviando", enviado: "Envio aceito pelo WhatsApp",
  incerto: "Envio não confirmado — confira no WhatsApp", erro: "Falha no envio",
  cancelado: "Pedido cancelado antes do envio", desabilitado: "Desativado",
};

function Options({ options, depth = 0 }: { options: IfoodOption[]; depth?: number }) {
  if (!options.length || depth >= 10) return null;
  return <ul className="ml-3 space-y-1 border-l pl-3 text-sm text-muted-foreground">
    {options.map((option, index) => <li key={index}>
      {formatQuantidade(option.quantity)} × {option.name}
      <Options options={option.options} depth={depth + 1} />
    </li>)}
  </ul>;
}

export default function IfoodPage() {
  const { data, isLoading, isError, refetch } = useIfoodMonitor();
  if (isLoading) return <p role="status">Carregando monitor iFood…</p>;
  if (isError || !data) return <div role="alert" className="space-y-3">
    <p>Não foi possível consultar o monitor iFood.</p>
    <button className="rounded-lg border px-4 py-2" onClick={() => refetch()}>Tentar novamente</button>
  </div>;
  const stale = !data.ultima_consulta || Date.now() - Date.parse(data.ultima_consulta) > Math.max(90000, data.intervalo_segundos * 3000);
  const connection = !data.habilitado ? "Monitor não habilitado nesta conta" : data.erro
    ? "Comunicação com falha" : stale ? "Aguardando comunicação" : "Recebendo eventos de teste";
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h1 className="text-xl font-bold">Monitor iFood</h1>
        <p className="text-sm text-muted-foreground">Ambiente de teste · somente observação</p></div>
      <button className="rounded-lg border px-4 py-2" onClick={() => refetch()}>Atualizar tela</button>
    </div>
    <p className="rounded-xl border bg-muted/30 p-3 text-sm">Pedidos exibidos aqui são testes. Estoque, vendas e aceitação de pedidos permanecem sem alteração.</p>
    <section aria-label="Conexão" className="space-y-2 rounded-xl border p-4">
      <p role="status" className="font-medium">{connection}</p>
      {data.loja_nome && <p>{data.loja_nome}</p>}
      {data.merchant_id && <p className="break-all text-xs text-muted-foreground">Loja: {data.merchant_id}</p>}
      <p className="text-sm">Última consulta: {date(data.ultima_consulta)}</p>
      <p className="text-sm">Último evento recebido: {date(data.ultima_recepcao)}</p>
      <p className="text-sm">Eventos aguardando detalhes: {data.eventos_pendentes}</p>
      <p className="text-sm">Aviso na tela: {data.alertas_habilitados ? "Ativo enquanto o Fornada estiver aberto" : "Desativado"}</p>
      <p className="text-sm">WhatsApp: {data.whatsapp_habilitado ? `Ativo · número com final ${data.whatsapp_final}` : "Desativado"}</p>
      {data.erro && <p role="alert" className="text-sm text-destructive">{data.erro}</p>}
    </section>
    <section aria-label="Pedidos observados" className="space-y-3">
      <h2 className="font-semibold">Pedidos observados ({data.pedidos.length})</h2>
      {!data.pedidos.length && <p className="text-sm text-muted-foreground">Nenhum pedido observado. Após habilitar o monitor, gere um pedido na loja de teste do iFood.</p>}
      {data.pedidos.map((order) => <article key={order.id} id={`pedido-${order.snapshot.id}`} className="scroll-mt-20 space-y-3 rounded-xl border p-4">
        <div className="flex flex-wrap justify-between gap-2"><h3 className="font-semibold">Pedido {order.snapshot.displayId} · teste</h3>
          <strong>{formatMoney(order.snapshot.total.orderAmount)}</strong></div>
        <p className="text-sm">Último evento: {order.ultimo_evento} · {date(order.evento_em)}</p>
        {order.aviso_whatsapp && <p className="text-sm">Aviso WhatsApp: {deliveryStates[order.aviso_whatsapp] ?? "Estado indisponível"}</p>}
        <p className="break-all text-xs text-muted-foreground">ID: {order.snapshot.id}</p>
        <ul className="space-y-2">{order.snapshot.items.map((item, index) => <li key={index}>
          <div className="flex items-start justify-between gap-3 text-sm"><span>{formatQuantidade(item.quantity)} × {item.name}</span>
            <span className="shrink-0">{item.totalPrice == null ? "Valor não informado" : formatMoney(item.totalPrice)}</span></div>
          <Options options={item.options} />
        </li>)}</ul>
        <dl className="grid grid-cols-2 gap-1 border-t pt-2 text-sm">
          <dt>Produtos</dt><dd className="text-right">{formatMoney(order.snapshot.total.subTotal)}</dd>
          <dt>Entrega</dt><dd className="text-right">{formatMoney(order.snapshot.total.deliveryFee)}</dd>
          <dt>Taxas adicionais</dt><dd className="text-right">{formatMoney(order.snapshot.total.additionalFees)}</dd>
          <dt>Descontos</dt><dd className="text-right">{formatMoney(order.snapshot.total.benefits)}</dd>
        </dl>
      </article>)}
    </section>
    <section aria-label="Eventos recebidos" className="space-y-2">
      <h2 className="font-semibold">Eventos recentes</h2>
      {data.eventos.map((event) => <div key={event.event_id} className="rounded-xl border p-3 text-sm">
        <p>{event.codigo} · {date(event.ocorrido_em)}</p>
        <p className="text-muted-foreground">{event.ack_em ? "Recebimento confirmado ao iFood" : "Confirmação de recebimento pendente"}</p>
        {event.erro && <p role="alert" className="text-destructive">{event.erro}</p>}
      </div>)}
    </section>
  </div>;
}
