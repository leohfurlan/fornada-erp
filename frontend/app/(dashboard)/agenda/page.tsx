"use client";

import { useState } from "react";
import { CalendarPlus, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { useAgenda } from "@/hooks/use-agenda";
import {
  adicionarDias,
  adicionarMeses,
  tituloPeriodo,
  toDateKey,
} from "@/lib/agenda";
import { cn } from "@/lib/utils";
import { AgendaItemDrawer } from "@/components/shared/agenda-item-drawer";
import { AgendaItemModal } from "@/components/shared/agenda-item-modal";
import type { AgendaItem, ViewAgenda } from "@/types";
import { ViewMes } from "./view-mes";
import { ViewSemana } from "./view-semana";
import { ViewDia } from "./view-dia";

const VIEWS: { value: ViewAgenda; label: string }[] = [
  { value: "mes", label: "Mês" },
  { value: "semana", label: "Semana" },
  { value: "dia", label: "Dia" },
];

interface ModalConfig {
  open: boolean;
  item?: AgendaItem | null;
  dataInicial?: string;
  horaInicial?: string | null;
}

export default function AgendaPage() {
  const [view, setView] = useState<ViewAgenda>("semana");
  const [dataRef, setDataRef] = useState<Date>(() => new Date());
  const [drawerItem, setDrawerItem] = useState<AgendaItem | null>(null);
  const [modal, setModal] = useState<ModalConfig>({ open: false });

  const { data: itens, isLoading, error } = useAgenda(view, dataRef);

  const navegar = (dir: -1 | 1) => {
    if (view === "mes") setDataRef((d) => adicionarMeses(d, dir));
    else if (view === "semana") setDataRef((d) => adicionarDias(d, dir * 7));
    else setDataRef((d) => adicionarDias(d, dir));
  };

  const abrirCriar = (dataKey?: string, hora?: string | null) =>
    setModal({
      open: true,
      item: null,
      dataInicial: dataKey ?? toDateKey(dataRef),
      horaInicial: hora ?? null,
    });

  const abrirEdicao = (item: AgendaItem) => {
    setDrawerItem(null);
    setModal({ open: true, item });
  };

  const abrirDia = (data: Date) => {
    setDataRef(data);
    setView("dia");
  };

  const vazio = !isLoading && !error && (itens?.length ?? 0) === 0;

  return (
    <div className="space-y-4">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-xl font-bold">Agenda</h1>
        <button
          type="button"
          onClick={() => abrirCriar()}
          className="hidden items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground sm:flex"
        >
          <Plus className="h-4 w-4" />
          Nova atividade
        </button>
      </div>

      {/* Navegação de período + tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => navegar(-1)}
            className="rounded-lg p-2 hover:bg-muted"
            aria-label="Período anterior"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="min-w-[150px] text-center text-sm font-semibold capitalize">
            {tituloPeriodo(view, dataRef)}
          </span>
          <button
            type="button"
            onClick={() => navegar(1)}
            className="rounded-lg p-2 hover:bg-muted"
            aria-label="Próximo período"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setDataRef(new Date())}
            className="ml-1 rounded-lg border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Hoje
          </button>
        </div>

        <div className="flex rounded-lg border p-0.5 text-sm">
          {VIEWS.map((v) => (
            <button
              key={v.value}
              type="button"
              onClick={() => setView(v.value)}
              className={cn(
                "rounded-md px-3 py-1 font-medium transition-colors",
                view === v.value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* Conteúdo */}
      {error ? (
        <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
          Não foi possível carregar a agenda.
        </div>
      ) : isLoading ? (
        <div className="h-64 animate-pulse rounded-xl bg-muted" />
      ) : vazio ? (
        <EmptyState onAdicionar={() => abrirCriar()} />
      ) : (
        <>
          {view === "mes" && (
            <ViewMes
              itens={itens ?? []}
              dataRef={dataRef}
              onItemClick={setDrawerItem}
              onSelectDia={abrirDia}
            />
          )}
          {view === "semana" && (
            <ViewSemana
              itens={itens ?? []}
              dataRef={dataRef}
              onItemClick={setDrawerItem}
              onCriar={abrirCriar}
            />
          )}
          {view === "dia" && (
            <ViewDia
              itens={itens ?? []}
              dataRef={dataRef}
              onItemClick={setDrawerItem}
              onCriar={abrirCriar}
            />
          )}
        </>
      )}

      {/* FAB mobile */}
      <button
        type="button"
        onClick={() => abrirCriar()}
        className="fixed bottom-20 right-4 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg sm:hidden"
        aria-label="Nova atividade"
      >
        <Plus className="h-6 w-6" />
      </button>

      {drawerItem && (
        <AgendaItemDrawer
          item={drawerItem}
          onClose={() => setDrawerItem(null)}
          onEdit={abrirEdicao}
        />
      )}

      <AgendaItemModal
        open={modal.open}
        onClose={() => setModal({ open: false })}
        item={modal.item}
        dataInicial={modal.dataInicial}
        horaInicial={modal.horaInicial}
      />
    </div>
  );
}

function EmptyState({ onAdicionar }: { onAdicionar: () => void }) {
  return (
    <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">
      <CalendarPlus className="mx-auto mb-2 h-10 w-10 text-muted-foreground/40" />
      <p className="font-medium text-foreground">Nenhuma atividade planejada</p>
      <p className="mt-1 text-sm">
        Toque em + para adicionar sua primeira tarefa do dia
      </p>
      <button
        type="button"
        onClick={onAdicionar}
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        <Plus className="h-4 w-4" />
        Planejar atividade
      </button>
    </div>
  );
}
