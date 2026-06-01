"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowDownToLine, ArrowLeft, ArrowUpFromLine, Sliders } from "lucide-react";
import { useIngrediente, useMovimentacoesIngrediente } from "@/hooks/use-estoque";
import { MoneyDisplay } from "@/components/shared/money-display";
import { formatDataHora, formatQuantidade } from "@/lib/utils";
import type { MovimentacaoEstoque } from "@/types";

const ORIGEM_LABEL: Record<string, string> = {
  compra: "Compra",
  producao: "Produção",
  ajuste: "Ajuste manual",
  cadastro_inicial: "Cadastro inicial",
};

export default function HistoricoIngredientePage() {
  const { id } = useParams<{ id: string }>();
  const { data: ingrediente, isLoading: loadingIngr } = useIngrediente(id);
  const { data: movs, isLoading: loadingMovs, error } = useMovimentacoesIngrediente(id);

  if (loadingIngr || loadingMovs) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || !ingrediente) {
    return (
      <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
        Não foi possível carregar o histórico.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <Link
        href={`/estoque/${id}/editar`}
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div>
        <p className="text-xs text-muted-foreground">Histórico de movimentações</p>
        <h1 className="text-xl font-bold">{ingrediente.nome}</h1>
        <p className="text-sm text-muted-foreground">
          Saldo atual:{" "}
          <span className="font-medium text-foreground">
            {formatQuantidade(ingrediente.saldo)} {ingrediente.unidade}
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
                  <th className="px-3 py-2 text-right">Custo unit.</th>
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
                      {ORIGEM_LABEL[m.origem] ?? m.origem}
                    </td>
                    <td className="px-3 py-2 text-right font-medium">
                      <QuantidadeAssinada
                        tipo={m.tipo}
                        quantidade={m.quantidade}
                        unidade={ingrediente.unidade}
                      />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <MoneyDisplay value={m.custo_unitario} size="sm" />
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
                  <span className="text-muted-foreground">
                    {ORIGEM_LABEL[m.origem] ?? m.origem}
                  </span>
                  <span className="font-medium">
                    <QuantidadeAssinada
                      tipo={m.tipo}
                      quantidade={m.quantidade}
                      unidade={ingrediente.unidade}
                    />
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Custo unitário</span>
                  <MoneyDisplay value={m.custo_unitario} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function TipoBadge({ tipo }: { tipo: MovimentacaoEstoque["tipo"] }) {
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

function QuantidadeAssinada({
  tipo,
  quantidade,
  unidade,
}: {
  tipo: MovimentacaoEstoque["tipo"];
  quantidade: string;
  unidade: string;
}) {
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
      {formatQuantidade(quantidade)} {unidade}
    </span>
  );
}
