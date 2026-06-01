"use client";

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { useState } from "react";
import { useMoverAgendaItem } from "@/hooks/use-agenda";
import { gradeDoMes, mesmoDia, toDateKey } from "@/lib/agenda";
import { cn } from "@/lib/utils";
import { AgendaItemChip } from "@/components/shared/agenda-item-chip";
import type { AgendaItem } from "@/types";
import { calcularMoverDia } from "./mover";

const DIAS_CABECALHO = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const MAX_CHIPS = 3;

interface Props {
  itens: AgendaItem[];
  dataRef: Date;
  onItemClick: (item: AgendaItem) => void;
  onSelectDia: (data: Date) => void;
}

function dayDroppableId(dataKey: string): string {
  return `day:${dataKey}`;
}

export function ViewMes({ itens, dataRef, onItemClick, onSelectDia }: Props) {
  const semanas = gradeDoMes(dataRef);
  const hoje = new Date();
  const mover = useMoverAgendaItem();
  const [arrastando, setArrastando] = useState<AgendaItem | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const porDia = (dataKey: string) => itens.filter((i) => i.data === dataKey);

  const onDragStart = (e: DragStartEvent) =>
    setArrastando(itens.find((i) => i.id === e.active.id) ?? null);

  const onDragEnd = (e: DragEndEvent) => {
    setArrastando(null);
    if (!e.over) return;
    const overId = String(e.over.id);
    if (!overId.startsWith("day:")) return;
    const dataKey = overId.slice(4);
    const item = itens.find((i) => i.id === e.active.id);
    if (!item || item.data === dataKey) return;
    mover.mutate({ id: item.id, payload: calcularMoverDia(item, dataKey) });
  };

  return (
    <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <div className="grid grid-cols-7 border-l border-t">
        {DIAS_CABECALHO.map((d) => (
          <div
            key={d}
            className="border-b border-r bg-muted/30 py-1.5 text-center text-[11px] font-medium uppercase text-muted-foreground"
          >
            {d}
          </div>
        ))}
        {semanas.flat().map((dia) => {
          const dataKey = toDateKey(dia);
          const doDia = porDia(dataKey);
          const noMes = dia.getMonth() === dataRef.getMonth();
          const ehHoje = mesmoDia(dia, hoje);
          const temPedido = doDia.some((i) => i.tipo === "pedido");
          return (
            <CelulaDia
              key={dataKey}
              dataKey={dataKey}
              noMes={noMes}
              ehHoje={ehHoje}
              numero={dia.getDate()}
              temPedido={temPedido}
              itens={doDia}
              onAbrirDia={() => onSelectDia(dia)}
              onItemClick={onItemClick}
            />
          );
        })}
      </div>

      <DragOverlay>
        {arrastando ? (
          <div className="w-32 opacity-90">
            <AgendaItemChip item={arrastando} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

interface CelulaProps {
  dataKey: string;
  noMes: boolean;
  ehHoje: boolean;
  numero: number;
  temPedido: boolean;
  itens: AgendaItem[];
  onAbrirDia: () => void;
  onItemClick: (item: AgendaItem) => void;
}

function CelulaDia({
  dataKey,
  noMes,
  ehHoje,
  numero,
  temPedido,
  itens,
  onAbrirDia,
  onItemClick,
}: CelulaProps) {
  const { setNodeRef, isOver } = useDroppable({ id: dayDroppableId(dataKey) });
  const visiveis = itens.slice(0, MAX_CHIPS);
  const extras = itens.length - visiveis.length;

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "min-h-[92px] border-b border-r p-1 text-left align-top",
        !noMes && "bg-muted/20",
        isOver && "bg-primary/10"
      )}
    >
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onAbrirDia}
          className={cn(
            "flex h-6 w-6 items-center justify-center rounded-full text-xs",
            ehHoje
              ? "bg-primary font-semibold text-primary-foreground"
              : noMes
                ? "text-foreground hover:bg-muted"
                : "text-muted-foreground hover:bg-muted"
          )}
        >
          {numero}
        </button>
        {temPedido && (
          <span aria-label="Entrega de pedido" title="Entrega de pedido">
            🎂
          </span>
        )}
      </div>
      <div className="mt-0.5 space-y-0.5">
        {visiveis.map((item) => (
          <ChipDraggable key={item.id} item={item} onClick={() => onItemClick(item)} />
        ))}
        {extras > 0 && (
          <button
            type="button"
            onClick={onAbrirDia}
            className="w-full rounded px-1 text-left text-[10px] font-medium text-muted-foreground hover:text-foreground"
          >
            +{extras} mais
          </button>
        )}
      </div>
    </div>
  );
}

function ChipDraggable({
  item,
  onClick,
}: {
  item: AgendaItem;
  onClick: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: item.id });
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      style={{
        transform: CSS.Translate.toString(transform),
        opacity: isDragging ? 0.5 : 1,
      }}
      className="touch-none"
    >
      <AgendaItemChip item={item} onClick={onClick} />
    </div>
  );
}
