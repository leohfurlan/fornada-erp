import { MoneyDisplay } from "@/components/shared/money-display";
import { formatMinutos, formatPercent } from "@/lib/utils";
import type { CustoDetalhado } from "@/types";

interface CustoCardProps {
  custo: CustoDetalhado;
  margemDesejada: string;
}

export function CustoCard({ custo, margemDesejada }: CustoCardProps) {
  const margemReal =
    parseFloat(custo.preco_recomendado) > 0
      ? (parseFloat(custo.preco_recomendado) - parseFloat(custo.custo_por_unidade)) /
        parseFloat(custo.preco_recomendado)
      : 0;

  return (
    <div className="rounded-xl border bg-card p-4 space-y-4">
      <h3 className="font-semibold text-card-foreground">Custo da receita</h3>

      {/* Breakdown de custos */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-muted-foreground">
          <span>Ingredientes</span>
          <MoneyDisplay value={custo.custo_ingredientes} />
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Custo operacional</span>
          <MoneyDisplay value={custo.custo_operacional} />
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Mão de obra direta</span>
          <MoneyDisplay value={custo.custo_mao_obra_direta} />
        </div>
        <div className="border-t pt-2 flex justify-between font-medium">
          <span>Custo total</span>
          <MoneyDisplay value={custo.custo_total} size="md" />
        </div>
      </div>

      {/* Por unidade */}
      <div className="rounded-lg bg-muted/50 p-3 space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Custo por unidade</span>
          <MoneyDisplay value={custo.custo_por_unidade} />
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Preço mínimo</span>
          <MoneyDisplay value={custo.preco_minimo} />
        </div>
        <div className="flex justify-between font-semibold text-primary">
          <span>Preço recomendado</span>
          <MoneyDisplay value={custo.preco_recomendado} size="lg" />
        </div>
      </div>

      {/* Tempo */}
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span>Tempo total: {formatMinutos(custo.tempo_total_minutos)}</span>
        <span>Tempo ativo: {formatMinutos(custo.tempo_ativo_minutos)}</span>
      </div>
    </div>
  );
}
