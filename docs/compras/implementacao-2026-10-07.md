# Compras: implementação e validação

Data: 07/10/2026. Escopo aprovado: CMP-01, CMP-02 e CMP-03, nas seis fatias de [tickets](tickets-propostos.md). Autorização: “Validado. Implementar”. Estado da validação inicial: implementação concluída no workspace. Commit, PR e publicação na VPS autorizados posteriormente pelo usuário; evidências da publicação serão registradas ao final. Alterações anteriores de administração, receitas e Markdown foram preservadas.

## Resultado para a confeiteira

No cadastro do ingrediente, a seção **Produtos aprovados** permite informar produtos comerciais, marca, fabricante conhecido, variante, conteúdo da embalagem, GTIN confirmado e lojas aprovadas por produto. Diferentes marcas continuam apontando para o mesmo material das receitas. Cadastrar ou editar esses dados não altera estoque nem custo.

Na primeira leitura, **COBERTURA EM BARRA DR.OETKER 1,01KG** mantém a escolha do material para revisão: a marca sozinha não comprova chocolate branco. A confeiteira pode selecionar **Chocolate branco**, escolher/cadastrar a embalagem, aprovar produto e loja e guardar a descrição ou código desta loja. A confirmação grava todas essas decisões com a compra. A próxima leitura reaproveita o vínculo compatível e explica sua origem.

Produto ou loja não aprovados exigem revisão e permitem aprovação durante a compra. Também é possível registrar uma exceção sem aprovação permanente; essa opção desliga aprendizado e aprovações. Cancelar ou ignorar item não envia uma compra nem aprende uma associação.

Quantidade fiscal e quantidade do estoque permanecem separadas:

| Dado | Uma barra | Duas barras |
|---|---|---|
| Quantidade fiscal | 1 un | 2 un |
| Conteúdo por embalagem | 1,01 kg | 1,01 kg |
| Entrada em estoque | 1,01 kg ou 1010 g | 2,02 kg ou 2020 g |
| Total efetivo | R$ 35,99 | R$ 71,98 |
| Preço comparável | R$ 35,63366337/kg | R$ 35,63366337/kg |

O histórico em **Compras → Histórico de compras**, também acessível pelo ingrediente, filtra material, loja, marca e período e mostra a descrição da nota, marca/fabricante/variante, embalagem, quantidade original, conversão e preço normalizado. Alterar ou inativar cadastros não reescreve a compra antiga. Data desconhecida continua desconhecida, distinta da data de registro.

CMP-04, o relatório para orientar onde comprar, permanece futuro. Este incremento fornece os dados históricos para construí-lo.

## Arquivos centrais

| Parte | Implementação |
|---|---|
| Persistência comercial | [compras_models.py](../../backend/infrastructure/database/compras_models.py), seis tabelas com tenant, soft delete e índices de identificadores/chave |
| Catálogo e aprovações | [catalogo.py](../../backend/domain/compras/catalogo.py), [repository.py](../../backend/domain/compras/repository.py) |
| Contratos e identificadores | [comercial_schemas.py](../../backend/domain/compras/comercial_schemas.py), [identificadores.py](../../backend/domain/compras/identificadores.py) |
| Prévia, confirmação e histórico | [comercial.py](../../backend/domain/compras/comercial.py) |
| OCR e reconhecimento | [reconhecimento.py](../../backend/domain/compras/reconhecimento.py), [gemma_adapter.py](../../backend/infrastructure/ocr/gemma_adapter.py) |
| HTTP autenticado | [compras_comerciais.py](../../backend/api/routers/compras_comerciais.py), registrado em [main.py](../../backend/main.py) |
| Consumidores existentes | [compras/service.py](../../backend/domain/compras/service.py), [whatsapp/service.py](../../backend/domain/whatsapp/service.py), [estoque/service.py](../../backend/domain/estoque/service.py) |
| Cadastro no ingrediente | [produtos-aprovados.tsx](../../frontend/components/shared/produtos-aprovados.tsx), [produto-compra-fields.tsx](../../frontend/components/shared/produto-compra-fields.tsx) |
| Conferência da compra | [compra-comercial.tsx](../../frontend/components/shared/compra-comercial.tsx), [hooks](../../frontend/hooks/use-compras-comerciais.ts), [tipos](../../frontend/types/compras.ts) |
| Consulta | [histórico](../../frontend/app/(dashboard)/compras/historico/page.tsx), [precisão/formatação](../../frontend/lib/compras.ts) |

