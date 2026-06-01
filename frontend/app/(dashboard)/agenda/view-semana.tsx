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
import { useMoverAgendaItem } from "@/hooks/use-agenda";
import {
  diasDaSemana,
  mesmoDia,
  nomeDiaSemana,
  toDateKey,
} from "@/lib/agenda";
import { cn } from "@/lib/utils";
import {
  ALTURA_TIMELINE,
  BlocoAgenda,
  CelulaHora,
  ColunaHoras,
  FaixaDiaInteiro,
  LinhaAgora,
  parseCellId,
} from "@/components/shared/agenda-timeline";
import { AgendaItemChip } from "@/components/shared/agenda-item-chip";
import { HORAS_GRADE } from "@/lib/agenda";
import type { AgendaItem } from "@/types";
import { calcularMover } from "./mover";

interface Props {
  itens: AgendaItem[];
  dataRef: Date;
  onItemClick: (item: AgendaItem) => void;
  onCriar: (dataKey: string, hora?: string | null) => void;
}

export function ViewSemana({ itens, dataRef, onItemClick, onCriar }: Props) {
  const dias = diasDaSemana(dataRef);
  const hoje = new Date();
  const mover = useMoverAgendaItem();
  const [arrastando, setArrastando] = useState<AgendaItem | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const porDia = (dataKey: string) =>
    itens.filter((i) => i.data === dataKey);

  const onDragStart = (e: DragStartEvent) => {
    setArrastando(itens.find((i) => i.id === e.active.id) ?? null);
  };

  const onDragEnd = (e: DragEndEvent) => {
    setArrastando(null);
    if (!e.over) return;
    const alvo = parseCellId(String(e.over.id));
    const item = itens.find((i) => i.id === e.active.id);
    if (!alvo || !item) return;
    const payload = calcularMover(item, alvo.dataKey, alvo.hora);
    mover.mutate({ id: item.id, payload });
  };

  return (
    <DndContext
      sensors={sensors}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
    >
      <div className="overflow-x-auto">
        <div className="flex min-w-[640px]">
          {/* Coluna de horas */}
          <div className="shrink-0 pt-[68px]">
            <ColunaHoras />
          </div>

          {/* Colunas dos dias */}
          {dias.map((dia) => {
            const dataKey = toDateKey(dia);
            const doDia = porDia(dataKey);
            const diaInteiro = doDia.filter((i) => !i.hora_inicio);
            const comHora = doDia.filter((i) => i.hora_inicio);
            const ehHoje = mesmoDia(dia, hoje);
            return (
              <div key={dataKey} className="flex-1 min-w-[88px] border-l">
                {/* Cabeçalho do dia */}
                <div
                  className={cn(
                    "h-[68px] border-b px-1 py-1 text-center",
                    ehHoje && "bg-primary/5"
                  )}
                >
                  <p className="text-[11px] uppercase text-muted-foreground">
                    {nomeDiaSemana(dia.getDay())}
                  </p>
                  <p
                    className={cn(
                      "mx-auto mt-0.5 flex h-6 w-6 items-center justify-center rounded-full text-sm font-semibold",
                      ehHoje && "bg-primary text-primary-foreground"
                    )}
                  >
                    {dia.getDate()}
                  </p>
                  <FaixaDiaInteiro itens={diaInteiro} onItemClick={onItemClick} />
                </div>

                {/* Linha do tempo */}
                <div className="relative" style={{ height: ALTURA_TIMELINE }}>
                  {HORAS_GRADE.map((h) => (
                    <CelulaHora
                      key={h}
                      dataKey={dataKey}
                      hora={h}
                      onClick={() =>
                        onCriar(dataKey, `${String(h).padStart(2, "0")}:00`)
                      }
                    />
                  ))}
                  <LinhaAgora visivel={ehHoje} />
                  {comHora.map((item) => (
                    <BlocoAgenda
                      key={item.id}
                      item={item}
                      onClick={() => onItemClick(item)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <DragOverlay>
        {arrastando ? (
          <div className="opacity-90">
            <AgendaItemChip item={arrastando} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
