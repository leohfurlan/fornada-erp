# Contrato CMP-03 — confirmação e histórico

Contrato r2, 07/10/2026, implementado e validado localmente. Fonte [PRD r2](../../compras-produtos-aprovados.md); [spec](spec.md); [plano](plan.md).

## Provedores e owners

| Provedor | Consumidor | Boundary/owner | Status |
|---|---|---|---|
| CMP-01 | CMP-03 | [Produtos/fornecedores/revisões](../cmp-01/contract.md) | Implementado |
| Estoque | CMP-03 | Ingrediente, conversão para principal, registrar entrada, custo médio | Implementado; lock e retorno de movimento integrados |
| CMP-03 | CMP-02/web | Prévia, confirmação idempotente e histórico | Implementado aqui |
| CMP-03 | WhatsApp/v1 | Mesmo núcleo de escrita com adaptação de metadados disponíveis | Consumidores adaptados e validados |

Rotas novas têm prefixo /api/v1, Bearer e tenant efetivo server-side. Usuario efetivo e operador real são derivados das dependencies; nunca recebidos do body. Nenhuma referência de outra conta é aceita.

## Request comum v2

Rejeitar campos extras; UUIDs em string; decimais em strings finitas com ponto. Totais/descontos BRL têm até 2 casas; preço por unidade fiscal aceita até 8 casas/16 dígitos totais, inclusive as quatro casas do cupom. Preço/total positivos; desconto >= 0. Quantidades/conteúdo têm até 8 casas/16 dígitos totais; conversão e saldo resultante precisam caber no Numeric(12,4) do estoque, sem perda de quantidade. Arredondar preço normalizado a oito casas e custo médio a quatro, HALF_UP; não arredondar total original para reconstruí-lo.

CompraRevisada:
- itens: lista não vazia, até 100 itens, em ordem fiscal.
- estabelecimento: string 1–200 ou null; data_compra: data ISO YYYY-MM-DD ou null; total_nota: moeda ou null. Data informada inválida é 422; data futura exige correção na revisão.
- fornecedor_id: UUID ou null; fornecedor_novo: {nome, cnpj?} ou null, exclusivo de fornecedor_id. Sem identificação cadastral, conservar estabelecimento e permitir fornecedor_id null; guardar vínculo de loja fica indisponível.
- identidade_nota: string de 44 dígitos confirmada como chave fiscal ou null; identidade_confirmada: bool default false. Extração incerta não ativa detecção forte de duplicidade.
- confirmar_duplicidade: bool default false. Necessário para nova compra com mesma identidade já registrada após alerta.
- origem: web_manual | web_ocr; canal WhatsApp/legado é definido pelo adaptador do servidor.

Cada ItemRevisado:
- ingrediente_id UUID ou criar_novo=true com nome/tipo/unidade_principal para novo material, separados da unidade fiscal; exatamente um modo. Nome/tipo de material existente vêm do servidor. Não permitir novo material junto de produto já vinculado a outro material.
- descricao_original: string 1–500; quantidade: decimal > 0; unidade: unidade fiscal; custo_unitario: preço original > 0; desconto_item: moeda >= 0 default 0; preco_total: total efetivo > 0. Exigir round(quantidade × custo_unitario − desconto_item, 2) = preco_total; ausência de rateio de desconto geral não pode ser preenchida automaticamente.
- produto_id UUID e produto_revisao int positivo, ou produto_novo com os atributos comerciais de CMP-01, ou ambos null (quantidade diretamente medida). Produto novo usa o material deste item; não recebe ingrediente_id duplicado. Modos são exclusivos.
- codigo_loja: string 1–100 ou null; gtin_confirmado: string válida ou null; não inferir natureza universal de codigo_loja.
- aprovar_produto: bool default false; aprovar_fornecedor: bool default false; aceitar_excecao: bool default false. Produto/fornecedor não aprovado exige aprovar especificamente ou aceitar_excecao. Sem produto identificado, aceitar_excecao é obrigatório e dados comerciais ficam incompletos.
- guardar_vinculo: bool default false; conflito_vinculo: {id UUID, revisao int positivo} ou null. Aprender exige fornecedor identificado, produto aprovado após confirmação e unidade/conteúdo revisados. Corrigir vínculo existente exige sua revisão explícita; sem isso é 409.

Para unidade de embalagem un/cx/pct/fardo, quantidade conta embalagens, multiplicada pelo conteúdo do produto. Para unidade diretamente medida em g/kg/ml/l, converter a quantidade fiscal diretamente, sem multiplicá-la novamente pelo conteúdo do pacote. Produto de material contado em un pode ter conteúdo de 1 un ou múltiplos explícitos. Sem produto, somente medida diretamente confirmada na principal ou alternativa cadastrada é aceita; nunca deduzir pacote → kg do texto. O conteúdo por cx/pct representa aquela embalagem comercial inteira, não uma barra interna. Produto conhecido não aceita conteúdo sobrescrito no item; selecionar outra embalagem ou produto_novo.

produto_novo não recebe aprovação por atributo oculto: aprovado deriva exclusivamente de aprovar_produto e da decisão revisada. aprovar_fornecedor=true exige fornecedor existente/novo identificado; com fornecedor null é 422. Produto/loja sem aprovação pode ser usado com aceitar_excecao=true, sem guardar_vinculo ou generalizar autorização. Aprovação em uma compra não confirma automaticamente a natureza universal de um código.

## Interfaces HTTP

