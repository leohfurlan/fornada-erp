"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Clock, Copy, Pencil, Trash2 } from "lucide-react";
import { useDeletarReceita, useDuplicarReceita, useReceita } from "@/hooks/use-receitas";
import { CustoCard } from "@/components/shared/custo-card";
import { MoneyDisplay } from "@/components/shared/money-display";
import { formatDataHora, formatMinutos, formatQuantidade } from "@/lib/utils";

export default function ReceitaPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: receita, isLoading } = useReceita(id);
  const deletar = useDeletarReceita();
  const duplicar = useDuplicarReceita();

  const handleDeletar = async () => {
    if (!confirm("Tem certeza que quer remover esta receita?")) return;
    await deletar.mutateAsync(id);
    router.push("/receitas");
  };

  const handleDuplicar = async () => {
    const nova = await duplicar.mutateAsync(id);
    router.push(`/receitas/${nova.id}/editar`);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-48 rounded bg-muted animate-pulse" />
        <div className="h-40 rounded-xl bg-muted animate-pulse" />
      </div>
    );
  }

  if (!receita) {
    return <p className="text-muted-foreground">Receita não encontrada.</p>;
  }

  return (
    <div className="space-y-5 pb-8">
      <div className="flex items-center justify-between">
        <Link href="/receitas" className="flex items-center gap-1 text-sm text-muted-foreground">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
        <div className="flex items-center gap-1">
          <button
            onClick={handleDuplicar}
            disabled={duplicar.isPending}
            className="flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-50"
            aria-label="Duplicar receita"
            title="Cria uma cópia desta receita para editar"
          >
            <Copy className="h-3.5 w-3.5" />
            {duplicar.isPending ? "Duplicando..." : "Duplicar"}
          </button>
          <Link
            href={`/receitas/${id}/editar`}
            className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Pencil className="h-3.5 w-3.5" />
            Editar
          </Link>
          <button
            onClick={handleDeletar}
            disabled={deletar.isPending}
            className="p-2 rounded-lg hover:bg-destructive/10 text-destructive"
            aria-label="Remover receita"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div>
        <h1 className="text-xl font-bold">{receita.nome}</h1>
        <p className="text-muted-foreground text-sm">{receita.categoria}</p>
        <p className="text-sm mt-0.5">
          Rende {formatQuantidade(receita.rendimento)} {receita.rendimento_unidade}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Última atualização: {formatDataHora(receita.updated_at)}
        </p>
      </div>

      {receita.custo && <CustoCard custo={receita.custo} />}

      {/* Ingredientes */}
      <section className="space-y-2">
        <h2 className="font-semibold">Ingredientes</h2>
        <div className="divide-y rounded-xl border">
          {receita.ingredientes.map((item) => (
            <div key={item.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <div>
                <p className="font-medium">{item.nome_ingrediente}</p>
                <p className="text-muted-foreground">
                  {formatQuantidade(item.quantidade)} {item.unidade}
                </p>
              </div>
              <MoneyDisplay value={item.custo_total} size="sm" className="text-muted-foreground" />
            </div>
          ))}
        </div>
      </section>

      {/* Etapas */}
      <section className="space-y-2">
        <h2 className="font-semibold">Etapas</h2>
        <div className="divide-y rounded-xl border">
          {receita.etapas.map((etapa, i) => (
            <div key={etapa.id} className="flex items-center gap-3 px-4 py-3 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
                {i + 1}
              </span>
              <div className="flex-1">
                <p className="font-medium">{etapa.nome}</p>
                <p className="text-muted-foreground text-xs">
                  {etapa.tipo_mao_obra === "direta" ? "Mão de obra direta" : "Mão de obra indireta"}
                </p>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span className="text-xs">{formatMinutos(etapa.duracao_minutos)}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Modo de preparo */}
      {receita.modo_preparo ? (
        <section className="space-y-2">
          <h2 className="font-semibold">Modo de preparo</h2>
          <div className="rounded-xl border bg-card p-4 text-sm whitespace-pre-wrap leading-relaxed">
            {receita.modo_preparo}
          </div>
        </section>
      ) : (
        <section className="space-y-2">
          <h2 className="font-semibold">Modo de preparo</h2>
          <Link
            href={`/receitas/${id}/editar`}
            className="block rounded-xl border border-dashed p-4 text-center text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors"
          >
            Adicionar passo a passo para consultar durante a produção
          </Link>
        </section>
      )}
    </div>
  );
}
