"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Calendar,
  Check,
  ChefHat,
  Clock,
  ExternalLink,
  Pencil,
  PlayCircle,
  Trash2,
  X,
} from "lucide-react";
import { useDeletarAgendaItem, useMarcarConcluido } from "@/hooks/use-agenda";
import { useMudarStatusOP, useOrdemProducao } from "@/hooks/use-producao";
import { DecimalInput } from "@/components/shared/decimal-input";
import { corDoItem, fromDateKey, formatHora, LABEL_TIPO } from "@/lib/agenda";
import { cn, formatQuantidade } from "@/lib/utils";
import type { AgendaItem, ApiError } from "@/types";
import type { AxiosError } from "axios";

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

  // Carrega a OP vinculada ao item (só quando há ordem_producao_id).
  const { data: op } = useOrdemProducao(item.ordem_producao_id ?? "");
  const mudarStatusOP = useMudarStatusOP(item.ordem_producao_id ?? "");

  // Estado do modal de apontamento (replicado da tela /producao/[id]).
  const [apontamentoAberto, setApontamentoAberto] = useState(false);
  const [qtdProduzida, setQtdProduzida] = useState<number>(0);

  const handleConcluir = () => {
    marcar.mutate({ id: item.id, concluido: !item.concluido });
  };

  const handleExcluir = async () => {
    await deletar.mutateAsync(item.id);
    onClose();
  };

  const handleIniciarProducao = async () => {
    if (!op) return;
    if (
      !confirm(
        "Ao iniciar produção, os ingredientes serão reservados no estoque. Continuar?"
      )
    )
      return;
    try {
      await mudarStatusOP.mutateAsync({ status: "em_producao" });
    } catch {
      // Erro exibido via mensagemErroOP abaixo
    }
  };

  const handleAbrirApontamento = () => {
    if (!op) return;
    const rendimento = parseFloat(op.receita_rendimento) || 1;
    setQtdProduzida(parseFloat(op.qtd_planejada) * rendimento);
    setApontamentoAberto(true);
  };

  const handleConfirmarApontamento = async () => {
    try {
      await mudarStatusOP.mutateAsync({
        status: "finalizada",
        qtd_produzida: qtdProduzida,
      });
      setApontamentoAberto(false);
    } catch {
      // Erro exibido no modal
    }
  };

  const handleCancelarOP = async () => {
    if (!op) return;
    if (!confirm("Cancelar esta ordem de produção?")) return;
    try {
      await mudarStatusOP.mutateAsync({ status: "cancelada" });
    } catch {
      // Erro exibido abaixo
    }
  };

  const erroOP = mudarStatusOP.error as AxiosError<ApiError> | null;
  const mensagemErroOP = erroOP?.response?.data?.detail;

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
          {/* OP vinculada — link navegável + status + botões de ação */}
          {item.ordem_producao_id && op && (
            <div className="space-y-2">
              {/* Linha de cabeçalho da OP */}
              <Link
                href={`/producao/${item.ordem_producao_id}`}
                className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2 text-sm hover:bg-muted"
              >
                <span className="flex items-center gap-2">
                  <ChefHat className="h-4 w-4 text-muted-foreground" />
                  <span>
                    <span className="text-muted-foreground">OP </span>
                    <span className="font-medium">
                      #{String(op.numero).padStart(3, "0")}
                    </span>
                    <span className="ml-2 text-muted-foreground">·</span>
                    <span className="ml-2 text-muted-foreground">
                      {labelStatusOP(op.status)}
                    </span>
                  </span>
                </span>
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
              </Link>

              {/* Mensagem de erro das transições */}
              {mensagemErroOP && (
                <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {mensagemErroOP}
                </div>
              )}

              {/* Botões de ação contextual — espelham /producao/[id] */}
              {op.proximas_transicoes.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {op.proximas_transicoes.map((transicao) => (
                    <button
                      key={transicao}
                      type="button"
                      onClick={() => {
                        if (transicao === "em_producao") handleIniciarProducao();
                        else if (transicao === "finalizada") handleAbrirApontamento();
                        else if (transicao === "cancelada") handleCancelarOP();
                      }}
                      disabled={mudarStatusOP.isPending}
                      className={cn(
                        "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50",
                        transicao === "cancelada"
                          ? "border border-destructive/30 text-destructive hover:bg-destructive/5"
                          : "bg-primary text-primary-foreground hover:bg-primary/90"
                      )}
                    >
                      {transicao === "em_producao" && <PlayCircle className="h-4 w-4" />}
                      {labelBotaoOP(transicao)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Fallback: OP vinculada mas ainda carregando */}
          {item.ordem_producao_id && !op && item.numero_op && (
            <div className="rounded-lg border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
              OP #{String(item.numero_op).padStart(3, "0")} — carregando...
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

      {/* Modal de apontamento — replicado de /producao/[id] */}
      {apontamentoAberto && op && (
        <div className="fixed inset-0 z-[60] bg-black/40 flex items-end md:items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl bg-background p-5 space-y-4 shadow-xl">
            <div>
              <h2 className="font-semibold text-lg">Apontar produção</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                Quantas unidades finais saíram de fato?
              </p>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">
                Unidades produzidas ({op.receita_rendimento_unidade || "un"})
              </label>
              <DecimalInput
                value={qtdProduzida}
                onChange={setQtdProduzida}
                placeholder="0"
              />
              <p className="text-xs text-muted-foreground">
                {(() => {
                  const fornadas = parseFloat(op.qtd_planejada);
                  const rendimento = parseFloat(op.receita_rendimento) || 1;
                  const esperadas = fornadas * rendimento;
                  const unidade = op.receita_rendimento_unidade || "un";
                  return `Esperado: ${formatQuantidade(esperadas)} ${unidade}`;
                })()}
              </p>
            </div>
            <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
              <p>📦 Ingredientes baixados pelo planejado.</p>
              <p>🧁 Estoque pronto recebe as unidades reais informadas.</p>
            </div>
            {mensagemErroOP && (
              <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {mensagemErroOP}
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setApontamentoAberto(false)}
                className="flex-1 rounded-lg border px-3 py-2.5 text-sm hover:bg-muted"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleConfirmarApontamento}
                disabled={qtdProduzida < 0 || mudarStatusOP.isPending}
                className="flex-1 rounded-lg bg-primary px-3 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                {mudarStatusOP.isPending ? "Salvando..." : "Finalizar produção"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function labelStatusOP(status: string): string {
  const map: Record<string, string> = {
    planejada: "Planejada",
    em_producao: "Em produção",
    finalizada: "Finalizada",
    cancelada: "Cancelada",
  };
  return map[status] ?? status;
}

function labelBotaoOP(transicao: string): string {
  if (transicao === "em_producao") return "Iniciar produção";
  if (transicao === "finalizada") return "Apontar produção";
  if (transicao === "cancelada") return "Cancelar OP";
  return transicao;
}
