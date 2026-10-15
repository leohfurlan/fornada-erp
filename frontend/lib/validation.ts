export interface FieldIssue { path: string; message: string }

const labels: Record<string, string> = {
  nome: "Nome", nome_negocio: "Nome do negócio", email: "E-mail", senha: "Senha",
  marca: "Marca", fabricante: "Fabricante", variante: "Variante",
  conteudo_embalagem: "Conteúdo por embalagem", unidade_conteudo: "Unidade do conteúdo",
  fator_para_principal: "Conversão do conteúdo", gtin: "GTIN/EAN", cnpj: "CNPJ",
  ingrediente_id: "Material", produto_id: "Produto e embalagem", receita_id: "Receita",
  quantidade: "Quantidade", unidade: "Unidade", custo_unitario: "Preço por unidade",
  preco_unitario: "Preço unitário", preco_total: "Total pago pelo item", desconto_item: "Desconto",
  descricao_original: "Descrição do produto comprado", unidade_principal: "Unidade principal",
  estabelecimento: "Nome da loja", fornecedor_id: "Loja da compra", data_compra: "Data da compra",
  identidade_nota: "Chave fiscal", cliente_id: "Cliente", data_entrega: "Data de entrega",
  rendimento: "Rendimento", rendimento_unidade: "Unidade de venda", categoria: "Categoria",
  duracao_minutos: "Duração em minutos", tipo_mao_obra: "Tipo de mão de obra",
  telefone: "WhatsApp", codigo: "Código de verificação", arquivo: "Imagem ou PDF do cupom",
  modo_preparo: "Modo de preparo", observacoes: "Observações", data_inicio: "Data inicial",
  data_fim: "Data final", regiao: "País/região", motivo: "Motivo",
  hora_inicio: "Hora de início", hora_fim: "Hora de término", titulo: "Título", cor: "Cor",
  qtd_planejada: "Quantidade planejada", qtd_produzida: "Quantidade produzida", qtd_minima: "Quantidade mínima",
  custo_operacional_mensal: "Custo operacional mensal", horas_mensais: "Horas mensais", valor_hora: "Valor da hora",
  taxa_ifood: "Taxa iFood", taxa_cartao: "Taxa do cartão", margem_desejada: "Margem desejada",
  receita_base_id: "Vincular ao cadastro", descricao: "Descrição", quantidade_minima: "Quantidade mínima",
  quantidade_maxima: "Quantidade máxima", guardar_vinculo: "Guardar descrição/código",
  cep: "CEP", logradouro: "Rua/avenida", numero: "Número", bairro: "Bairro", cidade: "Cidade", estado: "Estado",
};

export function fieldLabel(path: string): string {
  const parts = path.split(".");
  const label = labels[parts.at(-1) ?? ""] ?? parts.at(-1)?.replaceAll("_", " ") ?? "Dados";
  const groups: Record<string, string> = { itens: "Item", ingredientes: "Ingrediente", etapas: "Etapa", composicao: "Componente", passos: "Etapa", unidades_alternativas: "Unidade alternativa" };
  const context = parts.flatMap((part, i) => groups[part] && /^\d+$/.test(parts[i + 1] ?? "") ? [`${groups[part]} ${Number(parts[i + 1]) + 1}`] : []);
  return [...context, label].join(" — ");
}

export function validationMessage(entry: Record<string, unknown>): string {
  const type = String(entry.type ?? "");
  const ctx = (entry.ctx ?? {}) as Record<string, unknown>;
  if (type === "missing" || type === "value_error.missing") return "Preencha este campo.";
  if (type.includes("string_too_short")) return `Informe pelo menos ${ctx.min_length ?? 1} caractere(s).`;
  if (type.includes("string_too_long")) return `Use no máximo ${ctx.max_length} caracteres.`;
  if (type === "greater_than") return `Informe um valor maior que ${ctx.gt}.`;
  if (type === "greater_than_equal") return `Informe um valor maior ou igual a ${ctx.ge}.`;
  if (type === "less_than") return `Informe um valor menor que ${ctx.lt}.`;
  if (type === "less_than_equal") return `Informe um valor menor ou igual a ${ctx.le}.`;
  if (/decimal|float|int_/.test(type)) return "Informe um número válido.";
  if (/date|datetime/.test(type)) return "Informe uma data válida.";
  if (/uuid/.test(type)) return "Selecione uma opção válida.";
  if (/bool/.test(type)) return "Selecione uma opção válida.";
  if (/too_short/.test(type)) return `Informe pelo menos ${ctx.min_length ?? 1} item(ns).`;
  if (/too_long/.test(type)) return `Use no máximo ${ctx.max_length} item(ns).`;
  const msg = String(entry.msg ?? entry.message ?? "").replace(/^Value error, /, "");
  // Nunca expor mensagens técnicas padrão em inglês ou os valores enviados.
  if (/Input should|String should|valid |required|validation|parsing|JSON|Extra inputs/i.test(msg)) return "Confira o preenchimento deste campo.";
  return msg || "Confira o preenchimento deste campo.";
}

export function fieldIssues(error: unknown): FieldIssue[] {
  const data = (error as { response?: { data?: { field_errors?: unknown; detail?: unknown } } })?.response?.data;
  const entries = data?.field_errors ?? data?.detail;
  if (!Array.isArray(entries)) return [];
  return entries.filter(e => e && typeof e === "object").map(e => ({
    path: Array.isArray(e.loc) ? e.loc.filter((p: unknown, i: number) => !(i === 0 && ["body", "query", "path"].includes(String(p)))).join(".") : String(e.path ?? e.field ?? ""),
    message: validationMessage(e),
  }));
}

export function errorMessage(error: unknown, fallback = "Não foi possível concluir a operação. Tente novamente."): string {
  const issues = fieldIssues(error);
  if (issues.length) return issues.map(i => `${i.path ? fieldLabel(i.path) : "Dados informados"}: ${i.message}`).join(" ");
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  const code = (error as { code?: string })?.code;
  if (code === "ECONNABORTED" || code === "ETIMEDOUT") return "A operação demorou mais que o esperado. Tente novamente; seus dados foram mantidos.";
  if (code === "ERR_NETWORK") return "Não foi possível enviar os dados. Verifique sua conexão e tente novamente.";
  return fallback;
}

export function formIssues(errors: unknown, prefix = ""): FieldIssue[] {
  if (!errors || typeof errors !== "object") return [];
  return Object.entries(errors).flatMap(([key, value]) => {
    if (["ref", "types", "type"].includes(key) || !value) return [];
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "object" && "message" in value && typeof value.message === "string") {
      return [{ path: path.startsWith("root") ? "" : path, message: value.message }];
    }
    return formIssues(value, path);
  });
}
