"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Plus, Trash2, Clock } from "lucide-react";
import { useForm, Controller } from "react-hook-form";
import { cn, formatMinutos } from "@/lib/utils";
import { DecimalInput } from "@/components/shared/decimal-input";
import {
  useCriarEtapaPadrao,
  useDeletarEtapaPadrao,
  useEtapasPadrao,
} from "@/hooks/use-configuracoes";

interface FormData {
  nome: string;
  tipo_mao_obra: "direta" | "indireta";
  duracao_minutos_default: number;
}

export default function ConfiguracoesEtapasPage() {
  const { data: etapas, isLoading } = useEtapasPadrao();
  const criar = useCriarEtapaPadrao();
  const deletar = useDeletarEtapaPadrao();
  const [mostrandoForm, setMostrandoForm] = useState(false);

  const { control, register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    defaultValues: { nome: "", tipo_mao_obra: "direta", duracao_minutos_default: 30 },
  });

  const onSubmit = async (data: FormData) => {
    await criar.mutateAsync(data);
    reset({ nome: "", tipo_mao_obra: "direta", duracao_minutos_default: 30 });
    setMostrandoForm(false);
  };

  const handleDeletar = async (id: string, nome: string) => {
    if (!confirm(`Remover a etapa "${nome}"?`)) return;
    await deletar.mutateAsync(id);
  };

  const diretas = etapas?.filter((e) => e.tipo_mao_obra === "direta") ?? [];
  const indiretas = etapas?.filter((e) => e.tipo_mao_obra === "indireta") ?? [];

  return (
    <div className="space-y-5">
      <Link
        href="/configuracoes"
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">Etapas de Produção</h1>
          <p className="text-muted-foreground text-sm">
            Cadastre uma vez, reutilize em todas as receitas
          </p>
        </div>
        {!mostrandoForm && (
          <button
            onClick={() => setMostrandoForm(true)}
            className="flex items-center gap-1 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            Nova
          </button>
        )}
      </div>

      {mostrandoForm && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="rounded-xl border bg-card p-4 space-y-3"
        >
          <h2 className="font-semibold text-sm">Nova etapa padrão</h2>

          <div className="space-y-1">
            <label className="text-xs font-medium">Nome da etapa</label>
            <input
              type="text"
              placeholder="Ex: Preparo da massa"
              className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              {...register("nome", { required: "Informe o nome" })}
            />
            {errors.nome && <p className="text-xs text-destructive">{errors.nome.message}</p>}
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium">Tipo de mão de obra</label>
            <select
              className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
              {...register("tipo_mao_obra")}
            >
              <option value="direta">Direta — fabricação do produto</option>
              <option value="indireta">Indireta — apoio (limpeza, compras...)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium">Duração padrão (minutos)</label>
            <p className="text-xs text-muted-foreground">
              Pode ser ajustada em cada receita
            </p>
            <Controller
              name="duracao_minutos_default"
              control={control}
              render={({ field }) => (
                <DecimalInput
                  value={field.value}
                  onChange={(v) => field.onChange(Math.round(v))}
                  placeholder="30"
                />
              )}
            />
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                reset();
                setMostrandoForm(false);
              }}
              className="flex-1 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={criar.isPending}
              className="flex-1 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {criar.isPending ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !etapas?.length && !mostrandoForm ? (
        <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
          <p className="font-medium">Nenhuma etapa cadastrada ainda</p>
          <p className="text-sm mt-1">
            Cadastre etapas comuns (preparo, decoração, limpeza...) para acelerar o cadastro de receitas
          </p>
        </div>
      ) : (
        <>
          <SecaoEtapas
            titulo="Mão de obra direta"
            descricao="Tempo trabalhando diretamente no produto"
            etapas={diretas}
            onDeletar={handleDeletar}
          />
          <SecaoEtapas
            titulo="Mão de obra indireta"
            descricao="Tempo de apoio (limpeza, organização, compras)"
            etapas={indiretas}
            onDeletar={handleDeletar}
          />
        </>
      )}
    </div>
  );
}

function SecaoEtapas({
  titulo,
  descricao,
  etapas,
  onDeletar,
}: {
  titulo: string;
  descricao: string;
  etapas: Array<{ id: string; nome: string; duracao_minutos_default: number }>;
  onDeletar: (id: string, nome: string) => void;
}) {
  if (!etapas.length) return null;
  return (
    <section className="space-y-2">
      <div>
        <h2 className="font-semibold">{titulo}</h2>
        <p className="text-xs text-muted-foreground">{descricao}</p>
      </div>
      <div className="divide-y rounded-xl border">
        {etapas.map((e) => (
          <div key={e.id} className="flex items-center justify-between px-4 py-3">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm">{e.nome}</p>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {formatMinutos(e.duracao_minutos_default)}
              </div>
            </div>
            <button
              onClick={() => onDeletar(e.id, e.nome)}
              className={cn("p-2 rounded-lg hover:bg-destructive/10 text-destructive")}
              aria-label={`Remover ${e.nome}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
