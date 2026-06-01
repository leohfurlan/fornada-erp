"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Calendar, Trash2 } from "lucide-react";
import {
  useDeletarPedido,
  useMudarStatusPedido,
  usePedido,
} from "@/hooks/use-pedidos";
import { MoneyDisplay } from "@/components/shared/money-display";
import { PedidoStatusBadge, STATUS_LABEL } from "@/components/shared/pedido-status-badge";
import { formatDataHora, formatQuantidade } from "@/lib/utils";
import type { ApiError, StatusPedido } from "@/types";
import type { AxiosError } from "axios";

export default function PedidoDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: pedido, isLoading } = usePedido(id);
  const mudarStatus = useMudarStatusPedido(id);
  const deletar = useDeletarPedido();

  const handleStatus = async (novo: StatusPedido) => {
    if (
      (novo === "em_producao" &&
        !confirm("Ao iniciar produção, os ingredientes serão reservados no estoque. Continuar?")) ||
      (novo === "finalizado" &&
        !confirm(
          "Ao finalizar, o estoque será debitado conforme as receitas. Esta ação é registrada no histórico. Continuar?"
        )) ||
      (novo === "cancelado" && !confirm("Cancelar este pedido?"))
    ) {
      return;
    }
    try {
      await mudarStatus.mutateAsync(novo);
    } catch {
      // Erro mostrado no banner abaixo via mudarStatus.error
    }
  };

  const handleDeletar = async () => {
    if (!confirm("Tem certeza que quer excluir este pedido?")) return;
    try {
      await deletar.mutateAsync(id);
      router.push("/pedidos");
    } catch {
      // Erro tratado no banner
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-48 rounded bg-muted animate-pulse" />
        <div className="h-40 rounded-xl bg-muted animate-pulse" />
      </div>
    );
  }

  if (!pedido) {
    return <p className="text-muted-foreground">Pedido não encontrado.</p>;
  }

  const statusError = mudarStatus.error as AxiosError<ApiError> | null;
  const deletarError = deletar.error as AxiosError<ApiError> | null;
  const mensagemStatus = statusError?.response?.data?.detail;
  const mensagemDeletar = deletarError?.response?.data?.detail;

  const podeEditar = pedido.status === "orcamento";
  const podeDeletar = pedido.status === "orcamento" || pedido.status === "cancelado";

  return (
    <div className="space-y-5 pb-8">
      <div className="flex items-center justify-between">
        <Link href="/pedidos" className="flex items-center gap-1 text-sm text-muted-foreground">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
        {podeEditar && (
          <Link
            href={`/pedidos/${id}/editar`}
            className="text-sm text-primary hover:underline"
          >
            Editar
          </Link>
        )}
      </div>

      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm text-muted-foreground">
            Pedido #{String(pedido.numero).padStart(3, "0")}
          </span>
          <PedidoStatusBadge status={pedido.status} />
        </div>
        <h1 className="text-xl font-bold mt-1">{pedido.cliente_nome ?? "Sem cliente"}</h1>
        {pedido.data_entrega && (
          <p className="text-sm text-muted-foreground mt-0.5 flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            Entrega: {formatarData(pedido.data_entrega)}
          </p>
        )}
        <p className="text-xs text-muted-foreground mt-1">
          Criado em {formatDataHora(pedido.created_at)}
        </p>
      </div>

      {mensagemStatus && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/30 px-3 py-2 text-sm text-destructive">
          {mensagemStatus}
        </div>
      )}

      {/* Botões de transição */}
      {pedido.proximas_transicoes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {pedido.proximas_transicoes.map((novo) => (
            <button
              key={novo}
              type="button"
              onClick={() => handleStatus(novo)}
              disabled={mudarStatus.isPending}
              className={`rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50 ${
                novo === "cancelado"
                  ? "border border-destructive/30 text-destructive hover:bg-destructive/5"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              }`}
            >
              {mudarStatus.isPending ? "..." : `Marcar como ${STATUS_LABEL[novo].toLowerCase()}`}
            </button>
          ))}
        </div>
      )}

      {/* Itens */}
      <section className="space-y-2">
        <h2 className="font-semibold">Itens</h2>
        <div className="divide-y rounded-xl border">
          {pedido.itens.map((it) => (
            <div key={it.id} className="px-4 py-3 text-sm space-y-1">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{it.nome_receita}</p>
                  <p className="text-muted-foreground text-xs">
                    {formatQuantidade(it.quantidade)} × <MoneyDisplay value={it.preco_unitario} size="sm" />
                  </p>
                </div>
                <MoneyDisplay value={it.subtotal} size="sm" />
              </div>
              {it.observacoes && (
                <p className="text-xs text-muted-foreground italic pl-1 border-l-2 ml-1">
                  {it.observacoes}
                </p>
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between items-center pt-2 px-1 font-semibold">
          <span>Total</span>
          <MoneyDisplay value={pedido.valor_total} size="lg" className="text-primary" />
        </div>
      </section>

      {pedido.observacoes && (
        <section className="space-y-2">
          <h2 className="font-semibold">Observações</h2>
          <div className="rounded-xl border bg-card p-4 text-sm whitespace-pre-wrap leading-relaxed">
            {pedido.observacoes}
          </div>
        </section>
      )}

      {podeDeletar && (
        <div className="border-t pt-5 space-y-2">
          {mensagemDeletar && (
            <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {mensagemDeletar}
            </div>
          )}
          <button
            type="button"
            onClick={handleDeletar}
            disabled={deletar.isPending}
            className="w-full flex items-center justify-center gap-2 rounded-lg border border-destructive/30 px-4 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/5 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
            {deletar.isPending ? "Excluindo..." : "Excluir pedido"}
          </button>
        </div>
      )}
    </div>
  );
}

function formatarData(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
