"use client";

import { useDraggable, useDroppable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import {
  corDoItem,
  formatHora,
  HORA_INICIO_GRADE,
  HORAS_GRADE,
  minutosDoDia,
} from "@/lib/agenda";
import { cn } from "@/lib/utils";
import type { AgendaItem } from "@/types";

/** Altura em pixels de uma hora na linha do tempo. */
export const PX_POR_HORA = 56;
/** Altura mínima de um bloco (≈30 min). */
export const ALTURA_MIN_BLOCO = 40;

export function topoDoBloco(horaInicio: string): number {
  const min = minutosDoDia(horaInicio) - HORA_INICIO_GRADE * 60;
  return (min / 60) * PX_POR_HORA;
}

export function alturaDoBloco(duracaoMin: number | null): number {
  if (!duracaoMin) return ALTURA_MIN_BLOCO;
  return Math.max(ALTURA_MIN_BLOCO, (duracaoMin / 60) * PX_POR_HORA);
}

export const ALTURA_TIMELINE = HORAS_GRADE.length * PX_POR_HORA;

/** id de droppable de uma célula = "cell:<dataKey>:<hora>". */
export function cellId(dataKey: string, hora: number): string {
  return `cell:${dataKey}:${hora}`;
}

export function parseCellId(
  id: string
): { dataKey: string; hora: number } | null {
  if (!id.startsWith("cell:")) return null;
  const [, dataKey, hora] = id.split(":");
  return { dataKey, hora: Number(hora) };
}

/** Coluna de rótulos de hora (06h–23h). */
export function ColunaHoras() {
  return (
    <div className="relative w-12 shrink-0" style={{ height: ALTURA_TIMELINE }}>
      {HORAS_GRADE.map((h, i) => (
        <div
          key={h}
          className="absolute right-1 -translate-y-1/2 text-[10px] text-muted-foreground tabular-nums"
          style={{ top: i * PX_POR_HORA }}
        >
          {String(h).padStart(2, "0")}h
        </div>
      ))}
    </div>
  );
}

interface BlocoProps {
  item: AgendaItem;
  onClick: () => void;
  detalhado?: boolean;
}

/** Bloco posicionado e arrastável de um item com horário. */
export function BlocoAgenda({ item, onClick, detalhado }: BlocoProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: item.id });
  const cor = corDoItem(item);
  const top = item.hora_inicio ? topoDoBloco(item.hora_inicio) : 0;
  const altura = alturaDoBloco(item.duracao_minutos);
  const subtitulo = item.nome_receita ?? item.nome_pedido;

  return (
    <button
      ref={setNodeRef}
      type="button"
      onClick={onClick}
      {...listeners}
      {...attributes}
      style={{
        top,
        height: altura,
        backgroundColor: cor,
        transform: CSS.Translate.toString(transform),
        opacity: isDragging ? 0.7 : item.concluido ? 0.6 : 1,
      }}
      className={cn(
        "absolute left-0.5 right-0.5 overflow-hidden rounded-md px-1.5 py-1 text-left text-[11px] leading-tight text-white shadow-sm touch-none",
        isDragging && "z-20 shadow-lg"
      )}
    >
      <p className={cn("font-semibold truncate", item.concluido && "line-through")}>
        {item.hora_inicio && (
          <span className="tabular-nums opacity-90 mr-1">
            {formatHora(item.hora_inicio)}
          </span>
        )}
        {item.titulo}
      </p>
      {detalhado && subtitulo && (
        <p className="truncate opacity-90">{subtitulo}</p>
      )}
    </button>
  );
}

interface CelulaProps {
  dataKey: string;
  hora: number;
  onClick: () => void;
}

/** Célula droppable de uma hora (e dia). Clicável para criar item. */
export function CelulaHora({ dataKey, hora, onClick }: CelulaProps) {
  const { setNodeRef, isOver } = useDroppable({ id: cellId(dataKey, hora) });
  return (
    <button
      ref={setNodeRef}
      type="button"
      onClick={onClick}
      aria-label={`Adicionar às ${String(hora).padStart(2, "0")}h`}
      className={cn(
        "absolute left-0 right-0 border-t border-border/60 transition-colors hover:bg-primary/5",
        isOver && "bg-primary/15"
      )}
      style={{ top: (hora - HORA_INICIO_GRADE) * PX_POR_HORA, height: PX_POR_HORA }}
    />
  );
}

/** Faixa de itens de dia inteiro (sem hora_inicio) no topo da coluna. */
export function FaixaDiaInteiro({
  itens,
  onItemClick,
}: {
  itens: AgendaItem[];
  onItemClick: (item: AgendaItem) => void;
}) {
  if (!itens.length) return null;
  return (
    <div className="space-y-0.5 p-0.5">
      {itens.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onItemClick(item)}
          style={{ backgroundColor: corDoItem(item), opacity: item.concluido ? 0.6 : 1 }}
          className={cn(
            "block w-full truncate rounded px-1.5 py-0.5 text-left text-[11px] font-medium text-white",
            item.concluido && "line-through"
          )}
        >
          {item.titulo}
        </button>
      ))}
    </div>
  );
}

/** Linha "agora" pontilhada (apenas quando a data exibida é hoje). */
export function LinhaAgora({ visivel }: { visivel: boolean }) {
  if (!visivel) return null;
  const agora = new Date();
  const min = agora.getHours() * 60 + agora.getMinutes() - HORA_INICIO_GRADE * 60;
  if (min < 0 || min > HORAS_GRADE.length * 60) return null;
  const top = (min / 60) * PX_POR_HORA;
  return (
    <div
      className="pointer-events-none absolute left-0 right-0 z-10 border-t-2 border-dashed border-red-500"
      style={{ top }}
    >
      <span className="absolute -left-1 -top-1 h-2 w-2 rounded-full bg-red-500" />
    </div>
  );
}
