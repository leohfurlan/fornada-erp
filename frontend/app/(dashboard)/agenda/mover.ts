import type { AgendaItem, MoverAgendaItemPayload } from "@/types";

const FIM_DO_DIA = 24 * 60;

function minParaHora(min: number): string {
  const m = Math.min(min, FIM_DO_DIA);
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return `${String(h).padStart(2, "0")}:${String(mm).padStart(2, "0")}:00`;
}

/**
 * Calcula o payload de movimentação ao soltar um item numa célula (dia + hora).
 * Preserva a duração do item (ou usa 60min para itens que eram de dia inteiro).
 */
export function calcularMover(
  item: AgendaItem,
  dataKey: string,
  hora: number
): MoverAgendaItemPayload {
  const inicioMin = hora * 60;
  const duracao = item.duracao_minutos ?? 60;
  return {
    data: dataKey,
    hora_inicio: minParaHora(inicioMin),
    hora_fim: minParaHora(inicioMin + duracao),
  };
}

/** Movimentação na view mês: só muda o dia, preserva o horário existente. */
export function calcularMoverDia(
  item: AgendaItem,
  dataKey: string
): MoverAgendaItemPayload {
  return {
    data: dataKey,
    hora_inicio: item.hora_inicio,
    hora_fim: item.hora_fim,
  };
}
