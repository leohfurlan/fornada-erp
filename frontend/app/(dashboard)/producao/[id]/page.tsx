"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Calendar, Trash2 } from "lucide-react";
import {
  useDeletarOrdemProducao,
  useMudarStatusOP,
  useOrdemProducao,
} from "@/hooks/use-producao";
import { useReceita } from "@/hooks/use-receitas";
import { OpStatusBadge, STATUS_OP_LABEL } from "@/components/shared/op-status-badge";
import { DecimalInput } from "@/components/shared/decimal-input";
import { formatDataHora, formatQuantidade } from "@/lib/utils";
import type { ApiError, StatusOP } from "@/types";
import type { AxiosError } from "axios";

export default function OrdemProducaoDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: op, isLoading } = useOrdemProducao(id);
  // Receita carregada à parte para mostrar consumo de ingredientes.
  const { data: receita } = useReceita(op?.receita_id ?? "");
  const mudar = useMudarStatusOP(id);
  const deletar = useDeletarOrdemProducao();

  const [apontamentoAberto, setApontamentoAberto] = useState(false);
  const [qtdProduzida, setQtdProduzida] = useState<number>(0);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-48 rounded bg-muted animate-pulse" />
        <div className="h-40 rounded-xl bg-muted animate-pulse" />
      </div>
    );
  }

  if (!op) {
    return <p className="text-muted-foreground">Ordem de produção não encontrada.</p>;
  }

  const handleTransicao = async (novo: StatusOP) => {
    if (novo === "finalizada") {
      // Abre modal pra coletar qtd_produzida.
      // Default = fornadas planejadas × rendimento da receita
      // (= unidades esperadas se nada der errado).
      const rendimento = parseFloat(op.receita_rendimento) || 1;
      setQtdProduzida(parseFloat(op.qtd_planejada) * rendimento);
      setApontamentoAberto(true);
      return;
    }
    if (novo === "em_producao") {
      if (
        !confirm(
          "Ao iniciar produção, os ingredientes serão reservados no estoque. Continuar?"
        )
      ) {
        return;
      }
    }
    if (novo === "cancelada") {
      if (!confirm("Cancelar esta ordem de produção?")) return;
    }
    try {
      await mudar.mutateAsync({ status: novo });
    } catch {
      // Erro mostrado abaixo
    }
  };

  const confirmarApontamento = async () => {
    try {
      await mudar.mutateAsync({ status: "finalizada", qtd_produzida: qtdProduzida });
      setApontamentoAberto(false);
    } catch {
      // Erro mostrado abaixo (modal continua aberto)
    }
  };

  const handleDeletar = async () => {
    if (!confirm("Excluir esta ordem de produção?")) return;
    try {
      await deletar.mutateAsync(id);
      router.push("/producao");
    } catch {
      // Erro tratado
    }
  };

  const erro = mudar.error as AxiosError<ApiError> | null;
  const mensagem = erro?.response?.data?.detail;
  const erroDel = deletar.error as AxiosError<ApiError> | null;
  const mensagemDel = erroDel?.response?.data?.detail;

  const podeDeletar = op.status === "planejada" || op.status === "cancelada";

  const consumoPrevisto = receita?.ingredientes.map((ri) => ({
    id: ri.id,
    nome: ri.nome_ingrediente,
    qtd: parseFloat(ri.quantidade) * parseFloat(op.qtd_planejada),
    unidade: ri.unidade,
  })) ?? [];

  return (
    <div className="space-y-5 pb-8">
      <Link href="/producao" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm text-muted-foreground">
            OP #{String(op.numero).padStart(3, "0")}
          </span>
          <OpStatusBadge status={op.status} />
        </div>
        <h1 className="text-xl font-bold mt-1">{op.nome_receita}</h1>
        {(() => {
          const fornadas = parseFloat(op.qtd_planejada);
          const rendimento = parseFloat(op.receita_rendimento) || 1;
          const unidade = op.receita_rendimento_unidade || "un";
          const unidadesPlanejadas = fornadas * rendimento;
          return (
            <p className="text-sm text-muted-foreground mt-0.5">
              Planejado:{" "}
              <span className="font-medium text-foreground">
                {formatQuantidade(fornadas)}{" "}
                {fornadas === 1 ? "fornada" : "fornadas"}
              </span>{" "}
              ({formatQuantidade(unidadesPlanejadas)} {unidade})
              {op.qtd_produzida && (
                <>
                  {" "}· Produzido:{" "}
                  <span className="font-medium text-foreground">
                    {formatQuantidade(op.qtd_produzida)} {unidade}
                  </span>
                </>
              )}
            </p>
          );
        })()}
        {op.data_prevista && (
          <p className="text-sm text-muted-foreground mt-0.5 flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {formatarData(op.data_prevista)}
          </p>
        )}
        {op.pedido_id && (
          <Link
            href={`/pedidos/${op.pedido_id}`}
            className="inline-block mt-1 text-sm text-primary hover:underline"
          >
            Pedido #{String(op.pedido_numero).padStart(3, "0")} →
          </Link>
        )}
        <p className="text-xs text-muted-foreground mt-1">
          Criada em {formatDataHora(op.created_at)}
        </p>
      </div>

      {mensagem && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/30 px-3 py-2 text-sm text-destructive">
          {mensagem}
        </div>
      )}

      {/* Botões de transição */}
      {op.proximas_transicoes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {op.proximas_transicoes.map((novo) => (
            <button
              key={novo}
              type="button"
              onClick={() => handleTransicao(novo)}
              disabled={mudar.isPending}
              className={`rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50 ${
                novo === "cancelada"
                  ? "border border-destructive/30 text-destructive hover:bg-destructive/5"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              }`}
            >
              {labelBotao(novo)}
            </button>
          ))}
        </div>
      )}

      {/* Consumo previsto */}
      {consumoPrevisto.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-semibold">
            {op.status === "finalizada" || op.status === "em_producao"
              ? "Ingredientes consumidos"
              : "Ingredientes a consumir"}
          </h2>
          <div className="divide-y rounded-xl border">
            {consumoPrevisto.map((ing) => (
              <div key={ing.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <span>{ing.nome}</span>
                <span className="font-medium">
                  {formatQuantidade(ing.qtd)} {ing.unidade}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {op.observacoes && (
        <section className="space-y-2">
          <h2 className="font-semibold">Observações</h2>
          <div className="rounded-xl border bg-card p-4 text-sm whitespace-pre-wrap leading-relaxed">
            {op.observacoes}
          </div>
        </section>
      )}

      {podeDeletar && (
        <div className="border-t pt-5 space-y-2">
          {mensagemDel && (
            <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {mensagemDel}
            </div>
          )}
          <button
            type="button"
            onClick={handleDeletar}
            disabled={deletar.isPending}
            className="w-full flex items-center justify-center gap-2 rounded-lg border border-destructive/30 px-4 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/5 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
            {deletar.isPending ? "Excluindo..." : "Excluir OP"}
          </button>
        </div>
      )}

      {/* Modal de apontamento */}
      {apontamentoAberto && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-end md:items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl bg-background p-5 space-y-4 shadow-xl">
            <div>
              <h2 className="font-semibold text-lg">Apontar produção</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                Quantas unidades finais saíram de fato? Pode ser diferente do
                esperado (perda no forno, sobra de massa).
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
                  return `Esperado: ${formatQuantidade(esperadas)} ${unidade} (${formatQuantidade(fornadas)} ${fornadas === 1 ? "fornada" : "fornadas"} × ${formatQuantidade(rendimento)} ${unidade}/fornada)`;
                })()}
              </p>
            </div>
            <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
              <p>📦 Ingredientes serão baixados pelo número de fornadas planejadas.</p>
              <p>🧁 Estoque pronto receberá as unidades reais informadas acima.</p>
            </div>
            {mensagem && (
              <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {mensagem}
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
                onClick={confirmarApontamento}
                disabled={qtdProduzida < 0 || mudar.isPending}
                className="flex-1 rounded-lg bg-primary px-3 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                {mudar.isPending ? "Salvando..." : "Finalizar produção"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function labelBotao(novo: StatusOP): string {
  if (novo === "em_producao") return "Iniciar produção";
  if (novo === "finalizada") return "Apontar produção";
  if (novo === "cancelada") return "Cancelar";
  return STATUS_OP_LABEL[novo];
}

function formatarData(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