| Método/caminho | Request | Response |
|---|---|---|
| POST /compras/v2/prever | CompraRevisada | 200 PreviaCompra, sem gravação |
| POST /compras/v2/confirmar | CompraRevisada + header Idempotency-Key UUID obrigatório | 200 ResultadoCompra, inclusive replay |
| GET /compras/historico | ingrediente_id?/produto_id?/fornecedor_id? UUID, marca? string, data_inicio?/data_fim? ISO, limit=50 (1–200), offset=0 (>=0) | 200 {itens: CompraResumo[], total: int} |
| GET /compras/historico/{compra_id} | — | 200 CompraDetalhada |

PreviaCompra: itens [{indice, ingrediente_id?, nome_material, produto_id?, quantidade_principal, unidade_principal, fator_aplicado, custo_normalizado, preco_total, pendencias: string[]}], total_selecionado, duplicidade: {compra_id, data_registro}[] e pode_confirmar bool. Conflito de referência/unidade/valor retorna erro; pendências de aprovação e duplicidade têm resultado sem estoque. Sem produto novo/seleção em item de embalagem a prévia pode apresentar conversão null e pode_confirmar false. Confirmação exige todas as pendências resolvidas ou exceção admitida.

ResultadoCompra preserva resumo conhecido: ingredientes_criados, ingredientes_atualizados, itens (IngredienteResponse[]) e acrescenta compra_id, data_compra?, fornecedor_id?, data_registro e total_selecionado. Resposta de retry é a original persistida, inclusive valores de estoque retornados naquele instante, não um novo saldo atual.

CompraResumo: id, data_compra?, data_registro, estabelecimento_original?, fornecedor_id?, fornecedor_nome_snapshot?, origem, total_selecionado, metadados_completos bool e quantidade_itens. Ordenar data_compra desc (null por último), data_registro desc, id desc. Filtro por período aplica à data_compra e exclui desconhecidos; UI explica. data_inicio > data_fim é 422. Referências de filtro alheias são 404. Filtros de produto/material/marca selecionam compras que contenham ao menos um item correspondente.

CompraDetalhada acrescenta itens: id, ingrediente_id, nome_material_snapshot, produto_id?, revisao_produto?, nome/variante/marca/fabricante_snapshot?, descricao_original?, identificadores_originais, quantidade/unidade/custo_unitario/preco_total/desconto_item originais quando conhecidos, conteudo/unidade/fator_snapshot?, quantidade_principal, unidade_principal, custo_normalizado, movimentacao_id, aprovacao_excepcional bool, dados_completos bool. Histórico legado pode ter descrição/preço fiscal null; dado em unidade de estoque não é apresentado como quantidade fiscal.

Erro de domínio: {detail: string em português}; validação Pydantic conserva detail lista. 401/403 auth; 404 referência fora da conta/inativa; 409 revisão, chave com payload diferente, vínculo conflitante ou duplicidade pendente; 422 campos/conversão/precisão/aprovação não resolvida. Não fazer escrita parcial antes de devolver erro. UI deve manter formulário e informar como corrigir.

## Idempotência, transação e cancelamento

Chave única por (tenant, Idempotency-Key), persistida com fingerprint canônico da request e identidade efetiva do solicitante. Normalize representação decimal, default e textos antes do fingerprint; ordem dos itens permanece significativa. Consultar replay depois de auth/tenant, antes de validar catálogo atual. Mesmo tenant/chave com outro corpo/solicitante = 409, nunca retorno de dados de outra identidade.

Lock de tenant e constraints evitam duas confirmações simultâneas da mesma chave. Falha antes de commit desfaz compra, chave, movimentos, cadastro e vínculos; retry pode concluir. Timeout depois de commit usa mesma chave. Frontend mantém chave enquanto o conteúdo não muda, inclusive em retry, e não cria nova chave por timeout. Mudança real em revisão gera nova tentativa consciente.

Processar todos os itens em uma transação. Cada item salvo se vincula a exatamente uma movimentação de compra. Saldo e custo devem ser lidos sob lock no momento da entrada. Não usar saldo inicial e entrada adicional para o mesmo material novo.

Vínculo/ aprovação durante revisão só é instrução nesta request; cancelamento ou item ignorado não envia essa instrução e não precisa de endpoint de desfazer. CRUD deliberado de produto fora da compra continua operação independente.

## Compatibilidade e persistência

Tabelas propostas: compras (tenant/chave/fingerprint/resultado, fornecedor e snapshots, datas/origem/identidade fiscal), compra_itens (compra/material/produto/movimento, originais e normalizados). UUID/tenant/timestamps/soft delete; índices por tenant/data, fornecedor, material, produto e chave idempotente. Identidade fiscal indexada para alertas, não unique, pois duplicidade explicitamente revisada é permitida.

Interface v1 existente não recebe campos obrigatórios novos. Adapter registra histórico básico nas novas confirmações, com null nos dados não recebidos, preservando respostas. Sem chave estável no cliente legado, não prometer idempotência de requests independentes v1. A UI migrada usa v2; WhatsApp utiliza UUID do rascunho como chave e passa metadados reais disponíveis. Rascunhos antigos têm null nos campos novos e seguem suas validações de unidade; não inventar valores para completar.

O núcleo retorna resultado e movimento sem commit próprio. A rota faz commit; WhatsApp confirma dentro do savepoint já existente e grava resposta/outbox na transação externa. Previa/confirmar/histórico usam o mesmo resolvedor de unidades.

Testes de contrato: preço/quantidade do exemplo, múltiplas embalagens, filtros/dados desconhecidos, overflow, desconto consistente/inconsistente, replay após inativação, erro parcial, concorrência real, compatibilidade v1/WhatsApp e isolamento com controles positivos. Resultados executados localmente; ver relatório abaixo.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
