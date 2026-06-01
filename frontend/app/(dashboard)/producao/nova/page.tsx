"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { ArrowLeft, ChefHat, Info } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { DecimalInput } from "@/components/shared/decimal-input";
import { useCriarOrdemProducao } from "@/hooks/use-producao";
import { usePedidos } from "@/hooks/use-pedidos";
import { useReceitas } from "@/hooks/use-receitas";
import { formatQuantidade } from "@/lib/utils";
import type { ApiError } from "@/types";
import type { AxiosError } from "axios";

interface OPForm {
  receita_id: string;
  qtd_planejada: number;
  data_prevista: string;
  pedido_id: string;
  observacoes: string;
}

export default function NovaOrdemProducaoPage() {
  const router = useRouter();
  const { data: receitas } = useReceitas();
  // Apenas pedidos aprovados (encomendas pra produzir) aparecem no select.
  const { data: pedidos } = usePedidos({ status: "aprovado" });
  const criar = useCriarOrdemProducao();

  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<OPForm>({
    defaultValues: {
      receita_id: "",
      qtd_planejada: 1,
      data_prevista: hojeISO(),
      pedido_id: "",
      observacoes: "",
    },
  });

  const receitaId = watch("receita_id");
  const qtdPlanejada = watch("qtd_planejada");
  const receitaSelecionada = useMemo(
    () => receitas?.find((r) => r.id === receitaId),
    [receitas, receitaId]
  );

  const rendimento = receitaSelecionada
    ? parseFloat(receitaSelecionada.rendimento)
    : 0;
  const unidadeRendimento = receitaSelecionada?.rendimento_unidade ?? "un";
  // qtd_planejada é em FORNADAS. Multiplicar pelo rendimento dá as unidades finais.
  const unidadesEsperadas = qtdPlanejada * rendimento;

  const consumoIngredientes = useMemo(() => {
    if (!receitaSelecionada || qtdPlanejada <= 0) return [];
    return receitaSelecionada.ingredientes.map((ri) => ({
      nome: ri.nome_ingrediente,
      qtd: parseFloat(ri.quantidade) * qtdPlanejada,
      unidade: ri.unidade,
    }));
  }, [receitaSelecionada, qtdPlanejada]);

  const onSubmit = async (data: OPForm) => {
    if (!data.receita_id) return;
    const payload = {
      receita_id: data.receita_id,
      qtd_planejada: data.qtd_planejada,
      data_prevista: data.data_prevista || null,
      pedido_id: data.pedido_id || null,
      observacoes: data.observacoes || null,
    };
    const op = await criar.mutateAsync(payload);
    router.push(`/producao/${op.id}`);
  };

  const erro = criar.error as AxiosError<ApiError> | null;
  const mensagem = erro?.response?.data?.detail;

  return (
    <div className="space-y-5 pb-8">
      <Link href="/producao" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <h1 className="text-xl font-bold">Nova ordem de produção</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium">Receita</label>
          <select
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
            {...register("receita_id", { required: "Selecione a receita" })}
          >
            <option value="">Selecione...</option>
            {receitas?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.nome}
              </option>
            ))}
          </select>
          {errors.receita_id && (
            <p className="text-xs text-destructive">{errors.receita_id.message}</p>
          )}
          {!receitas?.length && (
            <p className="text-xs text-muted-foreground">
              Nenhuma receita cadastrada.{" "}
              <Link href="/receitas/nova" className="underline text-primary">
                Cadastrar uma agora
              </Link>
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium">Fornadas (lotes)</label>
            <p className="text-xs text-muted-foreground">
              Quantas vezes vai fazer a receita
            </p>
            <Controller
              name="qtd_planejada"
              control={control}
              rules={{ validate: (v) => v > 0 || "Maior que 0" }}
              render={({ field }) => (
                <DecimalInput value={field.value} onChange={field.onChange} placeholder="1" />
              )}
            />
            {errors.qtd_planejada && (
              <p className="text-xs text-destructive">{errors.qtd_planejada.message}</p>
            )}
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Data prevista</label>
            <input
              type="date"
              className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              {...register("data_prevista")}
            />
          </div>
        </div>

        {/* Preview de rendimento esperado */}
        {receitaSelecionada && qtdPlanejada > 0 && (
          <div className="rounded-xl bg-primary/5 border border-primary/20 p-3 flex items-center gap-2 text-sm">
            <ChefHat className="h-4 w-4 text-primary shrink-0" />
            <p>
              <span className="text-muted-foreground">Renderá </span>
              <span className="font-semibold text-primary">
                {formatQuantidade(unidadesEsperadas)} {unidadeRendimento}
              </span>
              <span className="text-muted-foreground">
                {" "}({formatQuantidade(qtdPlanejada)}{" "}
                {qtdPlanejada === 1 ? "fornada" : "fornadas"} × {formatQuantidade(rendimento)}{" "}
                {unidadeRendimento}/fornada)
              </span>
            </p>
          </div>
        )}

        <div className="space-y-1">
          <label className="text-sm font-medium">Vincular a um pedido (opcional)</label>
          <p className="text-xs text-muted-foreground">
            Se essa produção atende uma encomenda específica, escolha o pedido para rastreio
          </p>
          <select
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
            {...register("pedido_id")}
          >
            <option value="">Sem vínculo (produção para estoque)</option>
            {pedidos?.map((p) => (
              <option key={p.id} value={p.id}>
                #{String(p.numero).padStart(3, "0")} — {p.cliente_nome ?? "Sem cliente"}
              </option>
            ))}
          </select>
        </div>

        {/* Preview de consumo de ingredientes */}
        {consumoIngredientes.length > 0 && (
          <div className="rounded-xl border bg-muted/30 p-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <Info className="h-3 w-3" />
              Consumo previsto de ingredientes
            </p>
            <ul className="text-sm space-y-1">
              {consumoIngredientes.map((ing, i) => (
                <li key={i} className="flex justify-between">
                  <span className="text-muted-foreground">{ing.nome}</span>
                  <span className="font-medium">
                    {formatQuantidade(ing.qtd)} {ing.unidade}
                  </span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground italic pt-1 border-t">
              Os ingredientes serão reservados quando você iniciar a produção
            </p>
          </div>
        )}

        <div className="space-y-1">
          <label className="text-sm font-medium">Observações</label>
          <textarea
            rows={3}
            placeholder="Decoração específica, ajustes, etc."
            className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
            {...register("observacoes")}
          />
        </div>

        {mensagem && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {mensagem}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || criar.isPending}
          className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting || criar.isPending ? "Salvando..." : "Criar ordem de produção"}
        </button>
      </form>
    </div>
  );
}

function hojeISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}
