# Publicação da correção de revisão de compras — 11/10/2026

Publicação autorizada pelo pedido “Faça commit push e deploy”, posterior à revisão. A requisição original recusada continua indisponível; a publicação não comprova a causa daquele caso específico.

## Código publicado

| Sistema | Commit | Branch enviada ao GitHub | Imagem ativa |
|---|---|---|---|
| Fornada | `d5dfa8d` | `codex/compras-produtos-aprovados` | `fornada-backend:review-d5dfa8d` |
| Talk2Me, API e três workers | `4d5937d` | `codex/overview-contact-identity` | `talk2me-backend:review-4d5937d` |
| Talk2Me, frontend | `4d5937d` | mesma branch | `talk2me-web:review-4d5937d` |

Somente os arquivos da correção foram commitados. Alterações locais anteriores e arquivos de outros trabalhos foram preservados e ficaram fora dos commits.

## Composição das releases

As imagens foram construídas sobre as imagens efetivamente em execução, sem reinstalar dependências. Os diretórios antigos de release não refletiam todas as atualizações já publicadas.

- Fornada: base `fornada-backend:8a62322-gemma-vision`. Todos os arquivos substituídos correspondiam à base do commit, exceto `main.py`. Nesse arquivo, a versão do container foi preservada e recebeu somente o ramo de tratamento de erros de `/api/v1/central/review`. OCR e demais diferenças publicadas foram mantidos.
- Talk2Me backend: base `talk2me-backend:1c6efca-review-alerts`; sobreposição somente de `fornada_adapter.py`, `purchases.py` e `fornada_review_errors.py`. Os dois arquivos preexistentes correspondiam à base revisada.
- Talk2Me frontend: build TypeScript/Vite da revisão, sobre `talk2me-web:489c46b-review-grouping`, preservando nginx e sua configuração.
- Fornada: somente o serviço backend foi recriado. Frontend, iFood, Celery, proxy, Redis e PostgreSQL mantiveram suas imagens anteriores.
- Talk2Me: API, messaging, agents, operations e web foram recriados. PostgreSQL e o proxy compartilhado foram preservados. A sessão de 336 horas foi confirmada no runtime novo.

Não houve migração de banco nem alteração intencional das configurações de integração.

## Evidências e recuperação

Fornada:

- Artefatos, script, log e marcador `status=complete`: `/opt/fornada/releases/review-d5dfa8d/`.
- Compose atual preservado em `/opt/fornada/releases/central-20261009-02/`, com os quatro arquivos originais e a sobreposição `/opt/fornada/releases/review-d5dfa8d/docker-compose.review.yml` por último.
- Backup restrito: `/opt/fornada/backups/review-d5dfa8d.dump`.
- Rollback previsto no script: reativar backend com os quatro arquivos Compose originais, sem a sobreposição de revisão.

Talk2Me:

- Release ativa, script, log e marcador `status=complete`: `/opt/talk2me/releases/review-4d5937d/`.
- `/opt/talk2me/current` aponta para essa release.
- Release anterior: `/opt/talk2me/releases/20261010T132928Z-8031057/`.
- Backup restrito: `/opt/talk2me/backups/review-4d5937d.dump`.
- Rollback previsto no script: reativar API, workers e web pelo Compose anterior, preservando o banco. Se realizado posteriormente, também reposicionar o symlink `current` na release anterior.

Ambos os backups foram produzidos com `pg_dump -Fc` e tiveram seu catálogo verificado com `pg_restore --list`. Não foi feita restauração de teste nesta publicação. As imagens anteriores foram mantidas. Os scripts têm lock, conferência das imagens anteriores, verificação de saúde e retorno automático na falha de ativação. Nenhum rollback foi necessário após a troca dos containers.

## Verificação

- Backend completo do Talk2Me, já com o endpoint final de atualização de proposta: **259 testes aprovados**, um aviso de depreciação de TestClient/Starlette; execução em schemas isolados do PostgreSQL local, 271,57 segundos.
- Frontend: `npm run build` aprovado, incluindo `tsc --noEmit` e Vite.
- Testes anteriores da correção: Fornada **357 aprovados e 4 ignorados**, fronteira central final **28 aprovados**, frontend Talk2Me **71 aprovados**. Esses resultados pertencem à etapa de revisão; não representam nova execução integral da Fornada nesta publicação.
- Fornada: backend `healthy`, sem reinicializações observadas após a ativação.
- Talk2Me: API `healthy`; três workers em execução com a imagem corrigida; banco `healthy`.
- Frontend público HTTPS: **200**; `/api/auth/me` sem sessão: **401**.
- POST autenticado à Fornada com corpo sintético vazio: **422**, `detail.code=purchase_review_invalid`, lista de campos com código e orientação segura.
- Mesmo POST feito pelo adaptador real dentro da API publicada do Talk2Me: **422**, diagnóstico estruturado preservado, seis erros de campos obrigatórios.

Os testes HTTP de produção foram deliberadamente inválidos no schema, antes de acessar uma proposta. Não foi submetida uma revisão válida, enviada aprovação, aprovada compra ou executada movimentação de estoque para verificar o deploy. O percurso de correção na interface com uma compra real ainda depende do uso pelo operador.

Contrato e exemplos sintéticos: [erros de revisão v1](talk2me-revisao-compras-erros-v1.md). Diagnóstico e regressões: [relatório da revisão](talk2me-revisao-compras-diagnostico-2026-10-10.md).
