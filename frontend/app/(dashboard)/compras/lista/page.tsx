"use client";

import Link from "next/link";
import { ArrowLeft, Camera, ClipboardList, Loader2 } from "lucide-react";
import { EstoqueBadge } from "@/components/shared/estoque-badge";
import { useListaCompras } from "@/hooks/use-compras";
import { formatMoney, formatQuantidade } from "@/lib/utils";

export default function ListaComprasPage() {
  const { data, isLoading } = useListaCompras();
  const itens = data?.itens ?? [];

  return (
    <div className="space-y-5 pb-8">
      <Link href="/estoque" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div className="space-y-1">
        <h1 className="text-xl font-bold">Lista de compras</h1>
        <p className="text-sm text-muted-foreground">
          Ingredientes que chegaram no estoque mínimo. Sugerimos quanto comprar
          para repor com folga.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-7 w-7 animate-spin text-primary" />
        </div>
      ) : itens.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed py-16 text-center">
          <ClipboardList className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">Tudo abastecido!</p>
            <p className="text-sm text-muted-foreground">
              Nenhum ingrediente atingiu o estoque mínimo.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {itens.map((item) => (
              <div
                key={item.ingrediente_id}
                className="flex items-center justify-between gap-3 rounded-xl border p-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{item.nome}</span>
                    <EstoqueBadge status={item.status_estoque} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Tem {formatQuantidade(item.saldo)} {item.unidade} · mínimo{" "}
                    {formatQuantidade(item.estoque_minimo)} {item.unidade}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-sm font-semibold text-primary">
                    Comprar {formatQuantidade(item.quantidade_sugerida)} {item.unidade}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    ~{formatMoney(item.custo_estimado)}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-xl bg-primary/5 border border-primary/20 p-4 flex items-center justify-between">
            <span className="font-medium">Custo estimado total</span>
            <span className="font-bold text-lg text-primary">
              {formatMoney(data?.custo_total_estimado)}
            </span>
          </div>

          <Link
            href="/compras"
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Camera className="h-4 w-4" />
            Já comprei — lançar cupom
          </Link>
        </>
      )}
    </div>
  );
}
