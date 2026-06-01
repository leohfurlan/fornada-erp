import { MoneyDisplay } from "@/components/shared/money-display";
import { formatMinutos, formatPercent } from "@/lib/utils";
import type { CustoDetalhado } from "@/types";

interface CustoCardProps {
  custo: CustoDetalhado;
}

export function CustoCard({ custo }: CustoCardProps) {
  const temEmbalagem = parseFloat(custo.custo_embalagem) > 0;
  const temResultado =
    custo.lucro_estimado !== null ||
    custo.custo_por_hora_produzida !== null ||
    custo.lucro_por_minuto !== null;
  const lucroNegativo =
    custo.lucro_estimado !== null && parseFloat(custo.lucro_estimado) < 0;

  return (
    <div className="rounded-xl border bg-card p-4 space-y-4">
      <h3 className="font-semibold text-card-foreground">Custo da receita</h3>

      {/* Breakdown de custos */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-muted-foreground">
          <span>Ingredientes</span>
          <MoneyDisplay value={custo.custo_ingredientes} />
        </div>
        {temEmbalagem && (
          <div className="flex justify-between text-muted-foreground">
            <span>Embalagem</span>
            <MoneyDisplay value={custo.custo_embalagem} />
          </div>
        )}
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

      {/* Resultado — só aparece quando há preço de venda real ou tempo ativo */}
      {temResultado && (
        <div
          className={`rounded-lg p-3 space-y-1.5 text-sm ${
            lucroNegativo
              ? "bg-destructive/10 border border-destructive/30"
              : "bg-green-50 border border-green-200"
          }`}
        >
          <p
            className={`text-xs font-medium uppercase tracking-wide ${
              lucroNegativo ? "text-destructive" : "text-green-800"
            }`}
          >
            Resultado
          </p>
          {custo.lucro_estimado !== null && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Lucro estimado por unidade</span>
              <MoneyDisplay
                value={custo.lucro_estimado}
                size="md"
                className={lucroNegativo ? "text-destructive" : "text-green-700"}
              />
            </div>
          )}
          {custo.margem_real !== null && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Margem real</span>
              <span className="font-medium">{formatPercent(custo.margem_real)}</span>
            </div>
          )}
          {custo.custo_por_hora_produzida !== null && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Custo por hora de produção</span>
              <MoneyDisplay value={custo.custo_por_hora_produzida} />
            </div>
          )}
          {custo.lucro_por_minuto !== null && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Lucro por minuto de produção</span>
              <MoneyDisplay value={custo.lucro_por_minuto} />
            </div>
          )}
        </div>
      )}

      {/* Tempo: total, ativo (atenção) e passivo (forno, descanso) */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
        <span>Tempo total: {formatMinutos(custo.tempo_total_minutos)}</span>
        <span>Ativo: {formatMinutos(custo.tempo_ativo_minutos)}</span>
        <span>Passivo: {formatMinutos(custo.tempo_passivo_minutos)}</span>
      </div>
    </div>
  );
}
