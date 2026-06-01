"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, X } from "lucide-react";
import { LABEL_TIPO, PALETA_CORES, somaMinutos } from "@/lib/agenda";
import { cn } from "@/lib/utils";
import {
  useAtualizarAgendaItem,
  useCriarAgendaItem,
} from "@/hooks/use-agenda";
import { useEtapasPadrao } from "@/hooks/use-configuracoes";
import { usePedidos } from "@/hooks/use-pedidos";
import { useOrdensProducao } from "@/hooks/use-producao";
import { useReceitas } from "@/hooks/use-receitas";
import type {
  AgendaItem,
  ApiError,
  CriarAgendaItemPayload,
  TipoAgendaItem,
} from "@/types";
import type { AxiosError } from "axios";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Quando presente, o modal abre em modo edição. */
  item?: AgendaItem | null;
  /** Pré-preenche data ao criar a partir de uma célula da grade. */
  dataInicial?: string;
  /** Pré-preenche hora de início ao criar a partir de uma célula da grade. */
  horaInicial?: string | null;
}

interface FormState {
  tipo: TipoAgendaItem;
  titulo: string;
  receita_id: string;
  pedido_id: string;
  data: string;
  diaInteiro: boolean;
  hora_inicio: string;
  hora_fim: string;
  cor: string;
  observacoes: string;
  ordem_producao_id: string;
}

const TIPOS: TipoAgendaItem[] = ["receita", "pedido", "tarefa"];

function estadoInicial(
  item: Props["item"],
  dataInicial?: string,
  horaInicial?: string | null
): FormState {
  if (item) {
    return {
      tipo: item.tipo,
      titulo: item.titulo,
      receita_id: item.receita_id ?? "",
      pedido_id: item.pedido_id ?? "",
      data: item.data,
      diaInteiro: !item.hora_inicio,
      hora_inicio: item.hora_inicio ? item.hora_inicio.slice(0, 5) : "08:00",
      hora_fim: item.hora_fim ? item.hora_fim.slice(0, 5) : "09:00",
      cor: item.cor ?? "",
      observacoes: item.observacoes ?? "",
      ordem_producao_id: item.ordem_producao_id ?? "",
    };
  }
  return {
    tipo: "tarefa",
    titulo: "",
    receita_id: "",
    pedido_id: "",
    data: dataInicial ?? new Date().toISOString().slice(0, 10),
    diaInteiro: !horaInicial,
    hora_inicio: horaInicial ? horaInicial.slice(0, 5) : "08:00",
    hora_fim: horaInicial ? somaUmaHora(horaInicial.slice(0, 5)) : "09:00",
    cor: "",
    observacoes: "",
    ordem_producao_id: "",
  };
}

