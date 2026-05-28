"use client";

import Link from "next/link";
import { ArrowLeft, Info } from "lucide-react";
import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { DecimalInput } from "@/components/shared/decimal-input";
import { MoneyDisplay } from "@/components/shared/money-display";
import { useAtualizarConfiguracaoCusto, useConfiguracaoCusto } from "@/hooks/use-configuracoes";

interface FormData {
  custo_operacional_mensal: number;
  horas_mensais: number;
  valor_hora: number;
}

export default function ConfiguracoesGeralPage() {
  const { data: config, isLoading } = useConfiguracaoCusto();
  const atualizar = useAtualizarConfiguracaoCusto();

  const { control, handleSubmit, reset, watch } = useForm<FormData>({
    defaultValues: { custo_operacional_mensal: 0, horas_mensais: 160, valor_hora: 0 },
  });

  // Quando os dados carregam do backend, popula o form
  useEffect(() => {
    if (config) {
      reset({
        custo_operacional_mensal: parseFloat(config.custo_operacional_mensal),
        horas_mensais: parseFloat(config.horas_mensais),
        valor_hora: parseFloat(config.valor_hora),
      });
    }
  }, [config, reset]);

  // Preview do custo por hora calculado em tempo real
  const watched = watch();
  const custoPorHora =
    watched.horas_mensais > 0
      ? (watched.custo_operacional_mensal / watched.horas_mensais).toFixed(2)
      : "0";

  const onSubmit = async (data: FormData) => {
    await atualizar.mutateAsync(data);
  };

  return (
    <div className="space-y-5">
      <Link
        href="/configuracoes"
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div>
        <h1 className="text-xl font-bold">Custos e Valor da Hora</h1>
        <p className="text-muted-foreground text-sm">
          Esses dados entram no cálculo do preço de cada receita
        </p>
      </div>

      <Link
        href="/configuracoes/ajuda"
        className="flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-sm text-blue-800"
      >
        <Info className="h-4 w-4 shrink-0" />
        <span>Não sabe o que preencher? Veja a página de ajuda</span>
      </Link>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="rounded-xl border p-4 space-y-2">
            <label className="text-sm font-medium">Seu valor/hora (R$)</label>
            <p className="text-xs text-muted-foreground">
              Quanto vale 1 hora do seu trabalho. Multiplicado pelo tempo ativo de cada receita.
            </p>
            <Controller
              name="valor_hora"
              control={control}
              render={({ field }) => (
                <DecimalInput value={field.value} onChange={field.onChange} placeholder="25,00" />
              )}
            />
          </div>

          <div className="rounded-xl border p-4 space-y-2">
            <label className="text-sm font-medium">Custos fixos mensais (R$)</label>
            <p className="text-xs text-muted-foreground">
              Soma de tudo que você paga todo mês: energia, gás, água, aluguel, internet, embalagens
              comuns. Não inclua ingredientes.
            </p>
            <Controller
              name="custo_operacional_mensal"
              control={control}
              render={({ field }) => (
                <DecimalInput value={field.value} onChange={field.onChange} placeholder="500,00" />
              )}
            />
          </div>

          <div className="rounded-xl border p-4 space-y-2">
            <label className="text-sm font-medium">Horas que você trabalha por mês</label>
            <p className="text-xs text-muted-foreground">
              Quantas horas você dedica em média ao negócio por mês (incluindo limpeza, organização e
              produção).
            </p>
            <Controller
              name="horas_mensais"
              control={control}
              render={({ field }) => (
                <DecimalInput value={field.value} onChange={field.onChange} placeholder="160" />
              )}
            />
          </div>

          <div className="rounded-xl bg-primary/5 border border-primary/20 p-4">
            <p className="text-xs text-muted-foreground">Custo operacional por hora (calculado)</p>
            <MoneyDisplay value={custoPorHora} size="lg" className="text-primary" />
            <p className="text-xs text-muted-foreground mt-1">
              É quanto custa cada hora que sua cozinha fica funcionando
            </p>
          </div>

          {atualizar.isError && (
            <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              Não foi possível salvar. Tente novamente.
            </div>
          )}

          {atualizar.isSuccess && (
            <div className="rounded-lg bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-800">
              Configurações salvas. Suas receitas foram recalculadas.
            </div>
          )}

          <button
            type="submit"
            disabled={atualizar.isPending}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {atualizar.isPending ? "Salvando..." : "Salvar configurações"}
          </button>
        </form>
      )}
    </div>
  );
}
