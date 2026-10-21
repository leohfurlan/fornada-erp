# Revisão de compras Talk2Me — diagnóstico e correção

## Evidência e limite do diagnóstico

A requisição original recusada não está disponível nos artefatos locais examinados. Há fotos de cupons, mas elas não demonstram quais campos o operador enviou ao salvar. Não foram consultados nem modificados bancos, compras ou serviços de produção nesta revisão. Não é possível atribuir a ocorrência original a loja, produto, unidade, valores ou versão com a evidência existente.

Foi reproduzida com dados sintéticos a recusa de uma revisão com `aprovar_fornecedor=true`, sem `fornecedor_id` nem `fornecedor_novo`. Antes da correção, o endpoint retornava HTTP 422 com detalhe textual. O teste que exigia `detail.errors[0]` falhou porque `detail` era uma string. A mesma verificação passou após a correção. Isso comprova o cenário e a falha de diagnóstico, não a causa da ocorrência original.

A mensagem informada pelo usuário vem do `except Exception` do endpoint de revisão em `whatsapp-admin/backend/app/purchases.py`. Ele cobre falhas de validação, conflito, acesso, transporte e resposta inválida. `FornadaAdapter.call` descartava o corpo de toda resposta HTTP de erro, e o endpoint convertia essas situações em HTTP 409 genérico. No Fornada, erros de schema eram também reduzidos a “Solicitação inválida”; pendências da prévia eram reduzidas a uma orientação genérica. Havia perda de informação em três pontos.

## Validações verificadas

| Caso | Comportamento real preservado |
|---|---|
| Aprovar loja sem referência | `resolver` exige fornecedor existente ou proposta de novo fornecedor; o texto livre `estabelecimento` não é um cadastro. |
| Aprovar produto sem referência | `resolver` exige produto existente ou `produto_novo`; escolher apenas material não equivale a escolher produto comercial. |
| Material e produto | Produto deve pertencer ao material e ao tenant autorizado. IDs de outra conta não são aceitos nem expostos no erro. |
| Conteúdo e estoque | `CatalogoCompras.fator` usa equivalência métrica ou conversão confirmada; fator explícito não pode contradizer equivalência já existente. Não se infere densidade para converter litros em quilogramas. |
| Unidade fiscal | Para `un`, `cx`, `pct` e `fardo` com produto comercial, quantidade é multiplicada pelo conteúdo da embalagem e seu fator. Para demais casos, a unidade fiscal é convertida diretamente para a principal. |
| Marca | Marca é obrigatória no schema de novo produto. Não há comparação heurística de marca com a descrição do cupom; não foi inventada essa regra. |
| Variante e embalagem | `validar_evidencia` bloqueia contradições explícitas de variante reconhecida e medidas descritas. Não verifica toda variante comercial possível nem garante identidade do produto pela foto. |
| Valores | `quantidade × custo_unitario − desconto_item`, arredondado a centavos com `ROUND_HALF_UP`, deve coincidir com `preco_total`. |
| Seleção parcial | `prever` soma somente os itens enviados. Não exige igualdade com `total_nota` na revisão manual. A preparação automática tem regra mais restrita e não foi flexibilizada. |
| Grupos repetidos | Quantidade, desconto e total enviados já estão somados; o servidor não usa nem multiplica por `occurrences`. A UI continua enviando apenas campos do contrato. |
| Versões | Produto deve coincidir com `produto_revisao`; proposta deve coincidir com `expected_version`. Salvar uma revisão muda versão/hash e invalida a aprovação anterior. |

Salvar usa somente `prever`, antes de persistir a proposta e a prévia na central do Fornada. Criação de loja/produto/material e entrada de estoque continuam exclusivamente no fluxo de execução posterior à aprovação identificada. Os testes confirmam ausência desses efeitos mesmo quando a revisão propõe novos cadastros e aprovações permanentes.

## Correção

