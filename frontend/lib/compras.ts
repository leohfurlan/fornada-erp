import { isAxiosError } from "axios";
import type { ItemLido, ItemObservado, ProdutoDados } from "@/types/compras";

export function produtoVazio(nome = ""): ProdutoDados {
  return { nome, marca: "", fabricante: null, variante: null, conteudo_embalagem: "",
    unidade_conteudo: "kg", fator_para_principal: null, gtin: null };
}
export function dadosObservados(item: ItemLido): ItemObservado {
  const { indice, descricao, quantidade, unidade, preco_unitario, preco_total, desconto_item,
    marca_observada, fabricante_observado, variante_observada, conteudo_observado,
    unidade_conteudo_observada, codigo_loja, gtin, gtin_confirmado } = item;
  return { indice, descricao, quantidade, unidade, preco_unitario, preco_total, desconto_item,
    marca_observada, fabricante_observado, variante_observada, conteudo_observado,
    unidade_conteudo_observada, codigo_loja, gtin, gtin_confirmado };
}
export function erroCompras(error: unknown): string {
  if (isAxiosError<{ detail: unknown }>(error)) {
    const detail = error.response?.data.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((entry: unknown) => {
        if (typeof entry === "object" && entry !== null && "msg" in entry) return String(entry.msg);
        return "Confira os campos da compra.";
      }).join(" ");
    }
  }
  return "Não foi possível concluir. Confira os dados e tente novamente.";
}
function escalado(value: string, casas: number): bigint {
  if (!/^\d*(\.\d*)?$/.test(value)) return BigInt(0);
  const [inteiro = "0", decimal = ""] = value.split(".");
  return BigInt((inteiro || "0") + decimal.padEnd(casas, "0").slice(0, casas));
}
/** Total efetivo em centavos, sem multiplicação monetária em float. */
export function totalItem(quantidade: string, preco: string, desconto: string): string {
  const bruto = escalado(quantidade, 8) * escalado(preco, 8);
  const centavos = (bruto + BigInt("50000000000000")) / BigInt("100000000000000") - escalado(desconto, 2);
  if (centavos <= BigInt(0)) return "0.00";
  return (centavos / BigInt(100)).toString() + "." + (centavos % BigInt(100)).toString().padStart(2, "0");
}
export function decimalCompra(value: string): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 8 }).format(Number(value));
}
export function custoCompra(value: string): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL",
    minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(Number(value));
}
export function dataCompra(value: string | null): string {
  return value ? value.split("-").reverse().join("/") : "Data não identificada";
}
