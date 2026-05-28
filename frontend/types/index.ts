export interface Usuario {
  id: string;
  tenant_id: string;
  email: string;
  nome: string;
  valor_hora: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  usuario: Usuario;
}

export type TipoIngrediente =
  | "ingrediente"
  | "embalagem"
  | "insumo"
  | "descartavel"
  | "outro";

export interface Ingrediente {
  id: string;
  tenant_id: string;
  codigo: number;
  tipo: TipoIngrediente;
  nome: string;
  unidade: string;
  estoque_atual: string;
  quantidade_reservada: string;
  saldo: string;
  estoque_minimo: string;
  custo_medio: string;
  data_custo_atualizado: string | null;
  status_estoque: "ok" | "baixo" | "critico" | "zerado";
}

export interface EtapaReceita {
  id: string;
  nome: string;
  duracao_minutos: number;
  tipo_mao_obra: "direta" | "indireta";
  ordem: number;
}

export interface IngredienteReceita {
  id: string;
  ingrediente_id: string;
  nome_ingrediente: string;
  quantidade: string;
  unidade: string;
  custo_total: string;
}

export interface CustoDetalhado {
  custo_ingredientes: string;
  custo_operacional: string;
  custo_mao_obra_direta: string;
  custo_total: string;
  custo_por_unidade: string;
  preco_minimo: string;
  preco_recomendado: string;
  tempo_total_minutos: number;
  tempo_ativo_minutos: number;
}

export interface Receita {
  id: string;
  tenant_id: string;
  nome: string;
  categoria: string;
  rendimento: string;
  rendimento_unidade: string;
  margem_desejada: string;
  modo_preparo: string | null;
  foto_url: string | null;
  created_at: string;
  updated_at: string;
  ingredientes: IngredienteReceita[];
  etapas: EtapaReceita[];
  custo: CustoDetalhado | null;
}

export interface ApiError {
  detail: string;
}
