"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowLeft, Plus, Trash2, UserPlus } from "lucide-react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { DecimalInput } from "@/components/shared/decimal-input";
import { useClientes, useCriarCliente } from "@/hooks/use-clientes";
import { useCriarPedido } from "@/hooks/use-pedidos";
import { useReceitas } from "@/hooks/use-receitas";
import { formatMoney } from "@/lib/utils";

interface PedidoItemForm {
  receita_id: string;
  quantidade: number;
  preco_unitario: number;
  observacoes: string;
}

interface PedidoForm {
  cliente_id: string;
  data_entrega: string;
  observacoes: string;
  itens: PedidoItemForm[];
}

export default function NovoPedidoPage() {
  const router = useRouter();
  const { data: clientes } = useClientes();
  const { data: receitas } = useReceitas();
  const criarPedido = useCriarPedido();
  const criarCliente = useCriarCliente();

  const [novoClienteAberto, setNovoClienteAberto] = useState(false);
  const [novoClienteNome, setNovoClienteNome] = useState("");
  const [novoClienteTelefone, setNovoClienteTelefone] = useState("");

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<PedidoForm>({
    defaultValues: {
      cliente_id: "",
      data_entrega: "",
      observacoes: "",
      itens: [{ receita_id: "", quantidade: 1, preco_unitario: 0, observacoes: "" }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "itens" });
  const itensWatch = watch("itens");

  const valorTotal = useMemo(() => {
    return itensWatch.reduce(
      (sum, it) => sum + (it.quantidade || 0) * (it.preco_unitario || 0),
      0
    );
  }, [itensWatch]);

  const aplicarPrecoSugerido = (index: number, receitaId: string) => {
    const r = receitas?.find((x) => x.id === receitaId);
    if (r?.custo) {
      setValue(`itens.${index}.preco_unitario`, parseFloat(r.custo.preco_recomendado));
    }
  };

  const criarClienteInline = async () => {
    if (!novoClienteNome.trim()) return;
    const cliente = await criarCliente.mutateAsync({
      nome: novoClienteNome.trim(),
      telefone: novoClienteTelefone.trim() || undefined,
    });
    setValue("cliente_id", cliente.id);
    setNovoClienteAberto(false);
    setNovoClienteNome("");
    setNovoClienteTelefone("");
  };

  const onSubmit = async (data: PedidoForm) => {
    const payload = {
      cliente_id: data.cliente_id || null,
      data_entrega: data.data_entrega || null,
      observacoes: data.observacoes || null,
      itens: data.itens.map((it) => ({
        receita_id: it.receita_id,
        quantidade: it.quantidade,
        preco_unitario: it.preco_unitario,
        observacoes: it.observacoes || null,
      })),
    };
    const pedido = await criarPedido.mutateAsync(payload);
    router.push(`/pedidos/${pedido.id}`);
  };

  return (
    <div className="space-y-5 pb-8">
      <Link href="/pedidos" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <h1 className="text-xl font-bold">Novo pedido</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Cliente */}
        <section className="space-y-1">
          <label className="text-sm font-medium">Cliente</label>
          {!novoClienteAberto ? (
            <div className="flex gap-2">
              <select
                className="flex-1 rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                {...register("cliente_id")}
              >
                <option value="">Sem cliente</option>
                {clientes?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setNovoClienteAberto(true)}
                className="flex items-center gap-1 rounded-lg border px-3 py-2.5 text-sm hover:bg-muted shrink-0"
              >
                <UserPlus className="h-4 w-4" />
                Novo
              </button>
            </div>
          ) : (
            <div className="rounded-xl border p-3 space-y-2 bg-muted/20">
              <input
                type="text"
                placeholder="Nome do cliente"
                value={novoClienteNome}
                onChange={(e) => setNovoClienteNome(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                autoFocus
              />
              <input
                type="tel"
                placeholder="Telefone (opcional)"
                value={novoClienteTelefone}
                onChange={(e) => setNovoClienteTelefone(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={criarClienteInline}
                  disabled={!novoClienteNome.trim() || criarCliente.isPending}
                  className="flex-1 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
                >
                  {criarCliente.isPending ? "Salvando..." : "Salvar cliente"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNovoClienteAberto(false);
                    setNovoClienteNome("");
                    setNovoClienteTelefone("");
                  }}
                  className="rounded-lg border px-3 py-2 text-sm hover:bg-muted"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Data entrega */}
        <section className="space-y-1">
          <label className="text-sm font-medium">Data de entrega</label>
          <input
            type="date"
            className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            {...register("data_entrega")}
          />
        </section>

        {/* Itens */}
        <section className="space-y-3">
          <h2 className="font-semibold">Itens do pedido</h2>
          {!receitas?.length && (
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
              Você ainda não tem receitas cadastradas.{" "}
              <Link href="/receitas/nova" className="underline font-medium">
                Cadastrar agora
              </Link>
            </div>
          )}

          {fields.map((field, index) => {
            const subtotal =
              (itensWatch[index]?.quantidade || 0) * (itensWatch[index]?.preco_unitario || 0);
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
                      {receitas?.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.nome}
                        </option>
                      ))}
                    </select>
                  )}
                />
                {errors.itens?.[index]?.receita_id && (
                  <p className="text-xs text-destructive">
                    {errors.itens[index]?.receita_id?.message}
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

        {/* Observações */}
        <section className="space-y-1">
          <label className="text-sm font-medium">Observações do pedido</label>
          <textarea
            rows={3}
            placeholder="Detalhes, decoração, alergias, etc."
            className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
            {...register("observacoes")}
          />
        </section>

        {/* Total */}
        <div className="rounded-xl bg-primary/5 border border-primary/20 p-4 flex items-center justify-between">
          <span className="font-medium">Total do pedido</span>
          <span className="font-bold text-lg text-primary">{formatMoney(valorTotal)}</span>
        </div>

        {criarPedido.isError && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            Não foi possível criar o pedido. Verifique os dados.
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || criarPedido.isPending}
          className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting || criarPedido.isPending ? "Salvando..." : "Criar pedido"}
        </button>
      </form>
    </div>
  );
}
