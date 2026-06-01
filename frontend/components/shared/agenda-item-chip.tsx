"use client";

import { Check } from "lucide-react";
import { corDoItem, formatHora, ICONE_TIPO } from "@/lib/agenda";
import { cn } from "@/lib/utils";
import type { AgendaItem } from "@/types";

interface Props {
  item: AgendaItem;
  onClick?: () => void;
  className?: string;
}

/**
 * Chip compacto usado na view mês. Cor de fundo pelo tipo (ou cor customizada),
 * ícone por tipo, título truncado. Itens concluídos ficam riscados e esmaecidos.
 */
export function AgendaItemChip({ item, onClick, className }: Props) {
  const cor = corDoItem(item);
  return (
    <button
      type="button"
      onClick={onClick}
      title={item.titulo}
      className={cn(
        "flex w-full items-center gap-1 rounded px-1.5 py-0.5 text-left text-[11px] font-medium text-white transition-opacity",
        item.concluido && "opacity-60",
        className
      )}
      style={{ backgroundColor: cor }}
    >
      <span aria-hidden className="shrink-0 text-[10px] leading-none">
        {item.concluido ? <Check className="h-3 w-3" /> : ICONE_TIPO[item.tipo]}
      </span>
      {item.hora_inicio && (
        <span className="shrink-0 tabular-nums opacity-90">
          {formatHora(item.hora_inicio)}
        </span>
      )}
      <span className={cn("truncate", item.concluido && "line-through")}>
        {item.titulo}
      </span>
    </button>
  );
}