Endpoints novos sob `/api/v1/compras`: catálogo `produtos`, `fornecedores`, `vinculos`; `v2/ocr`, `v2/reconhecer`, `v2/prever`, `v2/confirmar`; `historico` e detalhe. Os contratos anteriores permanecem disponíveis. V2 exige UUID em `Idempotency-Key`; as referências são verificadas na conta efetiva e os usuários são derivados da autenticação.

## Integridade e compatibilidade

- Prévia e OCR não gravam estoque, aprovações ou aprendizado.
- Confirmação, estoque, movimento, snapshot, cadastros inline e vínculos usam uma transação. Falha tardia desfaz inclusive o primeiro movimento e os cadastros novos.
- Cada item salvo tem exatamente um movimento. Material novo começa zerado e recebe uma entrada.
- Mesma chave e mesmo conteúdo retornam o resultado persistido, inclusive após inativar o produto. Mesma chave com outro conteúdo devolve 409. Duas conexões reais confirmam a mesma compra sem duplicá-la; compras distintas somam saldo sem perder atualização.
- Identidade fiscal confirmada alerta para nota já registrada; repetir exige revisão explícita. Coincidência de preço não é identidade fiscal.
- Código interno e descrição são vinculados à loja e à conta. GTIN só recebe alcance entre lojas quando validado e confirmado como universal. Evidências conflitantes, peso diferente, variante diferente e vínculo com revisão antiga pedem revisão.
- Conversão usa conteúdo da embalagem ou equivalência explicitamente confirmada, sem mudar o fator genérico de “un” do ingrediente. Valores são Decimal; a soma dos itens também deve caber na precisão do estoque.
- O WhatsApp usa a chave do rascunho e o mesmo núcleo. Foto de produto aprovado conserva loja, data e unidade fiscal e converte ao confirmar. Dados ilegíveis, mock e conversão não confirmada continuam exigindo correção. Aprovação completa de novos produtos por conversa permanece futura; o fluxo orienta revisão no Fornada.
- Rascunhos antigos e compras v1 seguem compatíveis e recebem histórico básico, sem inventar atributos comerciais. Movimentos históricos anteriores não foram reconstruídos.

## Validação executada

| Gate | Resultado final |
|---|---|
| Backend completo com PostgreSQL real | **267 passed, 4 skipped** |
| Cobertura `domain.compras` | **92%**; catálogo 87%, confirmação 86%, reconhecimento 88%, adapter de consumidores 100% |
| Frontend completo | **53 testes, 12 arquivos, todos passaram** |
| TypeScript | `tsc --noEmit` passou |
| Build Next.js | `pnpm build` passou, incluindo compras e histórico |
| Ruff direcionado | Arquivos de compras, router novo, modelos novos, OCR, WhatsApp e testes passaram |
| ESLint direcionado | Arquivos frontend novos passaram com `next/core-web-vitals`; config temporária, sem inicializar uma configuração global |
| Alembic | Uma head: `0f6af4c60f80`; upgrade validado em dois bancos descartáveis |
| Diff | `git diff --check` passou |
| Navegador real | Desktop 1280×900 e celular 390×844, sem overflow horizontal nos fluxos verificados |

Os quatro testes pulados pertencem ao OTP preexistente e exigem `TEST_REDIS_URL` isolado; não foram substituídos por testes falsos. O transporte WhatsApp e a saída do OCR foram determinísticos: nenhuma mensagem real nem chamada ao Google foi executada nesta validação. Isso comprova os fluxos e contratos, sem reavaliar a qualidade do provedor de visão real.

