import { errorMessage } from "@/lib/validation";
import type { ItemLido, ItemObservado, ProdutoDados } from "@/types/compras";
import { nomeMaiusculo } from "@/lib/nomes";

export function produtoVazio(nome = ""): ProdutoDados {
  return { nome: nomeMaiusculo(nome), marca: "", fabricante: null, variante: null, conteudo_embalagem: "",
    unidade_conteudo: "kg", fator_para_principal: null, gtin: null };
}
export function dadosObservados(item: ItemLido): ItemObservado {
  const { indice, descricao, quantidade, unidade, preco_unitario, preco_total, desconto_item,
    marca_observada, fabricante_observado, variante_observada, conteudo_observado,
    unidade_conteudo_observada, codigo_loja, gtin, gtin_confirmado } = item;
  return { indice, linhas_origem: item.linhas_origem ?? [], descricao, quantidade, unidade, preco_unitario, preco_total, desconto_item,
    marca_observada, fabricante_observado, variante_observada, conteudo_observado,
    unidade_conteudo_observada, codigo_loja, gtin, gtin_confirmado };
}
export function erroCompras(error: unknown): string {
  return errorMessage(error);
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
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(Number(value));
}
export function custoCompra(value: string): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL",
    minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(Number(value));
}
export function dataCompra(value: string | null): string {
  return value ? value.split("-").reverse().join("/") : "Data não identificada";
}
