"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useReceitas } from "@/hooks/use-receitas";
import { MoneyDisplay } from "@/components/shared/money-display";
import { formatQuantidade } from "@/lib/utils";

export default function ReceitasPage() {
  const { data: receitas, isLoading, error } = useReceitas();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-32 rounded bg-muted animate-pulse" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar as receitas. Tente novamente.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Receitas</h1>
        <Link
          href="/receitas/nova"
          className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
        >
          <Plus className="h-4 w-4" />
          Nova receita
        </Link>
      </div>

      {!receitas?.length ? (
        <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
          <p className="font-medium">Nenhuma receita ainda</p>
          <p className="text-sm mt-1">Crie sua primeira receita e descubra o custo real</p>
          <Link
            href="/receitas/nova"
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            Criar receita
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {receitas.map((receita) => (
            <Link
              key={receita.id}
              href={`/receitas/${receita.id}`}
              className="block rounded-xl border bg-card p-4 hover:bg-accent transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{receita.nome}</p>
                  <p className="text-sm text-muted-foreground">{receita.categoria}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Rende {formatQuantidade(receita.rendimento)} {receita.rendimento_unidade}
                  </p>
                </div>
                {receita.custo && (
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Preço sugerido</p>
                    <MoneyDisplay value={receita.custo.preco_recomendado} size="lg" className="text-primary" />
                    <p className="text-xs text-muted-foreground">
                      Custo:{" "}
                      <MoneyDisplay value={receita.custo.custo_por_unidade} size="sm" />
                      /un
                    </p>
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
