import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatMoney(value: string | number | null | undefined): string {
  const num = typeof value === "string" ? parseFloat(value) : (value ?? 0);
  if (isNaN(num)) return "R$ 0,00";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(num);
}

export function formatDecimal(value: string | number | null | undefined, decimals = 3): string {
  const num = typeof value === "string" ? parseFloat(value) : (value ?? 0);
  if (isNaN(num)) return "0";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(num);
}

/**
 * Formata uma quantidade de forma inteligente:
 * - número inteiro (12, 20)        → "12", "20"
 * - número decimal real (0.5, 1.25) → "0,5", "1,25"
 *
 * Usa quando exibimos rendimento de receita, estoque, quantidade de
 * ingrediente — onde "12.000 fatias" confunde a usuária por causa do
 * separador de milhar em pt-BR.
 */
export function formatQuantidade(value: string | number | null | undefined): string {
  const num = typeof value === "string" ? parseFloat(value) : (value ?? 0);
  if (isNaN(num)) return "0";
  const ehInteiro = Number.isInteger(num);
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: ehInteiro ? 0 : 3,
  }).format(num);
}

export function formatPercent(value: string | number | null | undefined): string {
  const num = typeof value === "string" ? parseFloat(value) : (value ?? 0);
  if (isNaN(num)) return "0%";
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(num);
}

/**
 * Formata data/hora ISO para exibição curta pt-BR.
 * - Hoje: "Hoje 14:32"
 * - Ontem: "Ontem 14:32"
 * - Mesmo ano: "27/05 14:32"
 * - Outro ano: "27/05/2024"
 */
export function formatDataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const hoje = new Date();
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);

  const mesmoDia = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  if (mesmoDia(d, hoje)) return `Hoje ${hora}`;
  if (mesmoDia(d, ontem)) return `Ontem ${hora}`;

  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  if (d.getFullYear() === hoje.getFullYear()) return `${dia}/${mes} ${hora}`;
  return `${dia}/${mes}/${d.getFullYear()}`;
}

/**
 * Para datas de OPs: se for hoje, exibe "Hoje"; caso contrário, "dd/mm".
 * `data_prevista` é `date` (sem hora) no backend, então não há hora a exibir.
 */
export function formatDataOP(dataISO: string | null | undefined): string {
  if (!dataISO) return "";
  const d = new Date(dataISO + "T00:00:00"); // evitar timezone shift
  const hoje = new Date();
  const ehHoje =
    d.getFullYear() === hoje.getFullYear() &&
    d.getMonth() === hoje.getMonth() &&
    d.getDate() === hoje.getDate();
  if (ehHoje) return "Hoje";
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${dia}/${mes}`;
}

export function formatMinutos(minutos: number): string {
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const mins = minutos % 60;
  return mins > 0 ? `${horas}h ${mins}min` : `${horas}h`;
}