- Diagnósticos comerciais possuem código, índice, campo, ação e orientação fixos. As validações continuam recusando os mesmos cenários. Conflitos e referências ausentes preservam seus tipos de exceção no domínio, inclusive para consumidores web existentes.
- `/api/v1/central/review` responde com envelope estruturado para validações e conflitos recuperáveis. Erros de schema não incluem `input`, `ctx`, mensagens de exceção ou nomes de campos desconhecidos.
- Prévia mantém `pendencias` e acrescenta `pendencias_codigos`; a API não interpreta texto traduzível para decidir um código.
- Talk2Me lê no máximo 64 KiB de erros 409/422 da rota de revisão. Somente códigos/campos conhecidos são aceitos; mensagens e ações são reconstruídas de um catálogo local. Corpos desconhecidos, grandes, internos e erros de acesso continuam genéricos.
- O formulário mostra item, campo e orientação, sem fechar a revisão ou perder os campos após recusa. Erros de catálogo permitem atualização explícita.
- Recarregar a tela consultava apenas a cópia local da proposta. O novo comando `refresh-source` busca `draft` no Fornada, revalida identidade e versões e mantém a compra em `review`. Na UI, substituir edições não salvas exige confirmação explícita; não há retry, envio ou aprovação automática.

## Alterações exatas no consumidor

Todas foram implementadas localmente em `C:/Projetos TI/whatsapp-admin`:

| Arquivo | Alteração |
|---|---|
| `backend/app/fornada_review_errors.py` (novo) | Catálogo público e sanitização do envelope; sincronizar códigos com o Fornada ao expandir o contrato. |
| `backend/app/fornada_adapter.py` | Leitura limitada de erros de revisão e `FornadaServiceError.review_detail`. Sem retry ou redirecionamento. |
| `backend/app/purchases.py` | Propaga somente diagnóstico sanitizado, preserva rascunho/versionamento na recusa; acrescenta `POST .../refresh-source` com guardas de conversa, tenant/identidade e concorrência. |
| `frontend/src/purchaseReviewErrors.ts` (novo) | Tipos, parser defensivo, mensagens/ações locais e rótulos de campo. |
| `frontend/src/api.ts` | `ApiError.reviewErrors`, mantendo compatibilidade com chamadas existentes. |
| `frontend/src/Purchases.tsx` | Erros dentro do formulário; mantém edição; atualização explícita de catálogo/proposta. Seleção parcial e agrupamento preservados. |
| `backend/tests/test_fornada_transport_errors.py` | Corpo seguro, desconhecido, interno, grande e índices inválidos. |
| `backend/tests/test_purchase_review_errors.py` (novo) | Endpoint preserva rascunho na recusa; atualização consulta fonte e não prepara envio. |
| `frontend/src/Purchases.test.tsx` | Erro visível sem perder valores e confirmação antes de atualizar proposta. |
| `frontend/src/purchaseReviewErrors.test.tsx` (novo) | Campos conhecidos e descarte de texto privado/desconhecido. |

O [contrato público e os exemplos sintéticos](talk2me-revisao-compras-erros-v1.md) detalham índices, códigos, HTTP e recuperação. O contrato válido de compra permanece `CompraRevisada`; não foram adicionados campos obrigatórios às requisições existentes.

## Validação

Os cenários foram executados somente em PostgreSQL local descartável e schemas isolados da central. As primeiras execuções falharam ao exigir diagnósticos estruturados e recuperação de proposta, antes das respectivas correções. O teste comercial existente de isolamento detectou uma alteração indevida de tipo de erro; essa alteração foi corrigida e o teste original passou.

Resultados finais registrados ao concluir a revisão: ver seção abaixo. As suítes existentes também exercitam aprovações e execução exclusivamente com dados sintéticos; nenhuma compra real foi aprovada ou lançada. Não houve deploy, migration de produção, commit ou push nesta revisão. Alterações locais anteriores foram preservadas.

| Verificação | Resultado |
|---|---|
| Fornada, suíte completa | 357 aprovados, 4 ignorados |
| Fronteira central Fornada, após ajustes finais de apresentação/tipos de erro | 28 aprovados |
| Backend Talk2Me, suíte completa | 259 aprovados; um aviso de depreciação do TestClient/Starlette |
| Endpoint/transportes Talk2Me, após concluir atualização de proposta e guardas de recurso/versão | 13 aprovados |
| Frontend Talk2Me, suíte completa final | 71 aprovados |
| TypeScript | `tsc --noEmit` aprovado |
| Ruff dos arquivos da correção e whitespace nos dois repositórios | Aprovados |

A suíte completa da central precedeu a conclusão do novo endpoint `refresh-source`; o endpoint e suas guardas foram validados novamente pelos 13 testes finais. Não foi afirmada uma nova execução integral após essa última adição. Os quatro testes ignorados da Fornada pertencem à suíte existente.
