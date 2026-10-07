# Contrato CMP-01 — catálogo comercial

Contrato r2, 07/10/2026, implementado e validado localmente. Fonte [PRD r2](../../compras-produtos-aprovados.md); [spec](spec.md); [plano](plan.md).

## Owners e consumidores

| Provedor | Consumidor | Capacidade/owner | Prontidão |
|---|---|---|---|
| Estoque existente | CMP-01 | IDs de material e unidade principal de Ingrediente | Implementado em schemas/service de estoque |
| CMP-01 | CMP-02 | Produto aprovado, revisão, fornecedor e aprovação | Implementado neste contrato |
| CMP-01 | CMP-03 | Resolver referências, criar produto revisado e aprovar dentro da transação | Implementado; comando de compra pertence ao contrato CMP-03 |

Todas as rotas abaixo incluem prefixo `/api/v1`, autenticação existente e tenant efetivo obtido no servidor. Nenhum tenant_id do body é aceito. Referências de outra conta retornam 404. Quando existir sessão administrativa válida, conservar operador real e usuário efetivo para auditoria.

## Tipos e invariantes

UUID como string; decimais como string de base 10 com ponto, finitos; moeda BRL. Conteúdo e fator têm até 8 casas, positivos, até 16 dígitos totais. Unidade de conteúdo: g/kg/ml/l/un ou alternativa explicitamente convertível do ingrediente. Texto aparado: nome/marca/variante/fabricante 1–200 caracteres quando preenchido; fabricante/variante podem ser null. String vazia não substitui desconhecido.

Produto: id, ingrediente_id, nome, marca (obrigatória), fabricante?, variante?, conteudo_embalagem, unidade_conteudo, fator_para_principal? (Decimal confirmado, só para alternativa não métrica), gtin?, aprovado (bool), revisao (int >= 1), fornecedores_aprovados (UUID[]). Retorno acrescenta tenant_id e timestamps do servidor. Fator métrico exato deriva do sistema; rejeitar tentativa de sobrescrevê-lo.

Fornecedor: id, nome, cnpj? (14 dígitos com validação cadastral de formato/dígitos, sem consulta externa obrigatória), revisao. CNPJ confirmado único ativo dentro da conta; nomes não são únicos. GTIN opcional precisa formato/dígito verificador válidos e confirmação da natureza universal; código de caixa interno não pode ocupar esse campo. Não validar tipo de chocolate só pela marca.

## HTTP implementado

| Método/caminho | Request | Response/status |
|---|---|---|
| GET /compras/produtos | ingrediente_id? UUID, aprovado? bool, limit=50 (1–200), offset=0 (>=0) | 200 {itens: Produto[], total: int}; ativos, ordem nome/id |
| POST /compras/produtos | Produto sem id/revisao/timestamps; ingrediente_id obrigatório; fornecedores_aprovados default [] | 201 Produto, revisão 1; não altera estoque |
| GET /compras/produtos/{id} | — | 200 Produto |
| PATCH /compras/produtos/{id} | revisao obrigatória + campos alterados, inclusive aprovado | 200 Produto, revisão incrementada; ingrediente_id imutável |
| DELETE /compras/produtos/{id} | query revisao obrigatória | 204, soft delete; não apaga histórico |
| GET /compras/fornecedores | q? texto, limit/offset como acima | 200 {itens: Fornecedor[], total: int}, ordem nome/id |
| POST /compras/fornecedores | nome, cnpj? | 201 Fornecedor, revisão 1 |
| PATCH /compras/fornecedores/{id} | revisao + nome?/cnpj? | 200 Fornecedor; revisão incrementada |
| DELETE /compras/fornecedores/{id} | query revisao | 204, soft delete, preserva compras |

Editar fornecedores_aprovados substitui a relação inteira sob revisão do produto e valida todos os fornecedores na conta. Retirar aprovação do fornecedor não apaga vínculo descritivo, mas a próxima compra exige revisão. Não há endpoint separado de “aprovar marca”: aprovação se refere ao produto/variante/material.

Erros: 401/403 conforme auth existente; 404 ausente/fora do tenant; 409 revisão, identificador ativo incompatível ou duplicado; 422 validação/conversão. Erro de domínio conserva `{"detail":"mensagem em português"}`; erros Pydantic podem trazer detail como lista, como FastAPI atual. Cliente deve suportar ambos. Campos extras rejeitados nas requests novas.

## Operações internas compartilhadas

resolver_produto(tenant, id, revisao) retorna produto/material/conversão aprovados ou erro 404/409/422. resolver_fornecedor(tenant, id) e aprovação_fornecedor_produto validam conta e estado. criar/aprovar_em_compra recebe a sessão/transação do owner CMP-03 e nunca faz commit próprio; direitos e validações são idênticos ao CRUD. Não introduzir RPC entre módulos.

Compatibilidade: as APIs de ingredientes e receitas permanecem com seus campos; UI de ingrediente ganha seção comercial separada. Testes de contrato devem demonstrar escala Decimal, referências próprias/alheias, revisão concorrente, identificadores conflitantes e ausência de efeito em saldo/custo/histórico.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
