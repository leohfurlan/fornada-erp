/**
 * Unidades padronizadas para evitar texto livre em formulários.
 * Centralizado aqui para que rendimento de receita, ingredientes e estoque
 * usem a mesma referência.
 */

export interface UnidadeOption {
  value: string;
  label: string;
  /** Categoria usada para filtrar (peso, volume, contagem). */
  categoria: "peso" | "volume" | "contagem";
}

/** Unidades de medida usadas em estoque e ingredientes de receita. */
export const UNIDADES_MEDIDA: UnidadeOption[] = [
  { value: "kg", label: "Quilograma (kg)", categoria: "peso" },
  { value: "g", label: "Grama (g)", categoria: "peso" },
  { value: "mg", label: "Miligrama (mg)", categoria: "peso" },
  { value: "L", label: "Litro (L)", categoria: "volume" },
  { value: "mL", label: "Mililitro (mL)", categoria: "volume" },
  { value: "un", label: "Unidade (un)", categoria: "contagem" },
  { value: "cx", label: "Caixa (cx)", categoria: "contagem" },
  { value: "pct", label: "Pacote (pct)", categoria: "contagem" },
  { value: "dz", label: "Dúzia (dz)", categoria: "contagem" },
  { value: "lata", label: "Lata", categoria: "contagem" },
];

/** Unidades de venda — como a receita rende para a cliente. */
export const UNIDADES_VENDA: UnidadeOption[] = [
  { value: "unidades", label: "Unidades", categoria: "contagem" },
  { value: "fatias", label: "Fatias", categoria: "contagem" },
  { value: "porcoes", label: "Porções", categoria: "contagem" },
  { value: "pedacos", label: "Pedaços", categoria: "contagem" },
  { value: "bolos", label: "Bolos", categoria: "contagem" },
  { value: "doces", label: "Doces", categoria: "contagem" },
  { value: "salgados", label: "Salgados", categoria: "contagem" },
  { value: "kg", label: "Quilogramas (kg)", categoria: "peso" },
  { value: "g", label: "Gramas (g)", categoria: "peso" },
  { value: "dz", label: "Dúzias", categoria: "contagem" },
];

/** Tipos de produto no estoque. Valor = chave da API; label = exibição. */
export const TIPOS_PRODUTO = [
  { value: "ingrediente", label: "Ingrediente" },
  { value: "embalagem", label: "Embalagem" },
  { value: "insumo", label: "Insumo" },
  { value: "descartavel", label: "Descartável" },
  { value: "outro", label: "Outro" },
] as const;

export type TipoProdutoValue = (typeof TIPOS_PRODUTO)[number]["value"];

export const CATEGORIAS_RECEITA = [
  "Bolos",
  "Cupcakes",
  "Doces",
  "Salgados",
  "Tortas",
  "Biscoitos",
  "Pães",
  "Sobremesas",
  "Brigadeiros",
  "Outros",
] as const;
