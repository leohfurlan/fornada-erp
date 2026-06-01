"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Trash2 } from "lucide-react";
import { useCancelarVenda, useVenda } from "@/hooks/use-vendas";
import { CanalVendaBadge } from "@/components/shared/canal-venda-icon";
import { MoneyDisplay } from "@/components/shared/money-display";
import { formatDataHora, formatQuantidade } from "@/lib/utils";
import type { ApiError } from "@/types";
import type { AxiosError } from "axios";

export default function VendaDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: venda, isLoading } = useVenda(id);
  const cancelar = useCancelarVenda();

  const handleCancelar = async () => {
    if (
      !confirm(
        "Cancelar esta venda? O estoque dos itens vendidos será devolvido ao saldo."
      )
    ) {
      return;
    }
    try {
      await cancelar.mutateAsync(id);
      router.push("/vendas");
    } catch {
      // Erro tratado
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

  if (!venda) {
    return <p className="text-muted-foreground">Venda não encontrada.</p>;
  }

  const erro = cancelar.error as AxiosError<ApiError> | null;
  const mensagem = erro?.response?.data?.detail;

  return (
    <div className="space-y-5 pb-8">
      <Link href="/vendas" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm text-muted-foreground">
            Venda #{String(venda.numero).padStart(3, "0")}
          </span>
          <CanalVendaBadge canal={venda.canal} />
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          {formatDataHora(venda.data_venda)}
        </p>
        {venda.cliente_nome && (
          <p className="font-medium mt-1">{venda.cliente_nome}</p>
        )}
      </div>

      <section className="space-y-2">
        <h2 className="font-semibold">Itens</h2>
        <div className="divide-y rounded-xl border">
          {venda.itens.map((it) => (
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
          <MoneyDisplay value={venda.valor_total} size="lg" className="text-primary" />
        </div>
      </section>

      {venda.observacoes && (
        <section className="space-y-2">
          <h2 className="font-semibold">Observações</h2>
          <div className="rounded-xl border bg-card p-4 text-sm whitespace-pre-wrap leading-relaxed">
            {venda.observacoes}
          </div>
        </section>
      )}

      <div className="border-t pt-5 space-y-2">
        {mensagem && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {mensagem}
          </div>
        )}
        <button
          type="button"
          onClick={handleCancelar}
          disabled={cancelar.isPending}
          className="w-full flex items-center justify-center gap-2 rounded-lg border border-destructive/30 px-4 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/5 disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" />
          {cancelar.isPending ? "Cancelando..." : "Cancelar venda"}
        </button>
        <p className="text-xs text-muted-foreground text-center">
          Cancelar devolve a quantidade ao estoque de produto acabado.
        </p>
      </div>
    </div>
  );
}