Evidências automatizadas em [integração comercial](../../backend/tests/integration/test_compras_comerciais.py), [validação de contratos](../../backend/tests/unit/test_compras_comerciais.py), [regressões WhatsApp](../../backend/tests/unit/test_whatsapp_compras.py), [conferência web](../../frontend/tests/compras-comerciais.test.tsx) e [upload real através do Axios](../../frontend/tests/compras-upload.test.tsx). O teste de upload cobre a transformação multipart que a verificação no navegador identificou e corrigiu.

O navegador confirmou cadastro de duas marcas para um ingrediente, fornecedores específicos, edição de marca, compra manual, upload do anexo para o servidor de QA com OCR determinístico, segunda leitura reconhecida, conversão e confirmação, filtro positivo/negativo e histórico mantendo a marca original após edição.

Capturas locais em [conferência desktop](../../output/playwright/compras-desktop.png), [conferência mobile](../../output/playwright/compras-mobile.png), [cadastro mobile](../../output/playwright/catalogo-mobile.png), [histórico mobile](../../output/playwright/historico-mobile.png) e [compra validada](../../output/playwright/compras-validacao.png). Esses arquivos estão na pasta ignorada de QA e não fazem parte de um commit.

## Migração e entrega operacional

[0f6af4c60f80](../../backend/alembic/versions/0f6af4c60f80_catalogo_comercial_compras_historico.py) foi gerada com Alembic e revisada para excluir alterações alheias de índices. Ela cria seis tabelas comerciais e adiciona `contexto` JSONB aos rascunhos do WhatsApp, com default vazio para os anteriores. Depende de `91ae81c71007`, migration administrativa já presente no working tree antes desta implementação.

Em um banco descartável separado, aplicou-se o schema até `91ae81c71007`, inseriram-se ingrediente com saldo **12,3456**, custo **3,2109** e rascunho v1 sem contexto, e aplicou-se a nova head. Saldo e custo permaneceram exatos; o rascunho conservou seus dados e recebeu contexto vazio. Não houve backfill de compras anteriores.

Os bancos utilizados foram `fornada_compras_test` e `fornada_compras_migration_test`, no PostgreSQL temporário local em `127.0.0.1:55439`. Os testes declararam `DATABASE_URL` e `TEST_DATABASE_URL` explicitamente. Scripts e capturas de QA permanecem em `output/playwright/`; os serviços e o container descartável foram encerrados ao finalizar.

A publicação exige uma etapa operacional separada: revisar também a dependência administrativa preexistente, backup do ambiente alvo, aplicar a cadeia Alembic e publicar backend/frontend com sua configuração normal. Nenhuma dessas operações foi executada em produção. CMP-04, retenção das imagens e aprovação completa pelo WhatsApp continuam fora deste incremento.


## Integração para publicação

A release consolida o painel administrativo e o suporte Markdown que já estavam aplicados na VPS, incluindo a migration `91ae81c71007`, pré-requisito da migration comercial. Arquivos de apresentações, marca e planejamento iFood ficaram fora do commit.

Integrada à `origin/main` em `106a6ad`, preservando o OCR híbrido, Gemma 4 configurável e a validação financeira dos PRs #4 e #5. O contrato comum de extração agora conserva marca, fabricante, variante, embalagem, código, desconto e cabeçalho fiscal durante a validação. O endpoint comercial usa a mesma fábrica de OCR dos consumidores existentes. Confiança ausente continua nula; avisos de reconciliação continuam visíveis na revisão. Testes de regressão comprovam preservação dos metadados e desconto sem alterar o preço original.

Após integração: backend **293 passed, 4 skipped** (OTP sem Redis de teste); frontend **53 passed**, TypeScript e builds Linux/amd64 de backend/frontend aprovados. Publicação usa cópia isolada e imagens correspondentes, sem modificar o checkout com alterações locais da VPS.
