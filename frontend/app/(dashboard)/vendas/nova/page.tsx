"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { DecimalInput } from "@/components/shared/decimal-input";
import { CANAIS_VENDA } from "@/components/shared/canal-venda-icon";
import { useClientes } from "@/hooks/use-clientes";
import { useEstoquePA } from "@/hooks/use-estoque-pa";
import { useReceitas } from "@/hooks/use-receitas";
import { useCriarVenda } from "@/hooks/use-vendas";
import { cn, formatMoney, formatQuantidade } from "@/lib/utils";
import type { ApiError, CanalVenda } from "@/types";
import type { AxiosError } from "axios";

interface VendaItemForm {
  receita_id: string;
  quantidade: number;
  preco_unitario: number;
  observacoes: string;
}

interface VendaForm {
  canal: CanalVenda | "";
  cliente_id: string;
  observacoes: string;
  itens: VendaItemForm[];
}

export default function NovaVendaPage() {
  const router = useRouter();
  const { data: receitas } = useReceitas();
  const { data: clientes } = useClientes();
  const { data: estoquePA } = useEstoquePA();
  const criar = useCriarVenda();

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<VendaForm>({
    defaultValues: {
      canal: "",
      cliente_id: "",
      observacoes: "",
      itens: [{ receita_id: "", quantidade: 1, preco_unitario: 0, observacoes: "" }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "itens" });
  const canalAtual = watch("canal");
  const itensWatch = watch("itens");

  const total = useMemo(
    () =>
      itensWatch.reduce(
        (sum, it) => sum + (it.quantidade || 0) * (it.preco_unitario || 0),
        0
      ),
    [itensWatch]
  );

  const aplicarPrecoSugerido = (index: number, receitaId: string) => {
    const r = receitas?.find((x) => x.id === receitaId);
    if (r?.custo) {
      setValue(`itens.${index}.preco_unitario`, parseFloat(r.custo.preco_recomendado));
    }
  };

  const saldoDe = (receitaId: string): string | null => {
    const e = estoquePA?.find((s) => s.receita_id === receitaId);
    return e ? e.qtd_disponivel : null;
  };

  const onSubmit = async (data: VendaForm) => {
    if (!data.canal) return;
    const payload = {
      canal: data.canal,
      cliente_id: data.cliente_id || null,
      observacoes: data.observacoes || null,
      itens: data.itens.map((it) => ({
        receita_id: it.receita_id,
        quantidade: it.quantidade,
        preco_unitario: it.preco_unitario,
        observacoes: it.observacoes || null,
      })),
    };
    const venda = await criar.mutateAsync(payload);
    router.push(`/vendas/${venda.id}`);
  };

  const erro = criar.error as AxiosError<ApiError> | null;
  const mensagem = erro?.response?.data?.detail;

  return (
    <div className="space-y-5 pb-8">
      <Link href="/vendas" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <h1 className="text-xl font-bold">Nova venda</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Canal — chips grandes */}
        <section className="space-y-2">
          <label className="text-sm font-medium">Canal</label>
          <Controller
            name="canal"
            control={control}
            rules={{ required: "Selecione o canal" }}
            render={({ field }) => (
              <div className="grid grid-cols-2 gap-2">
                {CANAIS_VENDA.map(({ value, label, Icon }) => {
                  const ativo = field.value === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => field.onChange(value)}
                      className={cn(
                        "flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium transition-colors",
                        ativo
                          ? "border-primary bg-primary/10 text-primary"
                          : "hover:bg-muted"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  );
                })}
              </div>
            )}
          />
          {errors.canal && (
            <p className="text-xs text-destructive">{errors.canal.message}</p>
          )}
        </section>

        {/* Itens */}
        <section className="space-y-3">
          <h2 className="font-semibold">Itens vendidos</h2>
          {fields.map((field, index) => {
            const receitaIdAtual = itensWatch[index]?.receita_id;
            const saldo = receitaIdAtual ? saldoDe(receitaIdAtual) : null;
            const subtotal =
              (itensWatch[index]?.quantidade || 0) *
              (itensWatch[index]?.preco_unitario || 0);
            return (
              <div key={field.id} className="rounded-xl border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">
                    Item {index + 1}
                  </span>
                  {fields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      className="p-1 rounded hover:bg-destructive/10 text-destructive"
                      aria-label="Remover item"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>

                <Controller
                  name={`itens.${index}.receita_id`}
                  control={control}
                  rules={{ required: "Selecione a receita" }}
                  render={({ field }) => (
                    <select
                      className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                      value={field.value}
                      onChange={(e) => {
                        field.onChange(e.target.value);
                        aplicarPrecoSugerido(index, e.target.value);
                      }}
                    >
                      <option value="">Selecione a receita...</option>
                      {receitas?.map((r) => {
                        const s = saldoDe(r.id);
                        return (
                          <option key={r.id} value={r.id}>
                            {r.nome}
                            {s !== null && ` — ${formatQuantidade(s)} disp.`}
                          </option>
                        );
                      })}
                    </select>
                  )}
                />
                {saldo !== null && parseFloat(saldo) <= 0 && (
                  <p className="text-xs text-orange-600">
                    ⚠️ Sem saldo em estoque. Produza antes de vender.
                  </p>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-muted-foreground">Quantidade</label>
                    <Controller
                      name={`itens.${index}.quantidade`}
                      control={control}
                      rules={{ validate: (v) => v > 0 || "Maior que 0" }}
                      render={({ field }) => (
                        <DecimalInput
                          value={field.value}
                          onChange={field.onChange}
                          placeholder="1"
                        />
                      )}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Preço unit. (R$)</label>
                    <Controller
                      name={`itens.${index}.preco_unitario`}
                      control={control}
                      rules={{ validate: (v) => v > 0 || "Maior que 0" }}
                      render={({ field }) => (
                        <DecimalInput
                          value={field.value}
                          onChange={field.onChange}
                          placeholder="0,00"
                        />
                      )}
                    />
                  </div>
                </div>

                <input
                  type="text"
                  placeholder="Observações do item (opcional)"
                  className="w-full rounded-lg border px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                  {...register(`itens.${index}.observacoes`)}
                />

                <div className="flex justify-between text-xs text-muted-foreground pt-1 border-t">
                  <span>Subtotal</span>
                  <span className="font-medium text-foreground">{formatMoney(subtotal)}</span>
                </div>
              </div>
            );
          })}

          <button
            type="button"
            onClick={() =>
              append({ receita_id: "", quantidade: 1, preco_unitario: 0, observacoes: "" })
            }
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed px-4 py-2.5 text-sm text-muted-foreground hover:border-primary hover:text-primary"
          >
            <Plus className="h-4 w-4" />
            Adicionar item
          </button>
        </section>

        {/* Cliente (opcional) */}
        <section className="space-y-1">
          <label className="text-sm font-medium">Cliente (opcional)</label>
          <p className="text-xs text-muted-foreground">
            Útil pra histórico. Pode deixar em branco em venda avulsa.
          </p>
          <select
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
            {...register("cliente_id")}
          >
            <option value="">Sem cliente</option>
            {clientes?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </section>

        {/* Observações */}
        <section className="space-y-1">
          <label className="text-sm font-medium">Observações</label>
          <textarea
            rows={2}
            placeholder="Detalhes da venda (opcional)"
            className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
            {...register("observacoes")}
          />
        </section>

        {/* Total */}
        <div className="rounded-xl bg-primary/5 border border-primary/20 p-4 flex items-center justify-between">
          <span className="font-medium">Total da venda</span>
          <span className="font-bold text-lg text-primary">{formatMoney(total)}</span>
        </div>

        {mensagem && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {mensagem}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || criar.isPending || !canalAtual}
          className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting || criar.isPending ? "Registrando..." : "Registrar venda"}
        </button>
      </form>
    </div>
  );
}
