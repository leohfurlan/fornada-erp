/**
 * Helpers para entrada de valores decimais em pt-BR (vírgula como separador).
 *
 * Estratégia: o usuário digita "1,5" ou "1.5" e nós sempre normalizamos para
 * o formato com ponto antes de enviar pra API. Na exibição, o número vira
 * texto com vírgula.
 */

/** Converte string digitada pelo usuário ("1,5", "1.234,56") para número. */
export function parseDecimalBR(input: string | number | null | undefined): number {
  if (input === null || input === undefined || input === "") return 0;
  if (typeof input === "number") return input;

  const limpa = input
    .trim()
    .replace(/\s+/g, "")
    // remove separador de milhar (ponto antes de 3 dígitos seguido de vírgula em algum lugar)
    .replace(/\.(?=\d{3}(\D|$))/g, "")
    .replace(",", ".");

  const num = parseFloat(limpa);
  return isNaN(num) ? 0 : num;
}

/** Formata número/string para exibição em input (vírgula como decimal, sem milhar). */
export function formatDecimalInput(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "";
  // Remove zeros decimais inúteis: 1.50 → "1,5"; 1.0 → "1"
  return String(num).replace(".", ",");
}

/** Permite só caracteres válidos de decimal pt-BR (0-9 + . + , uma única vez). */
export function sanitizeDecimalInput(raw: string): string {
  // mantém apenas dígitos, vírgula e ponto
  let s = raw.replace(/[^\d.,]/g, "");
  // só permite uma vírgula
  const firstComma = s.indexOf(",");
  if (firstComma !== -1) {
    s = s.slice(0, firstComma + 1) + s.slice(firstComma + 1).replace(/,/g, "");
  }
  return s;
}
