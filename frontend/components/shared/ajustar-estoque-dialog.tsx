"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { SlidersHorizontal } from "lucide-react";
import { useAjustarEstoque } from "@/hooks/use-estoque";
import type { Ingrediente } from "@/types";

interface AjustarEstoqueDialogProps {
  item: Ingrediente;
  variant?: "icon" | "button";
}

export function AjustarEstoqueDialog({
  item,
  variant = "icon",
}: AjustarEstoqueDialogProps) {
  const [open, setOpen] = useState(false);
  const [quantidade, setQuantidade] = useState(item.estoque_atual);
  const [erro, setErro] = useState<string | null>(null);
  const ajustar = useAjustarEstoque(item.id);

  const alvo = quantidade.trim() ? Number(quantidade) : Number.NaN;
  const atual = Number(item.estoque_atual);
  const reservado = Number(item.quantidade_reservada);
  const diferenca = alvo - atual;
  const quantidadeValida = Number.isFinite(alvo) && alvo >= reservado;
  const podeSalvar = quantidadeValida && diferenca !== 0 && !ajustar.isPending;

  function abrir(valor: boolean) {
    if (ajustar.isPending) return;
    if (valor) {
      setQuantidade(item.estoque_atual);
      setErro(null);
    }
    setOpen(valor);
  }

  async function salvar(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErro(null);

    if (!Number.isFinite(alvo) || alvo < 0) {
      setErro("Informe uma quantidade válida, igual ou maior que zero.");
      return;
    }
    if (alvo < reservado) {
      setErro(`O novo estoque não pode ficar abaixo de ${formatar(reservado)} ${item.unidade} reservado.`);
      return;
    }
    if (diferenca === 0) {
      setErro("A quantidade informada já corresponde ao estoque atual.");
      return;
    }

    try {
      await ajustar.mutateAsync({ quantidade_alvo: String(alvo) });
      setOpen(false);
    } catch (error) {
      const detalhe = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setErro(
        typeof detalhe === "string"
          ? detalhe
          : error instanceof Error
            ? error.message
            : "Não foi possível ajustar o estoque. Tente novamente."
      );
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={abrir}>
      <Dialog.Trigger asChild>
        {variant === "button" ? (
          <button
            type="button"
            aria-label={`Ajustar estoque de ${item.nome}`}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Ajustar saldo
          </button>
        ) : (
          <button
            type="button"
            aria-label={`Ajustar estoque de ${item.nome}`}
            title="Ajustar estoque"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
          >
            <SlidersHorizontal className="h-4 w-4" />
          </button>
        )}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border bg-background p-5 shadow-xl sm:p-6">
          <form className="space-y-4" onSubmit={(event) => void salvar(event)}>
            <div>
              <Dialog.Title className="text-lg font-semibold">Ajustar estoque</Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                {item.nome} · unidade principal: {item.unidade}
              </Dialog.Description>
            </div>

            <div className="rounded-lg bg-muted/40 p-3 text-sm">
              <p>Estoque cadastrado: <strong>{formatar(atual)} {item.unidade}</strong></p>
              {reservado > 0 && <p className="mt-1 text-muted-foreground">Reservado: {formatar(reservado)} {item.unidade}</p>}
            </div>

            <div className="space-y-1.5">
              <label htmlFor={`quantidade-correta-${item.id}`} className="text-sm font-medium">
                Quantidade correta em estoque ({item.unidade})
              </label>
              <input
                id={`quantidade-correta-${item.id}`}
                type="number"
                inputMode="decimal"
                min={reservado}
                step="0.0001"
                value={quantidade}
                onChange={(event) => {
                  setQuantidade(event.target.value);
                  setErro(null);
                }}
                className="w-full rounded-lg border bg-background px-3 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <p className="text-xs text-muted-foreground">
                Informe o total que existe fisicamente. O sistema registra só a diferença no histórico; a compra original e o custo médio não mudam.
              </p>
            </div>

            {quantidadeValida && diferenca !== 0 && (
              <p className={`rounded-lg p-3 text-sm ${diferenca > 0 ? "bg-green-50 text-green-800" : "bg-orange-50 text-orange-800"}`}>
                {diferenca > 0 ? "O estoque aumentará" : "O estoque diminuirá"} em {formatar(Math.abs(diferenca))} {item.unidade}.
              </p>
            )}
            {quantidadeValida && diferenca === 0 && (
              <p className="rounded-lg bg-muted/40 p-3 text-sm text-muted-foreground">
                Essa quantidade já está cadastrada. Nenhum ajuste será registrado.
              </p>
            )}
            {Number.isFinite(alvo) && alvo < reservado && (
              <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                O novo estoque não pode ficar abaixo de {formatar(reservado)} {item.unidade} reservado.
              </p>
            )}
            {erro && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{erro}</p>}

            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Dialog.Close asChild>
                <button type="button" disabled={ajustar.isPending} className="rounded-lg border px-4 py-2.5 text-sm disabled:opacity-50">
                  Cancelar
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={!podeSalvar}
                className="rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                {ajustar.isPending ? "Salvando..." : "Salvar ajuste"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function formatar(valor: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 4 }).format(valor);
}
