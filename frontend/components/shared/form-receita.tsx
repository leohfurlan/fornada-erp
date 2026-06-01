"use client";

import Link from "next/link";
import { Plus, Trash2 } from "lucide-react";
import { useForm, useFieldArray, Controller, type SubmitHandler } from "react-hook-form";
import { useIngredientes } from "@/hooks/use-estoque";
import { useEtapasPadrao } from "@/hooks/use-configuracoes";
import { DecimalInput } from "@/components/shared/decimal-input";
import { UnidadeSelect } from "@/components/shared/unidade-select";
import { CATEGORIAS_RECEITA, UNIDADES_MEDIDA } from "@/lib/unidades";

export interface ReceitaFormValues {
  nome: string;
  categoria: string;
  rendimento: number;
  rendimento_unidade: string;
  margem_desejada: number; // como percentual (0-99), conversão p/ decimal acontece no submit
  preco_de_venda_real: number; // 0 = sem preço informado (omitido no payload)
  modo_preparo: string;
  ingredientes: Array<{ ingrediente_id: string; quantidade: number; unidade: string }>;
  etapas: Array<{ nome: string; duracao_minutos: number; tipo_mao_obra: "direta" | "indireta"; ordem: number }>;
}

interface FormReceitaProps {
  valoresIniciais?: Partial<ReceitaFormValues>;
  textoBotao: string;
  textoBotaoLoading: string;
  isPending?: boolean;
  isError?: boolean;
  onSubmit: SubmitHandler<ReceitaFormValues>;
}

const defaultsForm: ReceitaFormValues = {
  nome: "",
  categoria: "",
  rendimento: 0,
  rendimento_unidade: "",
  margem_desejada: 30,
  preco_de_venda_real: 0,
  modo_preparo: "",
  ingredientes: [{ ingrediente_id: "", quantidade: 0, unidade: "" }],
  etapas: [{ nome: "", duracao_minutos: 30, tipo_mao_obra: "direta", ordem: 0 }],
};

