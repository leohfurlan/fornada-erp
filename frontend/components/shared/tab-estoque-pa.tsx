"use client";

import Link from "next/link";
import { useState } from "react";
import { ChefHat, History, Pencil } from "lucide-react";
import { useAtualizarMinimaPA, useEstoquePA } from "@/hooks/use-estoque-pa";
import { DecimalInput } from "@/components/shared/decimal-input";
import { cn, formatQuantidade } from "@/lib/utils";
import type { EstoquePA } from "@/types";

const STATUS_CONFIG: Record<EstoquePA["status"], { label: string; className: string }> = {
  ok: { label: "OK", className: "bg-green-100 text-green-800" },
  baixo: { label: "Baixo", className: "bg-orange-100 text-orange-800" },
  zerado: { label: "Zerado", className: "bg-red-100 text-red-800" },
};

export function TabEstoquePA() {
  const { data: saldos, isLoading, error } = useEstoquePA();
  const [editandoId, setEditandoId] = useState<string | null>(null);

  if (error) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar o estoque de produtos prontos.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (!saldos?.length) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
        <ChefHat className="h-10 w-10 mx-auto mb-2 text-muted-foreground/40" />
        <p className="font-medium">Nenhum produto pronto em estoque</p>
        <p className="text-sm mt-1">
          O saldo aparece automaticamente quando uma ordem de produção é finalizada
        </p>
        <Link
          href="/producao/nova"
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Nova ordem de produção
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {saldos.map((s) => (
        <CardSaldoPA
          key={s.receita_id}
          saldo={s}
          editando={editandoId === s.receita_id}
          onEditar={() => setEditandoId(s.receita_id)}
          onCancelar={() => setEditandoId(null)}
        />
      ))}
    </div>
  );
}

interface CardProps {
  saldo: EstoquePA;
  editando: boolean;
  onEditar: () => void;
  onCancelar: () => void;
}

function CardSaldoPA({ saldo, editando, onEditar, onCancelar }: CardProps) {
  const status = STATUS_CONFIG[saldo.status];
  const atualizar = useAtualizarMinimaPA(saldo.receita_id);
  const [valor, setValor] = useState<number>(parseFloat(saldo.qtd_minima));

  const salvar = async () => {
    await atualizar.mutateAsync({ qtd_minima: valor });
    onCancelar();
  };

  return (
    <div className="rounded-xl border bg-card p-4 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-medium truncate">{saldo.nome_receita}</p>
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                status.className
              )}
            >
              {status.label}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Disponível:{" "}
            <span className="font-medium text-foreground">
              {formatQuantidade(saldo.qtd_disponivel)} un
            </span>
            {parseFloat(saldo.qtd_minima) > 0 && (
              <> · mínimo {formatQuantidade(saldo.qtd_minima)} un</>
            )}
          </p>
        </div>
        <div className="flex gap-1 shrink-0">
          <Link
            href={`/estoque/pa/${saldo.receita_id}/historico`}
            className="p-1.5 rounded-md hover:bg-muted text-muted-foreground"
            title="Histórico"
          >
            <History className="h-4 w-4" />
          </Link>
          {!editando && (
            <button
              type="button"
              onClick={onEditar}
              className="p-1.5 rounded-md hover:bg-muted text-muted-foreground"
              title="Ajustar mínimo"
            >
              <Pencil className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {editando && (
        <div className="border-t pt-3 space-y-2">
          <label className="text-xs text-muted-foreground">
            Quantidade mínima (alerta de baixo estoque)
          </label>
          <div className="flex gap-2">
            <div className="flex-1">
              <DecimalInput value={valor} onChange={setValor} placeholder="0" />
            </div>
            <button
              type="button"
              onClick={salvar}
              disabled={atualizar.isPending}
              className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
            >
              {atualizar.isPending ? "..." : "Salvar"}
            </button>
            <button
              type="button"
              onClick={onCancelar}
              className="rounded-lg border px-3 py-2 text-sm hover:bg-muted"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
