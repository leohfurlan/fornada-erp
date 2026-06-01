"use client";

import { useState } from "react";
import Link from "next/link";
import { Calendar, Check, Clock, ExternalLink, Pencil, Trash2, X } from "lucide-react";
import { useDeletarAgendaItem, useMarcarConcluido } from "@/hooks/use-agenda";
import { corDoItem, fromDateKey, formatHora, LABEL_TIPO } from "@/lib/agenda";
import { cn } from "@/lib/utils";
import type { AgendaItem } from "@/types";

interface Props {
  item: AgendaItem;
  onClose: () => void;
  onEdit: (item: AgendaItem) => void;
}

function dataLonga(dataKey: string): string {
  const d = fromDateKey(dataKey);
  return d.toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  });
}

export function AgendaItemDrawer({ item, onClose, onEdit }: Props) {
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);
  const marcar = useMarcarConcluido();
  const deletar = useDeletarAgendaItem();
  const cor = corDoItem(item);

  const handleConcluir = () => {
    marcar.mutate({ id: item.id, concluido: !item.concluido });
  };

  const handleExcluir = async () => {
    await deletar.mutateAsync(item.id);
    onClose();
  };

  const horario =
    item.hora_inicio && item.hora_fim
      ? `${formatHora(item.hora_inicio)} – ${formatHora(item.hora_fim)}`
      : item.hora_inicio
        ? formatHora(item.hora_inicio)
        : "Dia inteiro";

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden />
      <div className="relative z-10 flex w-full max-w-lg flex-col rounded-t-2xl bg-background shadow-xl sm:rounded-2xl max-h-[92vh]">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 p-4 pb-2">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="inline-block h-3 w-3 shrink-0 rounded-full"
              style={{ backgroundColor: cor }}
              aria-hidden
            />
            <span
              className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
              style={{ backgroundColor: cor }}
            >
              {LABEL_TIPO[item.tipo]}
            </span>
            {item.concluido && (
              <span className="rounded-full bg-green-100 text-green-800 px-2 py-0.5 text-xs font-medium">
                Concluído
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-muted -mt-1 -mr-1"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Conteúdo */}
        <div className="flex-1 overflow-y-auto px-4 pb-2 space-y-3">
          <h2
            className={cn(
              "text-xl font-bold",
              item.concluido && "line-through text-muted-foreground"
            )}
          >
            {item.titulo}
          </h2>

          <div className="space-y-1.5 text-sm">
            <p className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4 shrink-0" />
              <span className="capitalize">{dataLonga(item.data)}</span>
            </p>
            <p className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4 shrink-0" />
              {horario}
              {item.duracao_minutos ? (
                <span className="text-xs">({item.duracao_minutos} min)</span>
              ) : null}
            </p>
          </div>

          {/* Vínculos */}
          {item.receita_id && item.nome_receita && (
            <Link
              href={`/receitas/${item.receita_id}`}
              className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2 text-sm hover:bg-muted"
            >
              <span>
                <span className="text-muted-foreground">Receita: </span>
                <span className="font-medium">{item.nome_receita}</span>
              </span>
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
            </Link>
          )}
          {item.pedido_id && item.nome_pedido && (
            <Link
              href={`/pedidos/${item.pedido_id}`}
              className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2 text-sm hover:bg-muted"
            >
              <span className="font-medium">{item.nome_pedido}</span>
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
            </Link>
          )}
          {item.numero_op && (
            <div className="rounded-lg border bg-muted/30 px-3 py-2 text-sm">
              <span className="text-muted-foreground">Ordem de produção: </span>
              <span className="font-medium">
                #{String(item.numero_op).padStart(3, "0")}
              </span>
            </div>
          )}

          {item.observacoes && (
            <div className="rounded-lg bg-muted/30 px-3 py-2 text-sm whitespace-pre-wrap">
              {item.observacoes}
            </div>
          )}

          {/* Ações secundárias */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => onEdit(item)}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border py-2 text-sm font-medium hover:bg-muted"
            >
              <Pencil className="h-4 w-4" />
              Editar
            </button>
            {confirmandoExclusao ? (
              <button
                type="button"
                onClick={handleExcluir}
                disabled={deletar.isPending}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-destructive py-2 text-sm font-medium text-destructive-foreground disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" />
                {deletar.isPending ? "Excluindo…" : "Confirmar exclusão"}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmandoExclusao(true)}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-destructive/30 py-2 text-sm font-medium text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4" />
                Excluir
              </button>
            )}
          </div>
        </div>

        {/* Concluir — grande e tátil no rodapé (acesso com o polegar). */}
        <div className="p-4 pt-2 border-t">
          <button
            type="button"
            onClick={handleConcluir}
            disabled={marcar.isPending}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-xl py-4 text-base font-semibold transition-colors disabled:opacity-50",
              item.concluido
                ? "bg-muted text-foreground hover:bg-muted/70"
                : "bg-green-600 text-white hover:bg-green-700"
            )}
          >
            <Check className="h-5 w-5" />
            {item.concluido ? "Marcar como pendente" : "Marcar como concluído"}
          </button>
        </div>
      </div>
    </div>
  );
}