function somaUmaHora(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const novo = (h + 1) % 24;
  return `${String(novo).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function AgendaItemModal({
  open,
  onClose,
  item,
  dataInicial,
  horaInicial,
}: Props) {
  const isEdicao = !!item;
  const [form, setForm] = useState<FormState>(() =>
    estadoInicial(item, dataInicial, horaInicial)
  );

  // Reinicia o formulário sempre que o modal abre com um item/data diferente.
  useEffect(() => {
    if (open) setForm(estadoInicial(item, dataInicial, horaInicial));
  }, [open, item, dataInicial, horaInicial]);

  const { data: receitas } = useReceitas();
  const { data: pedidos } = usePedidos();
  const { data: ordensProducao } = useOrdensProducao();
  const { data: etapasPadrao } = useEtapasPadrao();
  const criar = useCriarAgendaItem();
  const atualizar = useAtualizarAgendaItem(item?.id ?? "");
  const mutation = isEdicao ? atualizar : criar;

  const set = <K extends keyof FormState>(campo: K, valor: FormState[K]) =>
    setForm((f) => ({ ...f, [campo]: valor }));

  // Sugestões de tarefa = etapas padrão de mão de obra indireta (MOI):
  // lavar louça, ir ao mercado, organizar ingredientes etc.
  const sugestoesTarefa = useMemo(
    () => etapasPadrao?.filter((e) => e.tipo_mao_obra === "indireta") ?? [],
    [etapasPadrao]
  );

  const tituloAuto = useMemo(() => {
    if (form.tipo === "receita") {
      return receitas?.find((r) => r.id === form.receita_id)?.nome ?? "";
    }
    if (form.tipo === "pedido") {
      const p = pedidos?.find((p) => p.id === form.pedido_id);
      return p ? `Pedido #${String(p.numero).padStart(3, "0")}` : "";
    }
    return form.titulo;
  }, [form.tipo, form.receita_id, form.pedido_id, form.titulo, receitas, pedidos]);

  // Recalcula hora_fim quando a receita selecionada ou hora_inicio mudam.
  // Apenas sugere o valor — o campo continua editável manualmente.
  useEffect(() => {
    if (form.diaInteiro || !form.receita_id || !form.hora_inicio) return;
    const receita = receitas?.find((r) => r.id === form.receita_id);
    const minutos = receita?.custo?.tempo_total_minutos;
    if (!minutos || minutos <= 0) return;
    setForm((f) => ({ ...f, hora_fim: somaMinutos(f.hora_inicio, minutos) }));
  }, [form.receita_id, form.hora_inicio, form.diaInteiro, receitas]);

  const erro = mutation.error as AxiosError<ApiError> | null;
  const mensagem = erro?.response?.data?.detail;

  if (!open) return null;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const titulo = (form.tipo === "tarefa" ? form.titulo : tituloAuto).trim();
    if (!titulo) return;

    const payload: CriarAgendaItemPayload = {
      titulo,
      tipo: form.tipo,
      data: form.data,
      hora_inicio: form.diaInteiro ? null : `${form.hora_inicio}:00`,
      hora_fim: form.diaInteiro ? null : `${form.hora_fim}:00`,
      cor: form.cor || null,
      observacoes: form.observacoes.trim() || null,
      receita_id: form.tipo === "receita" ? form.receita_id || null : null,
      pedido_id: form.tipo === "pedido" ? form.pedido_id || null : null,
      ordem_producao_id:
        form.tipo === "receita" && form.ordem_producao_id
          ? form.ordem_producao_id
          : null,
    };

    if (isEdicao) {
      await atualizar.mutateAsync(payload);
    } else {
      await criar.mutateAsync(payload);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden />
      <div className="relative z-10 w-full max-w-lg rounded-t-2xl bg-background p-4 shadow-xl sm:rounded-2xl sm:p-6 max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">
            {isEdicao ? "Editar atividade" : "Nova atividade"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-muted"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {/* Tipo */}
          <div className="grid grid-cols-3 gap-2">
            {TIPOS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => set("tipo", t)}
                className={cn(
                  "rounded-lg border py-2 text-sm font-medium transition-colors",
                  form.tipo === t
                    ? "border-primary bg-primary/10 text-primary"
                    : "hover:bg-muted text-muted-foreground"
                )}
              >
                {LABEL_TIPO[t]}
              </button>
            ))}
          </div>

          {/* Campo dependente do tipo */}
          {form.tipo === "receita" && (
            <div className="space-y-1">
              <label className="text-sm font-medium">Receita</label>
              <select
                className="w-full rounded-lg border px-3 py-2.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                value={form.receita_id}
                onChange={(e) => set("receita_id", e.target.value)}
              >
                <option value="">Selecione...</option>
                {receitas?.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.nome}
                  </option>
                ))}
              </select>
            </div>
          )}

          {form.tipo === "receita" && (
            <div className="space-y-1">
              <label className="text-sm font-medium">
                Ordem de Produção{" "}
                <span className="text-xs font-normal text-muted-foreground">
                  (opcional)
                </span>
              </label>
              <select
                className="w-full rounded-lg border px-3 py-2.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                value={form.ordem_producao_id}
                onChange={(e) => set("ordem_producao_id", e.target.value)}
              >
                <option value="">Sem vínculo com OP</option>
                {ordensProducao
                  ?.filter((op) => !["finalizada", "cancelada"].includes(op.status))
                  .map((op) => (
                    <option key={op.id} value={op.id}>
                      OP #{String(op.numero).padStart(3, "0")} — {op.nome_receita} (
                      {op.status === "em_producao" ? "Em produção" : "Planejada"})
                    </option>
                  ))}
              </select>
              <p className="text-xs text-muted-foreground">
                Vincule uma OP para rastrear este planejamento na produção.
              </p>
            </div>
          )}

          {form.tipo === "pedido" && (
            <div className="space-y-1">
              <label className="text-sm font-medium">Pedido</label>
              <select
                className="w-full rounded-lg border px-3 py-2.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                value={form.pedido_id}
                onChange={(e) => set("pedido_id", e.target.value)}
              >
                <option value="">Selecione...</option>
                {pedidos?.map((p) => (
                  <option key={p.id} value={p.id}>
                    #{String(p.numero).padStart(3, "0")} —{" "}
                    {p.cliente_nome ?? "Sem cliente"}
                    {p.data_entrega ? ` — ${p.data_entrega}` : ""}
                  </option>
                ))}
              </select>
            </div>
          )}

          {form.tipo === "tarefa" && (
            <div className="space-y-1">
              <label className="text-sm font-medium">O que precisa fazer?</label>
              <input
                type="text"
                value={form.titulo}
                onChange={(e) => set("titulo", e.target.value)}
                placeholder="Ex: Ir ao mercado, lavar louça…"
                className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {sugestoesTarefa.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {sugestoesTarefa.map((e) => (
                    <button
                      key={e.id}
                      type="button"
                      onClick={() => set("titulo", e.nome)}
                      className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                    >
                      {e.nome}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Data */}
          <div className="space-y-1">
            <label className="text-sm font-medium">Data</label>
            <input
              type="date"
              value={form.data}
              onChange={(e) => set("data", e.target.value)}
              className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Horário */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => set("diaInteiro", true)}
                className={cn(
                  "flex-1 rounded-lg border py-2 text-sm font-medium",
                  form.diaInteiro
                    ? "border-primary bg-primary/10 text-primary"
                    : "hover:bg-muted text-muted-foreground"
                )}
              >
                Dia inteiro
              </button>
              <button
                type="button"
                onClick={() => set("diaInteiro", false)}
                className={cn(
                  "flex-1 rounded-lg border py-2 text-sm font-medium",
                  !form.diaInteiro
                    ? "border-primary bg-primary/10 text-primary"
                    : "hover:bg-muted text-muted-foreground"
                )}
              >
                Definir horário
              </button>
            </div>
            {!form.diaInteiro && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Início</label>
                  <input
                    type="time"
                    value={form.hora_inicio}
                    onChange={(e) => set("hora_inicio", e.target.value)}
                    className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Fim</label>
                  <input
                    type="time"
                    value={form.hora_fim}
                    onChange={(e) => set("hora_fim", e.target.value)}
                    className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
            )}
            {form.tipo === "receita" &&
              !form.diaInteiro &&
              (() => {
                const receita = receitas?.find((r) => r.id === form.receita_id);
                const minutos = receita?.custo?.tempo_total_minutos;
                if (!minutos || minutos <= 0) return null;
                const horas = Math.floor(minutos / 60);
                const mins = minutos % 60;
                const label =
                  horas > 0
                    ? `${horas}h${mins > 0 ? ` ${mins}min` : ""}`
                    : `${mins}min`;
                return (
                  <p className="text-xs text-muted-foreground">
                    Duração estimada:{" "}
                    <span className="font-medium text-foreground">{label}</span>{" "}
                    (baseado nas etapas da receita)
                  </p>
                );
              })()}
          </div>

          {/* Cor */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Cor</label>
            <div className="flex flex-wrap gap-2">
              {PALETA_CORES.map((c) => (
                <button
                  key={c.hex}
                  type="button"
                  onClick={() => set("cor", form.cor === c.hex ? "" : c.hex)}
                  aria-label={c.nome}
                  className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center ring-offset-2 transition",
                    form.cor === c.hex && "ring-2 ring-foreground"
                  )}
                  style={{ backgroundColor: c.hex }}
                >
                  {form.cor === c.hex && <Check className="h-4 w-4 text-white" />}
                </button>
              ))}
            </div>
          </div>

          {/* Observações */}
          <div className="space-y-1">
            <label className="text-sm font-medium">Observações</label>
            <textarea
              rows={2}
              value={form.observacoes}
              onChange={(e) => set("observacoes", e.target.value)}
              placeholder="Detalhes, lembretes…"
              className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
            />
          </div>

          {mensagem && (
            <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {mensagem}
            </div>
          )}

          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {mutation.isPending
              ? "Salvando..."
              : isEdicao
                ? "Salvar alterações"
                : "Adicionar à agenda"}
          </button>
        </form>
      </div>
    </div>
  );
}
