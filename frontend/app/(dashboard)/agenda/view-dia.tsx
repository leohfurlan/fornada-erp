"use client";

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useState } from "react";
import { Plus } from "lucide-react";
import { useMoverAgendaItem } from "@/hooks/use-agenda";
import { HORAS_GRADE, mesmoDia, toDateKey } from "@/lib/agenda";
import {
  ALTURA_TIMELINE,
  BlocoAgenda,
  CelulaHora,
  ColunaHoras,
  FaixaDiaInteiro,
  LinhaAgora,
  parseCellId,
  PX_POR_HORA,
} from "@/components/shared/agenda-timeline";
import { AgendaItemChip } from "@/components/shared/agenda-item-chip";
import type { AgendaItem } from "@/types";
import { calcularMover } from "./mover";

interface Props {
  itens: AgendaItem[];
  dataRef: Date;
  onItemClick: (item: AgendaItem) => void;
  onCriar: (dataKey: string, hora?: string | null) => void;
}

export function ViewDia({ itens, dataRef, onItemClick, onCriar }: Props) {
  const dataKey = toDateKey(dataRef);
  const ehHoje = mesmoDia(dataRef, new Date());
  const mover = useMoverAgendaItem();
  const [arrastando, setArrastando] = useState<AgendaItem | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const doDia = itens.filter((i) => i.data === dataKey);
  const diaInteiro = doDia.filter((i) => !i.hora_inicio);
  const comHora = doDia.filter((i) => i.hora_inicio);

  const onDragStart = (e: DragStartEvent) =>
    setArrastando(itens.find((i) => i.id === e.active.id) ?? null);

  const onDragEnd = (e: DragEndEvent) => {
    setArrastando(null);
    if (!e.over) return;
    const alvo = parseCellId(String(e.over.id));
    const item = itens.find((i) => i.id === e.active.id);
    if (!alvo || !item) return;
    mover.mutate({ id: item.id, payload: calcularMover(item, alvo.dataKey, alvo.hora) });
  };

  return (
    <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      {diaInteiro.length > 0 && (
        <div className="mb-2 rounded-lg border bg-muted/20">
          <p className="px-2 pt-1.5 text-[11px] font-medium uppercase text-muted-foreground">
            Dia inteiro
          </p>
          <FaixaDiaInteiro itens={diaInteiro} onItemClick={onItemClick} />
        </div>
      )}

      <div className="flex">
        <ColunaHoras />
        <div className="relative flex-1 border-l" style={{ height: ALTURA_TIMELINE }}>
          {HORAS_GRADE.map((h) => (
            <div key={h} className="group">
              <CelulaHora
                dataKey={dataKey}
                hora={h}
                onClick={() => onCriar(dataKey, `${String(h).padStart(2, "0")}:00`)}
              />
              <button
                type="button"
                onClick={() => onCriar(dataKey, `${String(h).padStart(2, "0")}:00`)}
                aria-label={`Adicionar às ${String(h).padStart(2, "0")}h`}
                className="absolute right-1 hidden -translate-y-1/2 items-center gap-0.5 rounded bg-primary px-1.5 py-0.5 text-[10px] font-medium text-primary-foreground group-hover:flex"
                style={{ top: (h - HORAS_GRADE[0]) * PX_POR_HORA + PX_POR_HORA / 2 }}
              >
                <Plus className="h-3 w-3" />
              </button>
            </div>
          ))}
          <LinhaAgora visivel={ehHoje} />
          {comHora.map((item) => (
            <BlocoAgenda
              key={item.id}
              item={item}
              detalhado
              onClick={() => onItemClick(item)}
            />
          ))}
        </div>
      </div>

      <DragOverlay>
        {arrastando ? (
          <div className="w-40 opacity-90">
            <AgendaItemChip item={arrastando} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
