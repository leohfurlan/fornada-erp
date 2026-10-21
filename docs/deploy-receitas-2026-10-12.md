# Publicação de receitas, nomes e histórico — 12/10/2026

Commit, push e deploy executados após autorização explícita do usuário. Alterações independentes dos checkouts foram preservadas e não entraram nos commits desta entrega. As branches existentes foram enviadas sem force-push; não houve merge automático em main/master.

## Fontes publicados

| Aplicação | Branch enviada | Commits de implementação |
| --- | --- | --- |
| Fornada | `codex/compras-produtos-aprovados` | `dbd2288` — consulta integral, nomes e versões; `2e15757` — compatibilidade das configurações OCR |
| Central | `codex/overview-contact-identity` | `44bea6c` — integração F08 de receitas |

A publicação foi incremental sobre as imagens/fontes ativos, preservando OCR híbrido, marca, custo por unidade base, iFood e proxy. Não foi utilizado o checkout inteiro como pacote de deploy. Os fontes do backend ativo e o arquivo de fontes do frontend publicado foram usados para compor e testar a release Fornada. A Central preservou o backend publicado e o proxy dinâmico da imagem web.

Os testes da release exata detectaram uma inconsistência preexistente: adapters OCR publicados acessavam sete campos ausentes de `Settings`. Esses campos foram restaurados no commit `2e15757`, sem remover as configurações Central/iFood. As seis regressões OCR inicialmente falhas passaram após a correção. Os exemplos de ambiente também foram documentados; o ambiente privado de produção foi preservado.

## Ambientes e migrations efetivamente aplicadas

| Aplicação | Servidor / banco / schema | Antes | Depois |
| --- | --- | --- | --- |
| Fornada | VPS `fornada`, PostgreSQL exclusivo `fornada`, `public` | `a85c10b7d302` | **`f17d5b4e421d`** |
| Central | VPS `atos-pd`, PostgreSQL exclusivo `central`, `public` | `0012_purchases` | **`0013_recipes`** |

Destinos, releases ativas e revisões foram conferidos antes das alterações. As imagens novas reportaram uma única head esperada no preflight. Escritores foram parados para o backup e o upgrade, depois reiniciados. Cada backup foi restaurado com `--exit-on-error` em banco temporário e validado antes de migrar o banco principal. Os bancos temporários foram removidos após essa verificação; nenhum dado principal ou volume foi restaurado/removido. Não houve downgrade.

Backups privados preservados:

- Fornada: `/opt/fornada/backups/recipes-20261012T181011Z.dump`.
- Central: `/opt/talk2me/backups/recipes-20261012T181746Z.dump`.

## Releases ativas

- Fornada: `/opt/fornada/releases/recipes-dbd2288`; backend/Celery/iFood `fornada-backend:recipes-2e15757`; frontend `fornada-frontend:recipes-dbd2288`.
- Central: `/opt/talk2me/releases/recipes-44bea6c`, também apontada por `/opt/talk2me/current`; API/workers `talk2me-backend:recipes-44bea6c`; web `talk2me-web:recipes-44bea6c`.
- Scripts, logs, indicação de backup e estado `COMPLETE` permanecem em cada release. Para administrar os serviços, usar os arquivos Compose registrados nos labels dos containers ativos, incluindo `compose.recipes.yml`; executar isoladamente um Compose anterior pode selecionar imagens antigas.
- PostgreSQL, Redis, proxy, volumes, credenciais e vínculos existentes foram preservados. Não houve envio de mensagem de teste externa.

## Evidências de validação

- Fornada, checkout de implementação: 400 testes passaram, 4 OTP ignorados por falta de Redis isolado; frontend 88 testes, TypeScript e build aprovados.
- Fornada, fontes exatos da release com OCR publicado: **380 passaram, 4 ignorados**. Build Linux da imagem frontend concluído.
- Central: suíte completa inicialmente com **298 testes aprovados, 12 erros de preparação e 1 HTTP ignorado**; os 12 erros eram exclusivamente ausência de `CENTRAL_TEST_RCLONE_BINARY`. Com o rclone já instalado configurado, **todos os 12 ensaios passaram**. O teste HTTP opt-in foi então executado separadamente e **passou**. Total validado nesta rodada: **311 testes**, sem falha remanescente. Os ensaios cifrados usam armazenamento local, sem envio ao Drive.
- Central frontend: **72 testes passaram**, TypeScript/Vite build aprovado.
- O HTTP local usou os fontes preparados da release Fornada e PostgreSQL real isolado; somente o transporte final WhatsApp foi simulado. Não é prova de entrega real no WhatsApp.
- Produção Fornada: serviços reiniciados saudáveis, `/health` aprovado e login acessível. OpenAPI da imagem ativa contém histórico de versões e leitura de receitas; validação em memória confirma maiúsculas e recusa de emoji sem inserir dados de cliente. Histórico sem autenticação retorna **401**.
- Produção Central: API saudável e workers/web ativos; HTTPS frontend aprovado; `/api/auth/me` sem sessão retorna **401**. Inspeção read-only confirmou `0013_recipes`, tabela `recipe_flows` e colunas de rastreamento nas mensagens. Configuração efetiva confirma receitas desativadas.

Dois ajustes no procedimento foram necessários: normalizar LF no script da Central antes de seu preflight e adaptar a verificação de rotas Fornada para consultar OpenAPI, pois a versão FastAPI publicada contém `_IncludedRouter` sem atributo `path`. Ambos foram corrigidos e as verificações finais passaram. Não exigiram rollback de aplicação ou de banco.

## Limites e pendências

Nomes de novos cadastros e edições já usam a validação publicada; edições registram histórico e a tela permite consultá-lo. A limpeza em massa de nomes antigos não foi executada: requer revisão da prévia por tenant e tratamento manual dos nomes que ficariam vazios.

A consulta automática de receitas no WhatsApp permanece **desativada** (`recipes_enabled=false` nos conectores). Publicação não incluiu alteração de homologação, início de ativação, escopo autorizado ou envio externo. Ativação por negócio/tenant e piloto com entrega real seguem pendentes. As compras e os demais fluxos previamente ativos mantêm suas configurações.
