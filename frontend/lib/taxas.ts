/** Desloca a vírgula usando texto: taxas nunca passam por ponto flutuante. */
function deslocarDecimal(valor: string, casas: number): string {
  const normalizado = valor.trim().replace(",", ".") || "0";
  if (!/^\d*(\.\d*)?$/.test(normalizado)) throw new Error("Taxa inválida");
  const [inteiro = "", fracao = ""] = normalizado.split(".");
  const digitos = inteiro + fracao;
  const posicao = inteiro.length + casas;
  let resultado: string;
  if (posicao <= 0) resultado = "0." + "0".repeat(-posicao) + digitos;
  else if (posicao >= digitos.length) resultado = digitos + "0".repeat(posicao - digitos.length);
  else resultado = digitos.slice(0, posicao) + "." + digitos.slice(posicao);
  const [i, f = ""] = resultado.split(".");
  const base = i.replace(/^0+(?=\d)/, "") || "0";
  const decimal = f.replace(/0+$/, "");
  return decimal ? `${base}.${decimal}` : base;
}

export function taxaParaPercentual(taxa: string): string {
  return deslocarDecimal(taxa, 2).replace(".", ",");
}

export function percentualParaTaxa(percentual: string): string {
  return deslocarDecimal(percentual, -2);
}
