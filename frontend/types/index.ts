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
  unidades_alternativas?: Array<{ unidade: string; fator: string; observacao?: string | null }>;
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
  custo_embalagem: string;
  custo_operacional: string;
  custo_mao_obra_direta: string;
  custo_total: string;
  custo_por_unidade: string;
  preco_minimo: string;
  preco_recomendado: string;
  /** Preço sugerido para venda via iFood (cobre comissão + cartão). Nulo sem taxas. */
  preco_recomendado_ifood: string | null;
  tempo_total_minutos: number;
  tempo_ativo_minutos: number;
  tempo_passivo_minutos: number;
  lucro_estimado: string | null;
  margem_real: string | null;
  custo_por_hora_produzida: string | null;
  lucro_por_minuto: string | null;
}

export interface Receita {
  tipo_cadastro?: "receita_base" | "produto";
  id: string;
  tenant_id: string;
  nome: string;
  categoria: string;
  rendimento: string;
  rendimento_unidade: string;
  margem_desejada: string;
  preco_de_venda_real: string | null;
  modo_preparo: string | null;
  foto_url: string | null;
  created_at: string;
  updated_at: string;
  ingredientes: IngredienteReceita[];
  etapas: EtapaReceita[];
  custo: CustoDetalhado | null;
}

export type StatusPedido =
  | "orcamento"
  | "aprovado"
  | "em_producao"
  | "finalizado"
  | "entregue"
  | "cancelado";

export interface Cliente {
  id: string;
  tenant_id: string;
  nome: string;
  telefone: string | null;
  observacoes: string | null;
  created_at: string;
}

export interface PedidoItem {
  id: string;
  receita_id: string;
  nome_receita: string;
  quantidade: string;
  preco_unitario: string;
  subtotal: string;
  observacoes: string | null;
}

export interface Pedido {
  id: string;
  tenant_id: string;
  numero: number;
  cliente_id: string | null;
  cliente_nome: string | null;
  status: StatusPedido;
  data_entrega: string | null;
  valor_total: string;
  observacoes: string | null;
  foto_referencia_url: string | null;
  created_at: string;
  updated_at: string;
  itens: PedidoItem[];
  proximas_transicoes: StatusPedido[];
}

export type StatusOP = "planejada" | "em_producao" | "finalizada" | "cancelada";
export type CanalVenda = "loja_fisica" | "whatsapp" | "ifood" | "instagram" | "outro";

export interface OrdemProducao {
  ficha_snapshot?: {
    ficha: import("@/hooks/use-ficha-tecnica").FichaTecnica;
    revisao: number;
    nome: string;
    rendimento: string;
    unidade: string;
    materiais: Record<string, string>;
    bases: Record<string, string>;
    consumo?: import("@/hooks/use-ficha-tecnica").ConsumoComponente[];
  } | null;
  id: string;
  tenant_id: string;
  numero: number;
  receita_id: string;
  nome_receita: string;
  /** Rendimento da receita por fornada (ex: brownie rende 20 un/fornada). */
  receita_rendimento: string;
  receita_rendimento_unidade: string;
  pedido_id: string | null;
  pedido_numero: number | null;
  /** Em fornadas/execuções da receita (não em unidades finais). */
  qtd_planejada: string;
  /** Em unidades finais reais que saíram (não em fornadas). */
  qtd_produzida: string | null;
  status: StatusOP;
  data_prevista: string | null;
  observacoes: string | null;
  created_at: string;
  updated_at: string;
  proximas_transicoes: StatusOP[];
}

export interface VendaItem {
  id: string;
  receita_id: string;
  nome_receita: string;
  quantidade: string;
  preco_unitario: string;
  subtotal: string;
  observacoes: string | null;
}

export interface Venda {
  id: string;
  tenant_id: string;
  numero: number;
  cliente_id: string | null;
  cliente_nome: string | null;
  canal: CanalVenda;
  data_venda: string;
  valor_total: string;
  observacoes: string | null;
  created_at: string;
  itens: VendaItem[];
}

export interface EstoquePA {
  receita_id: string;
  nome_receita: string;
  qtd_disponivel: string;
  qtd_minima: string;
  status: "ok" | "baixo" | "zerado";
}

export interface MovimentacaoEstoquePA {
  id: string;
  receita_id: string;
  tipo: "entrada" | "saida" | "ajuste";
  quantidade: string;
  origem: string;
  created_at: string;
}

export interface MovimentacaoEstoque {
  id: string;
  ingrediente_id: string;
  tipo: "entrada" | "saida" | "ajuste";
  quantidade: string;
  custo_unitario: string;
  origem: string;
  created_at: string;
}

export type TipoAgendaItem = "receita" | "pedido" | "tarefa";

export interface AgendaItem {
  id: string;
  tenant_id: string;
  titulo: string;
  tipo: TipoAgendaItem;
  data: string; // 'YYYY-MM-DD'
  hora_inicio: string | null; // 'HH:MM:SS'
  hora_fim: string | null;
  cor: string | null;
  concluido: boolean;
  observacoes: string | null;
  receita_id: string | null;
  pedido_id: string | null;
  ordem_producao_id: string | null;
  nome_receita: string | null;
  nome_pedido: string | null;
  numero_op: number | null;
  duracao_minutos: number | null;
  created_at: string;
  updated_at: string;
}

export type ViewAgenda = "mes" | "semana" | "dia";

export interface CriarAgendaItemPayload {
  titulo: string;
  tipo: TipoAgendaItem;
  data: string;
  hora_inicio?: string | null;
  hora_fim?: string | null;
  cor?: string | null;
  observacoes?: string | null;
  receita_id?: string | null;
  pedido_id?: string | null;
  ordem_producao_id?: string | null;
}

export type AtualizarAgendaItemPayload = Partial<
  CriarAgendaItemPayload & { concluido: boolean }
>;

export interface MoverAgendaItemPayload {
  data: string;
  hora_inicio?: string | null;
  hora_fim?: string | null;
}

export interface ItemCompraSugerido {
  descricao: string;
  quantidade: string;
  unidade: string;
  preco_unitario: string;
  preco_total: string;
  /** Ingrediente existente sugerido para vínculo (null = sem correspondente). */
  ingrediente_id: string | null;
  nome_match: string | null;
  /** Confiança do match (0 a 1). */
  score: number;
  /** Para itens novos: tipo e unidade já normalizados. */
  tipo_sugerido: TipoIngrediente;
  unidade_sugerida: string;
}

export interface OcrComprasResponse {
  itens: ItemCompraSugerido[];
  total: string | null;
  estabelecimento: string | null;
  fonte: string;
  confianca: number | null;
  avisos?: string[];
}

export interface ItemConfirmadoPayload {
  ingrediente_id?: string | null;
  criar_novo: boolean;
  nome: string;
  tipo: TipoIngrediente;
  unidade: string;
  quantidade: number;
  custo_unitario: number;
}

export interface ConfirmarCompraPayload {
  itens: ItemConfirmadoPayload[];
  estabelecimento?: string | null;
}

export interface ConfirmarCompraResponse {
  ingredientes_criados: number;
  ingredientes_atualizados: number;
  itens: Ingrediente[];
}

export interface ItemListaCompras {
  ingrediente_id: string;
  nome: string;
  unidade: string;
  saldo: string;
  estoque_minimo: string;
  status_estoque: "baixo" | "critico" | "zerado";
  quantidade_sugerida: string;
  custo_estimado: string;
}

export interface ListaComprasResponse {
  itens: ItemListaCompras[];
  custo_total_estimado: string;
}

export interface ApiError {
  detail: string;
}
