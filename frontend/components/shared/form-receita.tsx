"use client";

import { ValidatedForm } from "@/components/shared/validation-feedback";
import { useEffect, useState } from "react";
import { useRascunho } from "@/hooks/use-rascunho";
import { RascunhoFeedback } from "@/components/shared/rascunho-feedback";

import Link from "next/link";
import { Plus, Trash2 } from "lucide-react";
import { useForm, useFieldArray, Controller, type SubmitHandler } from "@/lib/form";
import { useCriarIngrediente, useIngredientes } from "@/hooks/use-estoque";
import { useReceitas } from "@/hooks/use-receitas";
import type { Ingrediente } from "@/types";
import { useEtapasPadrao } from "@/hooks/use-configuracoes";
import { DecimalInput } from "@/components/shared/decimal-input";
import { UnidadeSelect } from "@/components/shared/unidade-select";
import { MarkdownField } from "@/components/shared/markdown-field";
import { CATEGORIAS_RECEITA, UNIDADES_MEDIDA } from "@/lib/unidades";
import { erroNome, nomeMaiusculo } from "@/lib/nomes";

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export interface ReceitaFormValues {
  versao?: number;
  nome: string;
  categoria: string;
  rendimento: number;
  rendimento_unidade: string;
  margem_desejada: number; // como percentual (0-99), conversão p/ decimal acontece no submit
  preco_de_venda_real: number; // 0 = sem preço informado (omitido no payload)
  modo_preparo: string;
  ingredientes: Array<{
    origem_tipo: "material" | "receita_base";
    ingrediente_id: string;
    receita_componente_id: string;
    quantidade: number;
    unidade: string;
  }>;
  etapas: Array<{ nome: string; duracao_minutos: number; tipo_mao_obra: "direta" | "indireta"; ordem: number }>;
}

interface FormReceitaProps {
  rascunhoId?: string;
  receitaAtualId?: string;
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
  ingredientes: [{ origem_tipo: "material", ingrediente_id: "", receita_componente_id: "", quantidade: 0, unidade: "" }],
  etapas: [{ nome: "", duracao_minutos: 30, tipo_mao_obra: "direta", ordem: 0 }],
};

