# Publicação da padronização de erros — 15/10/2026

Código: `5166161`, após autorização explícita para commit e deploy. O commit contém apenas a validação; alterações locais de marca, layout, infraestrutura e simplificação de compras foram preservadas fora dele. Sem push ou migração nesta atividade.

Release: `/opt/fornada/releases/validation-20261015`. Backend, Celery e iFood usam `fornada-backend:validation-5166161`; frontend usa `fornada-frontend:validation-5166161`. Backend derivado de `receipt-20261015`, com patch aplicado dentro da imagem para preservar OCR e integrações. A exportação de fontes foi recusada pela revisão automática e não foi executada; a publicação seguiu por aplicação interna do patch autorizado.

O primeiro preflight detectou uma publicação concorrente do frontend e parou antes de alterar serviços. A release foi recomposta sobre `purchases-guide-20261015`, preservando a simplificação de compras, cálculo de preço pelo total e guia de primeiros passos já publicados. O manifesto SHA-256, cadeia Compose, imagens anteriores e procedimento de reversão estão na pasta da release.

Validação da implementação: 122 testes distintos frontend, 277 testes unitários backend, TypeScript, schemas centrais e build Linux aprovados. A release final preservando o frontend mais recente passou em 23 testes focados durante o build. O preflight HTTP usa payload sintético inválido com dependências de persistência substituídas: confirma campo/item, mensagens em português e ausência dos valores enviados na resposta. Não houve compra, movimentação de estoque, chamada de IA ou envio de mensagens por esses testes.

Estado final: `COMPLETE`. Backup conferido com `pg_restore --list`: `/opt/fornada/backups/validation-20261015T161910Z.dump`. Não houve migração ou restauração de dados principais.

Preflight aprovado: `HTTP_FIELD_ERRORS_OK`, `CROSS_FIELD_VALIDATION_OK`, `INTEGRATION_FLAGS_PRESERVED` e `VALIDATION_PREFLIGHT_OK`. Verificação pública aprovada: `PUBLIC_VALIDATION_JS_AND_CSS_OK`; `/health` retornou `{"status":"ok","version":"0.1.0"}` e login acessível. Backend saudável e frontend/Celery/iFood ativos. Houve 502 transitório durante a recriação, seguido de sucesso nas tentativas e verificações finais.

O aceite em aparelho Android não foi repetido nesta publicação. Atualizar/reabrir o aplicativo carrega os novos arquivos. Falhas de preenchimento recebem campo vermelho, mensagem associada, identificação do item e resumo; falhas operacionais sem campo responsável continuam como aviso geral.