export function FormReceita({
  valoresIniciais,
  textoBotao,
  textoBotaoLoading,
  isPending,
  isError,
  onSubmit,
}: FormReceitaProps) {
  const { data: ingredientes } = useIngredientes();
  const { data: etapasPadrao } = useEtapasPadrao();

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ReceitaFormValues>({
    defaultValues: { ...defaultsForm, ...valoresIniciais },
  });

  const {
    fields: camposIngredientes,
    append: addIngrediente,
    remove: removeIngrediente,
  } = useFieldArray({ control, name: "ingredientes" });

  const { fields: camposEtapas, append: addEtapa, remove: removeEtapa } = useFieldArray({
    control,
    name: "etapas",
  });

  const aplicarEtapaPadrao = (index: number, etapaPadraoId: string) => {
    if (!etapaPadraoId) return;
    const ep = etapasPadrao?.find((e) => e.id === etapaPadraoId);
    if (!ep) return;
    setValue(`etapas.${index}.nome`, ep.nome);
    setValue(`etapas.${index}.tipo_mao_obra`, ep.tipo_mao_obra);
    setValue(`etapas.${index}.duracao_minutos`, ep.duracao_minutos_default);
  };

  const aplicarUnidadeDoIngrediente = (index: number, ingredienteId: string) => {
    const ing = ingredientes?.find((i) => i.id === ingredienteId);
    if (ing) setValue(`ingredientes.${index}.unidade`, ing.unidade);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Dados básicos */}
      <section className="space-y-3">
        <div className="space-y-1">
          <label className="text-sm font-medium">Nome da receita</label>
          <input
            type="text"
            placeholder="Ex: Bolo de chocolate"
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            {...register("nome", { required: "Informe o nome" })}
          />
          {errors.nome && <p className="text-xs text-destructive">{errors.nome.message}</p>}
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium">Categoria</label>
          <select
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
            {...register("categoria", { required: "Selecione uma categoria" })}
          >
            <option value="">Selecione...</option>
            {CATEGORIAS_RECEITA.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          {errors.categoria && (
            <p className="text-xs text-destructive">{errors.categoria.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium">Rendimento</label>
            <Controller
              name="rendimento"
              control={control}
              rules={{ validate: (v) => v > 0 || "Maior que 0" }}
              render={({ field }) => (
                <DecimalInput value={field.value} onChange={field.onChange} placeholder="12" />
              )}
            />
            {errors.rendimento && (
              <p className="text-xs text-destructive">{errors.rendimento.message}</p>
            )}
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Unidade de venda</label>
            <Controller
              name="rendimento_unidade"
              control={control}
              rules={{ required: "Selecione" }}
              render={({ field }) => (
                <UnidadeSelect
                  tipo="venda"
                  value={field.value}
                  onChange={field.onChange}
                  placeholder="fatias, un..."
                />
              )}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium">Margem desejada</label>
            <p className="text-xs text-muted-foreground">
              Margem de lucro para o preço recomendado
            </p>
            <div className="relative">
              <Controller
                name="margem_desejada"
                control={control}
                render={({ field }) => (
                  <DecimalInput
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="30"
                    className="pr-8"
                  />
                )}
              />
              <span className="absolute right-3 top-2.5 text-sm text-muted-foreground pointer-events-none">
                %
              </span>
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Preço de venda real</label>
            <p className="text-xs text-muted-foreground">
              Quanto você cobra de fato. Calcula lucro e margem real.
            </p>
            <div className="relative">
              <Controller
                name="preco_de_venda_real"
                control={control}
                render={({ field }) => (
                  <DecimalInput
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="0,00"
                    className="pl-9"
                  />
                )}
              />
              <span className="absolute left-3 top-2.5 text-sm text-muted-foreground pointer-events-none">
                R$
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Ingredientes */}
      <section className="space-y-3">
        <h2 className="font-semibold">Ingredientes</h2>
        {!ingredientes?.length && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
            Você ainda não cadastrou nenhum ingrediente.{" "}
            <Link href="/estoque/novo" className="underline font-medium">
              Cadastrar agora
            </Link>
          </div>
        )}
        {camposIngredientes.map((field, index) => (
          <div key={field.id} className="rounded-xl border p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Ingrediente {index + 1}
              </span>
              {camposIngredientes.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeIngrediente(index)}
                  className="p-1 rounded hover:bg-destructive/10 text-destructive"
                  aria-label="Remover ingrediente"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            <Controller
              name={`ingredientes.${index}.ingrediente_id`}
              control={control}
              render={({ field }) => (
                <select
                  className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                  value={field.value}
                  onChange={(e) => {
                    field.onChange(e.target.value);
                    aplicarUnidadeDoIngrediente(index, e.target.value);
                  }}
                >
                  <option value="">Selecione o ingrediente...</option>
                  {ingredientes?.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.nome} ({i.unidade})
                    </option>
                  ))}
                </select>
              )}
            />

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground">Quantidade</label>
                <Controller
                  name={`ingredientes.${index}.quantidade`}
                  control={control}
                  render={({ field }) => (
                    <DecimalInput
                      value={field.value}
                      onChange={field.onChange}
                      placeholder="0,5"
                    />
                  )}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Unidade</label>
                <Controller
                  name={`ingredientes.${index}.unidade`}
                  control={control}
                  render={({ field }) => (
                    <select
                      value={field.value}
                      onChange={field.onChange}
                      className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                    >
                      <option value="">Unidade...</option>
                      {UNIDADES_MEDIDA.map((u) => (
                        <option key={u.value} value={u.value}>
                          {u.value}
                        </option>
                      ))}
                    </select>
                  )}
                />
              </div>
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={() => addIngrediente({ ingrediente_id: "", quantidade: 0, unidade: "" })}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed px-4 py-2.5 text-sm text-muted-foreground hover:border-primary hover:text-primary"
        >
          <Plus className="h-4 w-4" />
          Adicionar ingrediente
        </button>
      </section>

      {/* Etapas */}
      <section className="space-y-3">
        <h2 className="font-semibold">Etapas de produção</h2>
        {camposEtapas.map((field, index) => (
          <div key={field.id} className="rounded-xl border p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Etapa {index + 1}
              </span>
              {camposEtapas.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeEtapa(index)}
                  className="p-1 rounded hover:bg-destructive/10 text-destructive"
                  aria-label="Remover etapa"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {etapasPadrao && etapasPadrao.length > 0 && (
              <select
                className="w-full rounded-lg border px-3 py-2 text-xs bg-muted/30 focus:outline-none focus:ring-2 focus:ring-primary"
                defaultValue=""
                onChange={(e) => {
                  aplicarEtapaPadrao(index, e.target.value);
                  e.target.value = "";
                }}
              >
                <option value="">⚡ Usar etapa cadastrada...</option>
                {etapasPadrao.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome} — {e.tipo_mao_obra === "direta" ? "direta" : "indireta"} (
                    {e.duracao_minutos_default}min)
                  </option>
                ))}
              </select>
            )}

            <input
              type="text"
              placeholder="Ex: Preparar a massa"
              className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              {...register(`etapas.${index}.nome`, { required: true })}
            />

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground">Duração (min)</label>
                <Controller
                  name={`etapas.${index}.duracao_minutos`}
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
              <div>
                <label className="text-xs text-muted-foreground">Tipo</label>
                <select
                  className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                  {...register(`etapas.${index}.tipo_mao_obra`)}
                >
                  <option value="direta">Mão de obra direta</option>
                  <option value="indireta">Mão de obra indireta</option>
                </select>
              </div>
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={() =>
            addEtapa({ nome: "", duracao_minutos: 30, tipo_mao_obra: "direta", ordem: 0 })
          }
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed px-4 py-2.5 text-sm text-muted-foreground hover:border-primary hover:text-primary"
        >
          <Plus className="h-4 w-4" />
          Adicionar etapa
        </button>

        {(!etapasPadrao || etapasPadrao.length === 0) && (
          <p className="text-xs text-muted-foreground">
            💡 Dica: cadastre etapas comuns em{" "}
            <Link href="/configuracoes/etapas" className="underline text-primary">
              Configurações → Etapas
            </Link>{" "}
            para reutilizar entre receitas.
          </p>
        )}
      </section>

      {/* Modo de preparo */}
      <section className="space-y-2">
        <h2 className="font-semibold">Modo de preparo</h2>
        <p className="text-xs text-muted-foreground">
          Escreva o passo a passo para consultar enquanto produz. Quebras de linha são preservadas.
        </p>
        <textarea
          rows={8}
          placeholder={
            "1. Pré-aqueça o forno a 180°C\n2. Bata as claras em neve\n3. Adicione o açúcar aos poucos\n..."
          }
          className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y min-h-[160px]"
          {...register("modo_preparo")}
        />
      </section>

      {isError && (
        <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          Não foi possível salvar a receita. Verifique os dados e tente novamente.
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting || isPending}
        className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {isSubmitting || isPending ? textoBotaoLoading : textoBotao}
      </button>
    </form>
  );
}
