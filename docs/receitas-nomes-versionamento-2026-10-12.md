# Validação de nomes e versionamento de receitas

Data: 12/10/2026. Implementação e validação locais, sem commit, push, deploy, ativação ou envio externo.

## Resultado

Nomes de receitas, produtos com composição e produtos comerciais de compra são normalizados para Unicode NFC e letras maiúsculas, com espaços consecutivos consolidados. Emojis, caracteres invisíveis, nomes vazios e nomes maiores que 200 caracteres são rejeitados pela API. A interface orienta e valida o preenchimento. Marcas, fabricantes, categorias, ingredientes de estoque e textos editoriais não são convertidos: o escopo é o nome dos cadastros de receita/produto.

Preparo, montagem, acentos, Markdown, quebras de linha e quantidades permanecem preservados. Produtos novos preparados na conferência de compras também passam pela regra, sem modificar a descrição original observada no documento.

Antes havia somente `ficha_revisao`, um contador para evitar sobrescrita da montagem, sem histórico integral das edições. Agora a receita possui `versao`, e `receita_versoes` armazena snapshots dos campos editáveis, ingredientes, quantidades, etapas e ficha técnica. Criação começa na versão 1; edição e alteração da montagem registram versões seguintes com data, origem e usuário autenticado, na mesma transação. Cópia recebe histórico próprio, começando em 1. Custos históricos não são recalculados.

Cadastros antigos recebem o snapshot anterior imediatamente antes da primeira edição registrada. Esse registro é identificado como `base_anterior`, com autoria desconhecida, sem inventar autor ou data da alteração original. Não há reconstrução de versões anteriores que nunca foram registradas. As referências de sub-receitas são preservadas no snapshot da receita editada; esse histórico não congela recursivamente o conteúdo de todas as receitas referenciadas.

`GET /api/v1/receitas/{id}/versoes` consulta versões por tenant, em ordem decrescente, com `offset` e `limit` limitado a 100. A tela da receita apresenta o histórico paginado, autoria e conteúdo salvo. Não existe operação de restauração neste escopo.

O formulário envia a versão carregada ao iniciar a edição. Se outra alteração já ocorreu, a API retorna 409; o formulário conserva a versão inicial mesmo durante atualização do cache. Clientes antigos podem omitir esse campo por compatibilidade, mas as alterações continuam serializadas e versionadas. A revisão otimista própria da montagem permanece ativa.

## Limpeza dos nomes existentes

`backend/scripts/padronizar_nomes_cadastro.py` produz prévia por tenant por padrão. Com `--tenant-id <UUID> --aplicar`, remove emojis e caracteres invisíveis dos nomes e converte para maiúsculas. Nomes que ficariam vazios ou inválidos são sinalizados e mantidos para correção manual. A limpeza de receitas também registra versões; produtos comerciais incrementam `revisao`, preservando o controle de vínculos comerciais. Snapshots anteriores de receitas e compras não são reescritos.

A prévia, aplicação, isolamento entre tenants e idempotência foram executados em testes com dados sintéticos e rollback. Não foi feita limpeza em nenhum cadastro persistente de cliente. Antes de executar fora do banco isolado, revisar a prévia, identificar o ambiente e obter autorização para esse alvo.

## Migration realmente aplicada

| Item | Valor |
| --- | --- |
| Host local | `127.0.0.1:55439` |
| Banco isolado | `fornada_central_test_recipes` |
| Schema | `public` |
| Revisão anterior | `a85c10b7d302` |
| Revisão posterior / única head | `f17d5b4e421d` |
| Migration aplicada nesta etapa | `f17d5b4e421d_receitas_historico_versoes.py` |

Heads, revisão e colunas foram inspecionadas antes do upgrade. A migration, gerada por Alembic e revisada antes de aplicar, acrescenta `receitas.versao` com default 1 e a tabela `receita_versoes`, incluindo unicidade `(tenant_id, receita_id, versao)`, índices e referências. Não altera revisões já aplicadas, não contém limpeza de dados e não foi executado downgrade.

