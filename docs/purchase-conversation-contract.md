# Compras conversacionais — contrato Fornada / Talk2Me

Implementação local, 2026-10-12. Integra o trabalho de
`codex/purchase-conversation` ao checkout atual. Fonte de requisitos: os quatro
documentos de F08-fornada-compras/revisao-conversacional do Talk2Me.

## Fronteira HTTP

`POST /api/v1/central/conversation-draft` usa o Bearer de serviço existente.
Campos base: `business_id`, `sender_phone`, `operation: purchases.review`,
`scope` opcional e `proposal_id`. Fornada revalida negócio, tenant ativo,
usuário ativo, telefone, escopo e propriedade em cada chamada, inclusive lookup.

| action | Campos adicionais | Comportamento |
| --- | --- | --- |
| read | nenhum | Snapshot atual; pode persistir referências estáveis, sem incrementar versão |
| patch | expected_version inteiro, incoming_message_id UUID, edits não vazio | Patch atômico, versão +1, invalidação de resumo/aprovação/prévia |
| lookup | incoming_message_id UUID | 200 se aplicado; snapshot **atual**, não histórico; 404 se desconhecido |

`edits` admite até 40 operações. Cada operação possui `op`, `item_ref`, `field`
e `value`, conforme sua forma. Campos extras, operações desconhecidas e tipos
incompatíveis retornam 422. Read/lookup não aceitam edits nem expected_version.

- `set_item`: item_ref existente e campo permitido.
- `remove_item`: somente item_ref, sem field/value. Talk2Me deve ter confirmado
  contextualmente a remoção na mesma versão; SIM nunca é decisão de estoque.
- `set_purchase`: sem item_ref; estabelecimento, data_compra, fornecedor_id ou
  fornecedor_novo.nome.

Campos de item: descricao_original, quantidade, unidade, custo_unitario,
desconto_item, preco_total, nome, tipo, unidade_principal, criar_novo,
ingrediente_id, produto_id, produto_revisao, aprovar_produto,
aprovar_fornecedor, aceitar_excecao; produto_novo.{nome,marca,fabricante,variante,
conteudo_embalagem,unidade_conteudo,fator_para_principal}.

Decimais são strings; vírgula é normalizada para ponto. Desconto admite zero;
quantidade/preços/conteúdo/fator exigem valor positivo finito quando preenchidos.
Null permite manter campos ausentes como pendências; booleanos exigem boolean
e produto_revisao exige inteiro positivo. Strings vazias/inválidas não recebem
valores inventados: a validação comercial identifica pendências.

## Snapshot e domínio

Resposta inclui o padrão de draft e `conversation_draft`, `issues`,
`ready_for_review`, `expired`. Itens têm `item_ref` e `occurrences`.
`reviewed` oferece os dados sem esses metadados para o review existente.
Rascunho incompleto não fornece hash aprovável. Um hash prévio também é omitido
do snapshot conversacional se seus dados diferem do rascunho agrupado.

Linhas equivalentes financeiramente válidas agrupam quantidade, desconto TOTAL
e total; preço unitário permanece. Texto e representação decimal são normalizados
para comparação. Material, produto, marca, variante, embalagem, unidade, código
e preço distintos mantêm grupos separados. Cálculo segue arredondamento monetário
HALF_UP do domínio; uma linha inconsistente não participa de grupo válido.
Patch pode agrupar itens que se tornaram equivalentes; conserva o item_ref do
primeiro grupo e audita referências absorvidas em dialogo.merged. Remoções ficam
em dialogo.removed, preservando leitura original. Após mudança de versão o
consumer deve usar as referências do snapshot atual.

IDs selecionados pertencem ao catálogo do tenant. Produto selecionado determina
material/revisão/unidade principal; material selecionado limpa o produto anterior.
Editar marca/embalagem de produto selecionado cria proposta de produto novo,
sem modificar o catálogo. Fornecedor existente e proposta nova são exclusivos.
Conversões são validadas pelo motor comercial; não há equivalência implícita l→kg.
Flags de aprovação no rascunho são intenções para a execução final, sem efeito
permanente durante a edição.

Idempotência fica na proposta, portanto isolada por negócio/proposta/mensagem.
Mesmo payload e versão para a mesma mensagem não incrementam nem reaplicam;
conteúdo diferente retorna 409. Versão obsoleta retorna 409. A implementação
mantém até 200 mensagens aplicadas por proposta e rejeita novas mutações além
desse limite, preservando as chaves anteriores. Catálogo público limita produtos
e fornecedores a 200 e informa truncated; consumer deve intervir nesse caso.

## Revisão, vencimento e execução

Patch limpa revisada, previa, resumo_hash, aprovacao_ref e aprovacao_message_id.
Compras confirmadas, recusadas, com operation_id ou resultado não são editáveis.
Read/lookup continuam consultivos nesses estados, com ready_for_review=false.
Review manual continua aceitando CompraRevisada e sincroniza o diálogo, sem
reutilizar referências de substituições ambíguas; não altera o registro idempotente.

Read/patch/lookup permitem revisão vencida, devolvendo expired=true sem renovar.
Review com renew_expired=true explícito, expected_version atual e dados válidos
renova por 24 horas. Produz nova versão/hash e exige nova decisão. Decision,
approval e execute mantêm bloqueio por expiração e revalidação existente.
Reconcile segue consultivo e não repete estoque.

401/403: autenticação/vínculo; 404: proposta invisível ou mensagem desconhecida;
409: versão, mensagem divergente ou estado proibido; 422: estrutura/catálogo
inválido. As mensagens de conflito do endpoint novo permanecem textos seguros;
os códigos draft_version_changed/draft_message_conflict propostos no Talk2Me
ainda não são um envelope estruturado deste provider. Consumer deve tratar o
status e reconciliar snapshot, sem interpretar texto externo como instrução.

## Migrações e homologação

`b208d193ca01` preservada após a85c10b7d302: coluna JSONB nullable dialogo.
Merge `c409e872a103` une b208d193ca01 e 2a86c837f345, preservando a sequência
f17d5b4e421d (receitas) → 2a86c837f345 (PWA). Nenhuma revisão anterior foi reescrita.

Homologação real Talk2Me/Google/Evolution, ativação por negócio e publicação
coordenada continuam pendentes. OCR sem nenhum item exige revisão manual: o
contrato atual não inclui add_item. Não houve commit, push ou operação de produção.
