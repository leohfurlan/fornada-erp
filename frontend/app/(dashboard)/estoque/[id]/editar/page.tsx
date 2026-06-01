"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Trash2 } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import {
  useAtualizarIngrediente,
  useDeletarIngrediente,
  useIngrediente,
} from "@/hooks/use-estoque";
import { DecimalInput } from "@/components/shared/decimal-input";
import { UnidadeSelect } from "@/components/shared/unidade-select";
import { TIPOS_PRODUTO } from "@/lib/unidades";
import type { ApiError } from "@/types";
import type { AxiosError } from "axios";

interface FormData {
  nome: string;
  tipo: string;
  unidade: string;
  estoque_minimo: number;
}

export default function EditarIngredientePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: ingrediente, isLoading, error } = useIngrediente(id);
  const atualizar = useAtualizarIngrediente(id);
  const deletar = useDeletarIngrediente();

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    defaultValues: {
      nome: "",
      tipo: "ingrediente",
      unidade: "",
      estoque_minimo: 0,
    },
  });

  useEffect(() => {
    if (ingrediente) {
      reset({
        nome: ingrediente.nome,
        tipo: ingrediente.tipo,
        unidade: ingrediente.unidade,
        estoque_minimo: parseFloat(ingrediente.estoque_minimo),
      });
    }
  }, [ingrediente, reset]);

  const onSubmit = async (data: FormData) => {
    if (!data.unidade) return;
    await atualizar.mutateAsync(data);
    router.push("/estoque");
  };

  const onDeletar = async () => {
    if (!ingrediente) return;
    if (!confirm(`Tem certeza que quer excluir "${ingrediente.nome}"?`)) return;
    try {
      await deletar.mutateAsync(id);
      router.push("/estoque");
    } catch {
      // Erro já capturado pelo estado da mutation; mensagem mostrada abaixo.
    }
  };

  if (isLoading) {
    return <div className="h-40 rounded-xl bg-muted animate-pulse" />;
  }

  if (error || !ingrediente) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Ingrediente não encontrado.
      </div>
    );
  }

  const deletarError = deletar.error as AxiosError<ApiError> | null;
  const mensagemDeletar = deletarError?.response?.data?.detail;

  return (
    <div className="space-y-5">
      <Link href="/estoque" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-bold">Editar item</h1>
        <span className="font-mono text-xs text-muted-foreground">
          #{String(ingrediente.codigo).padStart(3, "0")}
        </span>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium">Tipo</label>
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
          <Controller
            name="estoque_minimo"
            control={control}
            render={({ field }) => (
              <DecimalInput value={field.value} onChange={field.onChange} placeholder="0" />
            )}
          />
        </div>

        <p className="rounded-lg bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          Para alterar a quantidade em estoque ou o custo, registre uma entrada de compra na
          tela de estoque.
        </p>

        {atualizar.isError && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            Não foi possível salvar as alterações. Tente novamente.
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || atualizar.isPending}
          className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting || atualizar.isPending ? "Salvando..." : "Salvar alterações"}
        </button>
      </form>

      <div className="border-t pt-5 space-y-3">
        <h2 className="text-sm font-medium text-destructive">Zona de risco</h2>
        {mensagemDeletar && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {mensagemDeletar}
          </div>
        )}
        <button
          type="button"
          onClick={onDeletar}
          disabled={deletar.isPending}
          className="w-full flex items-center justify-center gap-2 rounded-lg border border-destructive/30 px-4 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/5 disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" />
          {deletar.isPending ? "Excluindo..." : "Excluir item"}
        </button>
      </div>
    </div>
  );
}