export function FormReceita({
  rascunhoId = "receita:nova",
  receitaAtualId,
  valoresIniciais,
  textoBotao,
  textoBotaoLoading,
  isPending,
  isError,
  onSubmit,
}: FormReceitaProps) {
  const { data: ingredientes } = useIngredientes();
  const { data: receitas } = useReceitas();
  const { data: etapasPadrao } = useEtapasPadrao();
  const criarInsumo = useCriarIngrediente();
  const [materiaisCriados, setMateriaisCriados] = useState<Ingrediente[]>([]);
  const [linhaCadastroInsumo, setLinhaCadastroInsumo] = useState<number | null>(null);
  const [novoInsumoNome, setNovoInsumoNome] = useState("");
  const [novoInsumoUnidade, setNovoInsumoUnidade] = useState("");
  const [novoInsumoEstoque, setNovoInsumoEstoque] = useState(0);
  const [novoInsumoCusto, setNovoInsumoCusto] = useState(0);
  const [erroCadastroInsumo, setErroCadastroInsumo] = useState("");
  const materiaisDisponiveis = [
    ...(ingredientes ?? []),
    ...materiaisCriados.filter((novo) => !ingredientes?.some((item) => item.id === novo.id)),
  ];
  const receitasDisponiveis = (receitas ?? []).filter((receita) => receita.id !== receitaAtualId);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    reset,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<ReceitaFormValues>({
    defaultValues: { ...defaultsForm, ...valoresIniciais, nome: nomeMaiusculo(valoresIniciais?.nome ?? "") },
  });

  const rascunho = useRascunho(rascunhoId, getValues(), reset);
  useEffect(() => {
    const subscription = watch(() => rascunho.persist(getValues()));
    return () => subscription.unsubscribe();
  }, [watch, getValues, rascunho.persist]);

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
    setValue(`etapas.${index}.duracao_minutos`, ep.duracao_minutos_default ?? 0);
    if (ep.instrucao) {
      const preparo = watch("modo_preparo");
      const texto = `${ep.receita_origem ? ep.receita_origem + "\n" : ""}${ep.instrucao}`;
      if (!preparo.includes(texto)) setValue("modo_preparo", preparo ? `${preparo}\n\n${texto}` : texto);
    }
  };

  const aplicarUnidadeDoIngrediente = (index: number, ingredienteId: string) => {
    const ing = materiaisDisponiveis.find((i) => i.id === ingredienteId);
    if (ing) setValue(`ingredientes.${index}.unidade`, ing.unidade);
  };

  const selecionarOrigem = (index: number, origem: "material" | "receita_base") => {
    setValue(`ingredientes.${index}.origem_tipo`, origem);
    setValue(`ingredientes.${index}.ingrediente_id`, "");
    setValue(`ingredientes.${index}.receita_componente_id`, "");
    setValue(`ingredientes.${index}.unidade`, "");
  };

  const aplicarUnidadeDaReceita = (index: number, receitaId: string) => {
    const receita = receitasDisponiveis.find((item) => item.id === receitaId);
    if (receita) setValue(`ingredientes.${index}.unidade`, receita.rendimento_unidade);
  };

  const salvarNovoInsumo = async (index: number) => {
    setErroCadastroInsumo("");
    if (!novoInsumoNome.trim() || !novoInsumoUnidade) {
      setErroCadastroInsumo("Informe o nome e a unidade principal do insumo.");
      return;
    }
    try {
      const novo = await criarInsumo.mutateAsync({
        nome: novoInsumoNome.trim(),
        tipo: "insumo",
        unidade: novoInsumoUnidade,
        unidades_alternativas: [],
        estoque_minimo: 0,
        estoque_inicial: novoInsumoEstoque,
        custo_inicial: novoInsumoCusto,
      });
      setMateriaisCriados((atuais) => [...atuais, novo]);
      setValue(`ingredientes.${index}.origem_tipo`, "material");
      setValue(`ingredientes.${index}.receita_componente_id`, "");
      setValue(`ingredientes.${index}.ingrediente_id`, novo.id);
      setValue(`ingredientes.${index}.unidade`, novo.unidade);
      setLinhaCadastroInsumo(null);
      setNovoInsumoNome("");
      setNovoInsumoUnidade("");
      setNovoInsumoEstoque(0);
      setNovoInsumoCusto(0);
    } catch {
      setErroCadastroInsumo("Não foi possível cadastrar o insumo. Confira os dados e tente novamente.");
    }
  };

  return (
    <ValidatedForm errors={errors} onSubmit={handleSubmit(async (values, event) => {
      await onSubmit(values, event);
      rascunho.complete(values, values);
    })} className="space-y-6">
      <RascunhoFeedback {...rascunho} />
      {/* Dados básicos */}
      <section className="space-y-3">
        <div className="space-y-1">
          <label className="text-sm font-medium">Nome da receita</label>
          <input
            type="text"
            placeholder="Ex: Bolo de chocolate"
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            maxLength={200}
            {...register("nome", {
              required: "Informe o nome",
              setValueAs: nomeMaiusculo,
              validate: (value) => erroNome(value) ?? true,
              onChange: (event) => { event.target.value = nomeMaiusculo(event.target.value); },
            })}
          />
          <p className="text-xs text-muted-foreground">Nome em letras maiúsculas, sem emojis.</p>
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
        <h2 className="font-semibold">Ingredientes e componentes</h2>
        {!materiaisDisponiveis.length && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
            Você ainda não cadastrou materiais. Você pode vincular outra receita como massa ou recheio, ou cadastrar um insumo aqui.
          </div>
        )}
        {camposIngredientes.map((field, index) => (
          <div key={field.id} className="rounded-xl border p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Item {index + 1}
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

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">O que entra nesta receita?</label>
              <select
                className="w-full rounded-lg border px-3 py-2.5 text-sm bg-background"
                value={watch(`ingredientes.${index}.origem_tipo`) || "material"}
                onChange={(event) => selecionarOrigem(index, event.target.value as "material" | "receita_base")}
              >
                <option value="material">Ingrediente ou insumo</option>
                <option value="receita_base">Massa, recheio ou outra receita</option>
              </select>
            </div>

            {watch(`ingredientes.${index}.origem_tipo`) === "receita_base" ? (
              <>
                <Controller
                  name={`ingredientes.${index}.receita_componente_id`}
                  control={control}
                  rules={{ validate: (value) => watch(`ingredientes.${index}.origem_tipo`) !== "receita_base" || !!value || "Selecione uma receita-base" }}
                  render={({ field }) => (
                    <select
                      className="w-full rounded-lg border px-3 py-2.5 text-sm bg-background"
                      value={field.value}
                      onChange={(event) => {
                        field.onChange(event.target.value);
                        aplicarUnidadeDaReceita(index, event.target.value);
                      }}
                    >
                      <option value="">Selecione uma massa, recheio ou receita...</option>
                      {receitasDisponiveis.map((receita) => (
                        <option key={receita.id} value={receita.id}>
                          {receita.nome} · rende {receita.rendimento} {receita.rendimento_unidade}
                          {receita.custo?.custo_por_unidade
                            ? ` · ${moeda.format(Number(receita.custo.custo_por_unidade))}/${receita.rendimento_unidade}`
                            : ""}
                        </option>
                      ))}
                    </select>
                  )}
                />
                {receitasDisponiveis.length === 0 && (
                  <p className="text-xs text-muted-foreground">Cadastre primeiro a massa ou o recheio como receita.</p>
                )}
                <p className="text-xs text-muted-foreground">A quantidade usa a unidade de rendimento da receita selecionada, e o custo dela entra no custo desta receita. A produção reserva o estoque da massa ou do recheio selecionado.</p>
              </>
            ) : (
              <>
                <Controller
                  name={`ingredientes.${index}.ingrediente_id`}
                  control={control}
                  rules={{ validate: (value) => watch(`ingredientes.${index}.origem_tipo`) !== "material" || !!value || "Selecione um ingrediente ou insumo" }}
                  render={({ field }) => (
                    <select
                      className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                      value={field.value}
                      onChange={(event) => {
                        field.onChange(event.target.value);
                        aplicarUnidadeDoIngrediente(index, event.target.value);
                      }}
                    >
                      <option value="">Selecione um ingrediente ou insumo...</option>
                      {materiaisDisponiveis.map((material) => (
                        <option key={material.id} value={material.id}>
                          {material.nome} ({material.unidade}){material.tipo === "insumo" ? " · insumo" : ""}
                        </option>
                      ))}
                    </select>
                  )}
                />
              </>
            )}

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
                {watch(`ingredientes.${index}.origem_tipo`) === "receita_base" ? (
                  <>
                    <label className="text-xs text-muted-foreground">Unidade da receita-base</label>
                    <input
                      readOnly
                      value={receitasDisponiveis.find((item) => item.id === watch(`ingredientes.${index}.receita_componente_id`))?.rendimento_unidade ?? ""}
                      className="w-full rounded-lg border bg-muted px-3 py-2.5 text-sm"
                    />
                  </>
                ) : (
                  <>
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
                          {(materiaisDisponiveis.find(i => i.id === watch(`ingredientes.${index}.ingrediente_id`))?.unidades_alternativas || []).map(u => <option key={`alt-${u.unidade}`} value={u.unidade}>{u.unidade}</option>)}
                          {UNIDADES_MEDIDA.map((u) => (
                            <option key={u.value} value={u.value}>
                              {u.value}
                            </option>
                          ))}
                        </select>
                      )}
                    />
                  </>
                )}
              </div>
            </div>

            {linhaCadastroInsumo === index ? (
              <div className="space-y-2 rounded-lg bg-muted/40 p-3">
                <p className="text-sm font-medium">Cadastrar insumo</p>
                <input
                  autoFocus
                  value={novoInsumoNome}
                  onChange={(event) => setNovoInsumoNome(event.target.value)}
                  placeholder="Ex.: chocolate em pó"
                  maxLength={200}
                  className="w-full rounded-lg border bg-background px-3 py-2.5 text-sm"
                />
                <UnidadeSelect
                  tipo="medida"
                  somenteBase
                  value={novoInsumoUnidade}
                  onChange={(event) => setNovoInsumoUnidade(event.target.value)}
                  placeholder="Unidade principal"
                />
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-muted-foreground">Estoque inicial (opcional)</label>
                    <DecimalInput value={novoInsumoEstoque} onChange={setNovoInsumoEstoque} placeholder="0" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Custo por {novoInsumoUnidade || "unidade"} (R$)</label>
                    <DecimalInput value={novoInsumoCusto} onChange={setNovoInsumoCusto} placeholder="0,00" />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">Informe o custo por unidade principal para incluir o insumo no cálculo. O estoque inicial é opcional.</p>
                {erroCadastroInsumo && <p role="alert" className="text-xs text-destructive">{erroCadastroInsumo}</p>}
                <div className="flex gap-2">
                  <button type="button" disabled={criarInsumo.isPending} onClick={() => void salvarNovoInsumo(index)} className="rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-50">
                    {criarInsumo.isPending ? "Cadastrando..." : "Salvar e usar"}
                  </button>
                  <button type="button" onClick={() => { setLinhaCadastroInsumo(null); setErroCadastroInsumo(""); }} className="rounded-lg border px-3 py-2 text-sm">Cancelar</button>
                </div>
              </div>
            ) : (
              watch(`ingredientes.${index}.origem_tipo`) === "material" && (
                <button
                  type="button"
                  onClick={() => {
                    setLinhaCadastroInsumo(index);
                    setNovoInsumoNome("");
                    setNovoInsumoUnidade("");
                    setNovoInsumoEstoque(0);
                    setNovoInsumoCusto(0);
                    setErroCadastroInsumo("");
                  }}
                  className="text-sm text-primary underline"
                >
                  Cadastrar insumo
                </button>
              )
            )}
          </div>
        ))}

        <button
          type="button"
          onClick={() => addIngrediente({ origem_tipo: "material", ingrediente_id: "", receita_componente_id: "", quantidade: 0, unidade: "" })}
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
                    {e.duracao_minutos_default === null ? "tempo pendente" : `${e.duracao_minutos_default}min`})
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
                  rules={{ validate: value => value > 0 || "Informe o tempo desta etapa para calcular o custo." }}
                  render={({ field }) => (
                    <DecimalInput
                      value={field.value || ""}
                      onChange={(v) => field.onChange(Math.round(v))}
                      placeholder="30"
                    />
                  )}
                />
                {errors.etapas?.[index]?.duracao_minutos && <p className="text-xs text-destructive">{errors.etapas[index]?.duracao_minutos?.message}</p>}
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
        <Controller name="modo_preparo" control={control} render={({ field }) => (
          <MarkdownField label="Modo de preparo" value={field.value} onChange={field.onChange} onBlur={field.onBlur} name={field.name} rows={8} placeholder={"1. Pré-aqueça o forno a **180°C**\n2. Bata as claras em neve\n3. Adicione o açúcar aos poucos"} />
        )} />
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
      <Link href="/receitas" className="block rounded-lg border px-4 py-3 text-center text-sm">Cancelar</Link>
    </ValidatedForm>
  );
}