A comparação posterior dos models com o banco confirmou a estrutura nova. Permanecem somente duas diferenças preexistentes: os índices `ix_agenda_itens_tenant_data` e `ux_estoque_pa_tenant_receita_ativo` existem em migrations anteriores, mas não estão descritos nos models. Foram preservados, removendo suas exclusões indevidas da revisão autogerada antes da aplicação.

A conclusão anterior da auditoria F08 de que o Fornada não precisava de migration correspondia ao escopo da integração de consulta. Este novo requisito de histórico exige a migration acima. A migration `0013_recipes` da Central já havia sido validada e aplicada no schema local isolado da auditoria F08; não foi reaplicada nesta etapa.

## Validação

| Verificação | Resultado |
| --- | --- |
| Backend completo, PostgreSQL isolado | **400 passaram, 4 ignorados** |
| Frontend completo | **88 passaram** |
| Frontend após ajustes finais de preenchimento/compras | **18 regressões pertinentes passaram** |
| TypeScript `tsc --noEmit` | Passou |
| Next.js build | Passou |
| `git diff --check` | Passou |
| Schema pós-migration | Head, colunas, unicidade e índices conferidos |

As 4 exclusões pertencem aos testes OTP que requerem `TEST_REDIS_URL`; não houve Redis isolado configurado nesta rodada. O build inicialmente encontrou EPERM ao criar arquivos gerados em `.next`; a repetição com permissão de execução local concluiu a compilação, checagem de tipos e geração das páginas.

As regressões novas cobrem emojis compostos, bandeiras, keycaps, invisíveis, limites, acentos, símbolos operacionais, preservação de textos, criação/edição/montagem/cópia, autoria, versão desatualizada, baseline legado, rollback transacional, limpeza com prévia, idempotência, paginação HTTP, usuário revogado e bloqueio entre tenants. A suíte completa inclui compras, estoque e consulta de receitas da Central. As chamadas HTTP destes novos testes usam ASGI local e banco PostgreSQL real; não comprovam entrega real no WhatsApp.

## Arquivos desta etapa

- Backend: `domain/nomes.py`; `domain/compras/comercial_schemas.py`; `domain/receitas/{schemas,service,repository,ficha_service,historico}.py`; `api/routers/receitas.py`; `infrastructure/database/models.py`.
- Banco: `backend/alembic/versions/f17d5b4e421d_receitas_historico_versoes.py`.
- Limpeza: `backend/scripts/padronizar_nomes_cadastro.py`.
- Frontend: `lib/{nomes,compras}.ts`; `components/shared/{form-receita,produto-compra-fields,produtos-aprovados,compra-comercial,historico-receita}.tsx`; `hooks/{use-receitas,use-ficha-tecnica}.ts`; `types/index.ts`; páginas de detalhe e edição em `app/(dashboard)/receitas/[id]/`.
- Regressões: `backend/tests/unit/test_nomes_cadastro.py`; `backend/tests/integration/test_receita_versoes.py`; `frontend/tests/{nomes-cadastro.test.ts,historico-receita.test.tsx}`.
- Evidências locais sem credenciais: `.scratch/recipe-review/version-migration-evidence.json`, `version-schema-evidence.json`, scripts `migrate_versions.py` e `check_versions_schema.py`.

As demais alterações preexistentes dos checkouts foram preservadas.

## Pendências para publicação

Revisar as alterações e autorizar a publicação; identificar explicitamente o banco persistente alvo antes de executar a nova migration; revisar a prévia dos nomes existentes e corrigir casos sem nome válido. A implantação precisa publicar backend, migration e frontend de forma coordenada. Ativação da integração WhatsApp e piloto com entrega real continuam sujeitos ao procedimento e à autorização da auditoria F08. Nenhuma dessas ações externas foi realizada.
