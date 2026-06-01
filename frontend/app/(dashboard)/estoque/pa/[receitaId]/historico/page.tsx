"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowDownToLine, ArrowLeft, ArrowUpFromLine, Sliders } from "lucide-react";
import { useMovimentacoesPA, useSaldoPA } from "@/hooks/use-estoque-pa";
import { formatDataHora, formatQuantidade } from "@/lib/utils";
import type { MovimentacaoEstoquePA } from "@/types";

export default function HistoricoEstoquePAPage() {
  const { receitaId } = useParams<{ receitaId: string }>();
  const { data: saldo, isLoading: loadingSaldo } = useSaldoPA(receitaId);
  const { data: movs, isLoading: loadingMovs, error } = useMovimentacoesPA(receitaId);

  if (loadingSaldo || loadingMovs) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !saldo) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar o histórico.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <Link href="/estoque?tab=pa" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div>
        <p className="text-xs text-muted-foreground">Histórico de movimentações</p>
        <h1 className="text-xl font-bold">{saldo.nome_receita}</h1>
        <p className="text-sm text-muted-foreground">
          Disponível agora:{" "}
          <span className="font-medium text-foreground">
            {formatQuantidade(saldo.qtd_disponivel)} un
          </span>
        </p>
      </div>

      {!movs?.length ? (
        <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          Nenhuma movimentação registrada ainda
        </div>
      ) : (
        <>
          {/* Desktop */}
          <div className="hidden md:block rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left">Data</th>
                  <th className="px-3 py-2 text-left">Tipo</th>
                  <th className="px-3 py-2 text-left">Origem</th>
                  <th className="px-3 py-2 text-right">Quantidade</th>
                </tr>
              </thead>
              <tbody>
                {movs.map((m) => (
                  <tr key={m.id} className="border-t">
                    <td className="px-3 py-2 text-muted-foreground">
                      {formatDataHora(m.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      <TipoBadge tipo={m.tipo} />
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      <OrigemLabel origem={m.origem} />
                    </td>
                    <td className="px-3 py-2 text-right font-medium">
                      <QtdAssinada tipo={m.tipo} qtd={m.quantidade} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile */}
          <div className="md:hidden space-y-2">
            {movs.map((m) => (
              <div key={m.id} className="rounded-xl border bg-card p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <TipoBadge tipo={m.tipo} />
                  <span className="text-xs text-muted-foreground">
                    {formatDataHora(m.created_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <OrigemLabel origem={m.origem} className="text-muted-foreground" />
                  <span className="font-medium">
                    <QtdAssinada tipo={m.tipo} qtd={m.quantidade} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function TipoBadge({ tipo }: { tipo: MovimentacaoEstoquePA["tipo"] }) {
  const cfg = {
    entrada: {
      label: "Entrada",
      Icon: ArrowDownToLine,
      className: "bg-green-100 text-green-800",
    },
    saida: {
      label: "Saída",
      Icon: ArrowUpFromLine,
      className: "bg-orange-100 text-orange-800",
    },
    ajuste: {
      label: "Ajuste",
      Icon: Sliders,
      className: "bg-blue-100 text-blue-800",
    },
  }[tipo];
  if (!cfg) return <span className="text-xs">{tipo}</span>;
  const { Icon } = cfg;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.className}`}
    >
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}

function OrigemLabel({ origem, className }: { origem: string; className?: string }) {
  // Origem vem no formato 'op:N', 'venda:N', 'pedido:N', 'ajuste', 'venda_cancelada:N'
  const [prefixo, numero] = origem.split(":");
  const labels: Record<string, string> = {
    op: "Ordem de Produção",
    venda: "Venda",
    pedido: "Pedido entregue",
    venda_cancelada: "Estorno de venda",
    ajuste: "Ajuste manual",
  };
  const label = labels[prefixo] ?? prefixo;
  return (
    <span className={className}>
      {label}
      {numero && ` #${numero}`}
    </span>
  );
}

function QtdAssinada({ tipo, qtd }: { tipo: MovimentacaoEstoquePA["tipo"]; qtd: string }) {
  const sinal = tipo === "entrada" ? "+" : tipo === "saida" ? "−" : "";
  const cor =
    tipo === "entrada"
      ? "text-green-700"
      : tipo === "saida"
        ? "text-orange-700"
        : "text-foreground";
  return (
    <span className={cor}>
      {sinal}
      {formatQuantidade(qtd)} un
    </span>
  );
}
