import type { AgendaItem, TipoAgendaItem } from "@/types";

/** Cor padrão por tipo quando o item não tem cor customizada. */
export const COR_POR_TIPO: Record<TipoAgendaItem, string> = {
  receita: "#f97316", // laranja
  pedido: "#7c3aed", // violeta
  tarefa: "#64748b", // cinza-azulado
};

/** Paleta pré-definida exibida no modal de criação/edição. */
export const PALETA_CORES: { hex: string; nome: string }[] = [
  { hex: "#f97316", nome: "Laranja" },
  { hex: "#7c3aed", nome: "Violeta" },
  { hex: "#2563eb", nome: "Azul" },
  { hex: "#16a34a", nome: "Verde" },
  { hex: "#dc2626", nome: "Vermelho" },
  { hex: "#db2777", nome: "Rosa" },
  { hex: "#ca8a04", nome: "Amarelo" },
  { hex: "#64748b", nome: "Cinza" },
];

export const LABEL_TIPO: Record<TipoAgendaItem, string> = {
  receita: "Receita",
  pedido: "Pedido",
  tarefa: "Tarefa",
};

/** Emoji/ícone textual por tipo (usado no chip da view mês). */
export const ICONE_TIPO: Record<TipoAgendaItem, string> = {
  receita: "🎂",
  pedido: "📦",
  tarefa: "✓",
};

export function corDoItem(item: Pick<AgendaItem, "cor" | "tipo">): string {
  return item.cor ?? COR_POR_TIPO[item.tipo];
}

/** Faixa de horas exibida na linha do tempo (06h–23h). */
export const HORA_INICIO_GRADE = 6;
export const HORA_FIM_GRADE = 23;
export const HORAS_GRADE: number[] = Array.from(
  { length: HORA_FIM_GRADE - HORA_INICIO_GRADE + 1 },
  (_, i) => HORA_INICIO_GRADE + i
);

const MESES = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

const DIAS_SEMANA_CURTO = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

export function nomeMes(mes0: number): string {
  return MESES[mes0] ?? "";
}

export function nomeDiaSemana(diaSemana: number): string {
  return DIAS_SEMANA_CURTO[diaSemana] ?? "";
}

/** Formata uma Date local como 'YYYY-MM-DD' (sem fuso, base da API). */
export function toDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

/** Converte 'YYYY-MM-DD' para Date local (meia-noite). */
export function fromDateKey(key: string): Date {
  return new Date(key + "T00:00:00");
}

/** Segunda-feira da semana que contém `d` (semana inicia na segunda). */
export function inicioSemana(d: Date): Date {
  const r = new Date(d);
  r.setHours(0, 0, 0, 0);
  // getDay(): domingo=0 ... sábado=6. Queremos segunda como início.
  const offset = (r.getDay() + 6) % 7;
  r.setDate(r.getDate() - offset);
  return r;
}

/** Os 7 dias (segunda a domingo) da semana de `d`. */
export function diasDaSemana(d: Date): Date[] {
  const seg = inicioSemana(d);
  return Array.from({ length: 7 }, (_, i) => {
    const dia = new Date(seg);
    dia.setDate(seg.getDate() + i);
    return dia;
  });
}

export function mesmoDia(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function adicionarDias(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export function adicionarMeses(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(1);
  r.setMonth(r.getMonth() + n);
  return r;
}

/** Grade de semanas (linhas de 7 dias) cobrindo o mês de `d`, completando
 * com dias do mês anterior/seguinte para iniciar na segunda. */
export function gradeDoMes(d: Date): Date[][] {
  const primeiro = new Date(d.getFullYear(), d.getMonth(), 1);
  const inicio = inicioSemana(primeiro);
  const semanas: Date[][] = [];
  const cursor = new Date(inicio);
  // 6 linhas cobrem qualquer disposição de mês.
  for (let s = 0; s < 6; s++) {
    const semana: Date[] = [];
    for (let i = 0; i < 7; i++) {
      semana.push(new Date(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    semanas.push(semana);
    // Para se já passamos do mês e completamos a semana.
    if (cursor.getMonth() !== d.getMonth() && semana[6].getMonth() !== d.getMonth()) {
      break;
    }
  }
  return semanas;
}

/** 'HH:MM:SS' → 'HH:MM'. */
export function formatHora(hora: string | null): string {
  if (!hora) return "";
  return hora.slice(0, 5);
}

/** Minutos desde 00:00 a partir de 'HH:MM[:SS]'. */
export function minutosDoDia(hora: string): number {
  const [h, m] = hora.split(":").map(Number);
  return h * 60 + (m || 0);
}

/** Rótulo do cabeçalho conforme a view. */
export function tituloPeriodo(view: "mes" | "semana" | "dia", ref: Date): string {
  if (view === "mes") return `${nomeMes(ref.getMonth())} ${ref.getFullYear()}`;
  if (view === "dia") {
    return `${nomeDiaSemana(ref.getDay())}, ${ref.getDate()} de ${nomeMes(
      ref.getMonth()
    )}`;
  }
  const dias = diasDaSemana(ref);
  const ini = dias[0];
  const fim = dias[6];
  const mesmoMes = ini.getMonth() === fim.getMonth();
  if (mesmoMes) {
    return `${ini.getDate()}–${fim.getDate()} de ${nomeMes(ini.getMonth())}`;
  }
  return `${ini.getDate()} ${nomeMes(ini.getMonth()).slice(0, 3)} – ${fim.getDate()} ${nomeMes(
    fim.getMonth()
  ).slice(0, 3)}`;
}
