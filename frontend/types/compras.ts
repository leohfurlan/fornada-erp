import type { ConfirmarCompraResponse } from "@/types";

export interface ProdutoDados {
  nome: string;
  marca: string;
  fabricante: string | null;
  variante: string | null;
  conteudo_embalagem: string;
  unidade_conteudo: string;
  fator_para_principal: string | null;
  gtin: string | null;
}
export interface ProdutoCriar extends ProdutoDados {
  ingrediente_id: string;
  aprovado: boolean;
  fornecedores_aprovados: string[];
}
export interface ProdutoCompra extends ProdutoCriar {
  id: string;
  tenant_id: string;
  revisao: number;
  created_at: string;
  updated_at: string;
}
export interface FornecedorCompra {
  id: string;
  nome: string;
  cnpj: string | null;
  revisao: number;
  created_at: string;
}
export interface VinculoCompra {
  id: string;
  fornecedor_id: string;
  produto_id: string;
  tipo: string;
  valor_original: string;
  valor_normalizado: string;
  revisao: number;
  produto_revisao_confirmada: number;
  ativo: boolean;
}
export interface Pagina<T> { itens: T[]; total: number }
export interface ItemObservado {
  indice: number;
  descricao: string;
  quantidade: string | null;
  unidade: string | null;
  preco_unitario: string | null;
  preco_total: string | null;
  desconto_item: string | null;
  marca_observada: string | null;
  fabricante_observado: string | null;
  variante_observada: string | null;
  conteudo_observado: string | null;
  unidade_conteudo_observada: string | null;
  codigo_loja: string | null;
  gtin: string | null;
  gtin_confirmado: boolean;
}
export interface ItemLido extends ItemObservado {
  ingrediente_id: string | null;
  nome_match: string | null;
  produto_id: string | null;
  produto_revisao: number | null;
  reconhecimento: string;
  score: number;
  explicacao: string;
  pendencias: string[];
  candidatos: { produto_id: string; produto_revisao: number; ingrediente_id: string;
    nome_produto: string; nome_material: string }[];
  vinculo_id: string | null;
  vinculo_revisao: number | null;
  tipo_sugerido: string;
  unidade_sugerida: string;
}
export interface LeituraCompra {
  itens: ItemLido[];
  total_nota: string | null;
  estabelecimento: string | null;
  data_compra: string | null;
  data_original: string | null;
  fornecedor_id: string | null;
  fornecedores_candidatos: FornecedorCompra[];
  cnpj_observado: string | null;
  identidade_nota: string | null;
  identidade_confirmada: boolean;
  fonte: string;
  confianca: number;
  aviso_mock: boolean;
}
export interface ItemRevisado {
  ingrediente_id: string | null;
  criar_novo: boolean;
  nome: string;
  tipo: string;
  unidade_principal: string | null;
  descricao_original: string;
  quantidade: string;
  unidade: string;
  custo_unitario: string;
  desconto_item: string;
  preco_total: string;
  produto_id: string | null;
  produto_revisao: number | null;
  produto_novo: ProdutoDados | null;
  codigo_loja: string | null;
  gtin_confirmado: string | null;
  aprovar_produto: boolean;
  aprovar_fornecedor: boolean;
  aceitar_excecao: boolean;
  guardar_vinculo: boolean;
  conflito_vinculo: { id: string; revisao: number } | null;
}
export interface CompraRevisada {
  itens: ItemRevisado[];
  estabelecimento: string | null;
  data_compra: string | null;
  total_nota: string | null;
  fornecedor_id: string | null;
  fornecedor_novo: { nome: string; cnpj: string | null } | null;
  identidade_nota: string | null;
  identidade_confirmada: boolean;
  confirmar_duplicidade: boolean;
  origem: "web_manual" | "web_ocr";
}
export interface PreviaCompra {
  itens: { indice: number; ingrediente_id: string | null; nome_material: string;
    produto_id: string | null; quantidade_principal: string; unidade_principal: string;
    fator_aplicado: string; custo_normalizado: string; preco_total: string;
    pendencias: string[] }[];
  total_selecionado: string;
  duplicidade: { compra_id: string; data_registro: string }[];
  pode_confirmar: boolean;
}
export interface ResultadoCompra extends ConfirmarCompraResponse {
  compra_id: string;
  data_compra: string | null;
  fornecedor_id: string | null;
  data_registro: string;
  total_selecionado: string;
}
export interface CompraResumo {
  id: string;
  data_compra: string | null;
  data_registro: string;
  estabelecimento_original: string | null;
  fornecedor_id: string | null;
  fornecedor_nome_snapshot: string | null;
  origem: string;
  total_selecionado: string;
  metadados_completos: boolean;
  quantidade_itens: number;
}
export interface SnapshotCompra {
  nome_material: string;
  unidade_principal: string;
  nome_produto: string | null;
  marca: string | null;
  fabricante: string | null;
  variante: string | null;
  revisao_produto: number | null;
  descricao_original: string | null;
  codigo_loja: string | null;
  gtin: string | null;
  quantidade_original: string | null;
  unidade_original: string | null;
  custo_unitario_original: string | null;
  desconto_item: string | null;
  conteudo_embalagem: string | null;
  unidade_conteudo: string | null;
  fator_aplicado: string;
  aprovacao_excepcional: boolean;
  dados_completos: boolean;
}
export interface CompraDetalhada extends CompraResumo {
  itens: { id: string; ingrediente_id: string; produto_id: string | null;
    movimentacao_id: string; quantidade_principal: string; custo_normalizado: string;
    preco_total: string; snapshot: SnapshotCompra }[];
}
