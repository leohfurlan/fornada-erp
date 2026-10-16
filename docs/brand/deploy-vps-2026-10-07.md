# Publicação da identidade Forno aberto na VPS

Em 07/10/2026, às 17:58 (America/Sao_Paulo), foi publicada a identidade oficial rosa e marrom com contorno em https://fornada.atospd.com. O [PR #7](https://github.com/leohfurlan/fornada-erp/pull/7) permanece aberto para revisão.

## Release publicada

- Código: `775b2f9090569e66392c42480c80ef9bed363a43`, branch `codex/identidade-forno-rosa`, baseada em `main` no commit `f15604d`.
- Imagem Linux/amd64: `fornada-frontend:forno-rosa-775b2f9`.
- ID da imagem executada: `sha256:c9ea5e76ef8ded17f70dd34285271cd71b6c4ab8e2fc18fc16b9737e3339e036`.
- Release: `/opt/fornada/releases/forno-rosa-775b2f9`.
- Container: `fornada-prod-frontend-1`, iniciado em `2026-10-07T20:58:41.561536458Z`.
- Fonte e imagem foram preparadas localmente e transferidas por SSH. O código extraído na VPS corresponde ao commit acima; o checkout existente não foi sobrescrito.

A imagem foi construída com o Dockerfile de produção, com lint e tipos aprovados. A publicação usou Compose com `--no-deps --no-build --pull never --force-recreate frontend`. A comparação com o frontend da release anterior confirmou que a atualização reúne somente a identidade visual.

## Verificação em produção

- `/login?email=1`, `/manifest.webmanifest` e `/health` responderam HTTP 200 por HTTPS, também a partir de um cliente externo à VPS.
- Saúde da API: `{"status":"ok","version":"0.1.0"}`.
- HTML do login usa `/brand/forno-v2/logo-horizontal-primary.svg`.
- Manifest: tema `#E7A0B3`, fundo `#FFF7FA`, ícones 192/512 px e maskable 512 px na pasta da versão 2.
- Sete arquivos publicados foram comparados byte a byte com a release: logo horizontal, favicon SVG, favicon ICO, Apple Touch Icon, app icons 192/512 e maskable 512.
- Login real revisado no navegador em larguras de 390 px e 1440 px: logo carregado, sem rolagem horizontal, contraste do botão de 5,82:1, sem erros de console.
- As capturas abaixo mostram produção sem autenticação. Nenhuma sessão ou dado fictício foi injetado na VPS.

[Login no celular](aplicacao-forno-v2/producao/login-mobile.png) · [Login no desktop](aplicacao-forno-v2/producao/login-desktop.png).

A área autenticada foi validada localmente com dados fictícios na etapa de implementação. Esta publicação verificou em produção as páginas públicas e os arquivos compartilhados; não realizou operações de negócio nem instalação em aparelhos Android/iOS.

## Serviços e dados preservados

Os IDs e horários de início da API, worker Celery, PostgreSQL, Redis e proxy foram registrados antes e depois da publicação e permaneceram idênticos. Não foram executadas migrations, importações, alterações de dados, reinícios desses serviços ou atualização do backend. Alterações locais e remotas de outros trabalhos foram preservadas.

## Validação anterior à publicação

- Backend: 293 testes aprovados; 4 testes OTP/Redis pulados por ausência de `TEST_REDIS_URL`, usando PostgreSQL temporário e isolado.
- Frontend desta branch: 53 testes aprovados em 12 arquivos; TypeScript aprovado.
- Kit: 23 verificações aprovadas, incluindo geometria, cópias dos assets, dimensões, ICO e área segura maskable.
- Build de produção Linux/amd64, lint e tipos aprovados.
- Login e painel validados localmente em desktop e celular.

O registro da implementação local menciona 58 testes porque naquele checkout havia cinco testes de um trabalho concorrente. A suíte da branch isolada e publicada contém 53; os demais testes e alterações não integram este PR.

## Integridade e rollback

Os checksums foram confirmados na VPS antes da extração e troca:

| Arquivo | SHA-256 |
| --- | --- |
| `frontend-775b2f9.tar.gz` | `1853a30a906f54a4d4da904f1e6ec36ff2a70d7ba180fd619695f27acadc7e64` |
| `source-775b2f9.tar.gz` | `12809f46490c4be0a9fdddc8b3414d795fd16818be466781e4410da4b0b9c94e` |

A imagem anterior foi preservada como `fornada-frontend:before-forno-rosa-775b2f9`, ID `sha256:72bbf64c18f1afe76cd6ac5b7d05ed30c7a02658793aa3d39ddbbdd360e593e0`.

O script `deploy-frontend.sh` da release mantém rollback automático em caso de falha após a troca, usa trava `/opt/fornada/.deploy.lock` e valida a imagem anterior antes de agir. Não houve necessidade de rollback. Para retorno operacional futuro, alterar somente a imagem do frontend em `docker-compose.brand.yml` para a tag preservada e aplicar a mesma composição da release com `--no-deps --no-build --pull never --force-recreate frontend`, preservando os demais serviços. Revalidar a release ativa antes de executar.

As evidências remotas ficaram na pasta da release: `SOURCE_REVISION`, `frontend-before.txt`, `frontend-after.txt`, `protected-before.txt`, `protected-after.txt`, HTML, manifest e cópias dos assets consultados.
