"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useForm, Controller } from "react-hook-form";
import { useCriarIngrediente } from "@/hooks/use-estoque";
import { DecimalInput } from "@/components/shared/decimal-input";
import { UnidadeSelect } from "@/components/shared/unidade-select";
import { TIPOS_PRODUTO } from "@/lib/unidades";

interface FormData {
  nome: string;
  tipo: string;
  unidade: string;
  estoque_minimo: number;
  estoque_inicial: number;
  custo_inicial: number;
}

export default function NovoIngredientePage() {
  const router = useRouter();
  const criar = useCriarIngrediente();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    defaultValues: {
      nome: "",
      tipo: "ingrediente",
      unidade: "",
      estoque_minimo: 0,
      estoque_inicial: 0,
      custo_inicial: 0,
    },
  });

  const onSubmit = async (data: FormData) => {
    if (!data.unidade) return;
    await criar.mutateAsync(data);
    router.push("/estoque");
  };

  return (
    <div className="space-y-5">
      <Link href="/estoque" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <h1 className="text-xl font-bold">Novo item de estoque</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium">Tipo</label>
          <p className="text-xs text-muted-foreground">
            Classifica o item para facilitar busca e relatórios
          </p>
          <select
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
            {...register("tipo", { required: "Selecione o tipo" })}
          >
            {TIPOS_PRODUTO.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">Descrição</label>
          <input
            type="text"
            placeholder="Ex: Farinha de trigo tipo 1"
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            {...register("nome", { required: "Informe a descrição" })}
          />
          {errors.nome && <p className="text-xs text-destructive">{errors.nome.message}</p>}
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">Unidade de medida</label>
          <Controller
            name="unidade"
            control={control}
            rules={{ required: "Selecione a unidade" }}
            render={({ field }) => (
              <UnidadeSelect tipo="medida" value={field.value} onChange={field.onChange} />
            )}
          />
          {errors.unidade && (
            <p className="text-xs text-destructive">{errors.unidade.message}</p>
          )}
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">Estoque mínimo</label>
          <p className="text-xs text-muted-foreground">
            Você recebe um alerta quando o estoque ficar abaixo deste valor
          </p>
          <Controller
            name="estoque_minimo"
            control={control}
            render={({ field }) => (
              <DecimalInput value={field.value} onChange={field.onChange} placeholder="0" />
            )}
          />
        </div>

        <div className="rounded-xl border p-4 space-y-3">
          <p className="text-sm font-medium">Estoque inicial (opcional)</p>
          <p className="text-xs text-muted-foreground">
            Se você já tem este ingrediente em casa, informe abaixo
          </p>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Quantidade</label>
              <Controller
                name="estoque_inicial"
                control={control}
                render={({ field }) => (
                  <DecimalInput value={field.value} onChange={field.onChange} placeholder="0" />
                )}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Custo por unidade (R$)</label>
              <Controller
                name="custo_inicial"
                control={control}
                render={({ field }) => (
                  <DecimalInput value={field.value} onChange={field.onChange} placeholder="0,00" />
                )}
              />
            </div>
          </div>
        </div>

        {criar.isError && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            Não foi possível salvar o ingrediente. Tente novamente.
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || criar.isPending}
          className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting || criar.isPending ? "Salvando..." : "Salvar ingrediente"}
        </button>
      </form>
    </div>
  );
}
