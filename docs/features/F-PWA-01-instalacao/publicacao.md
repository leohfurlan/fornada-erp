# F-PWA-01 — Publicação em 12/10/2026

Commit, push e deploy autorizados explicitamente pelo usuário e concluídos. Implementação: `0ffee70`, enviada para `origin/codex/compras-produtos-aprovados`. Nenhum merge em main foi realizado. Alterações locais de outros trabalhos preservadas; layout compartilhado foi commitado apenas com os trechos PWA.

## Release efetiva

- URL: https://fornada.atospd.com
- Servidor: alias SSH `fornada`; projeto Compose `fornada-prod`.
- Pacote: `/opt/fornada/releases/pwa-0ffee70`.
- Backend, Celery e iFood: `fornada-backend:pwa-0ffee70`, derivados da imagem ativa `recipes-2e15757`.
- Frontend: `fornada-frontend:pwa-20261012`, construído Linux/amd64 fora da VPS sobre o contexto usado na release `recipes-dbd2288`, com overlay PWA.
- Migration: `f17d5b4e421d` → **`2a86c837f345`**. Não foi incluída a migration independente de compras conversacionais.

Compose preserva a cadeia ativa de Central, OCR, review, renewal e recipes, acrescentando somente override de imagens PWA. Flags `central_enabled`, `ifood_enabled` e `evolution_enabled` eram **true** antes da publicação e permaneceram **true**; nenhum conector ou integração foi ativado/desativado por esta entrega.

## Backup e verificação

Antes da migration: serviços escritores pausados; backup `/opt/fornada/backups/pwa-20261012T182518Z.dump`, restaurado com sucesso em banco temporário. A migration PWA passou nesse banco restaurado antes de ser aplicada no banco `fornada` de produção. Banco temporário removido após verificação; imagens anteriores preservadas para recuperação sem downgrade destrutivo.

A revisão automática bloqueou a exportação do dump para o computador local por possível conteúdo de clientes e ausência de autorização específica para essa exportação. Backup permaneceu na VPS; cópia local não realizada nesta execução. Isso não impediu o deploy nem a restauração de teste remota.

Verificações efetivamente concluídas:

| Checagem | Resultado |
|---|---|
| Build Docker Linux/amd64 | aprovado, TypeScript/lint/build incorporados |
| Backup restaurado + migration candidata | aprovado antes da migration real |
| Banco e metadata PWA | revisão correta; tabela e quatro índices presentes |
| Rotas PWA e Central recipes; compatibilidade OCR | aprovadas no container publicado |
| Backend, frontend, Celery e iFood | saudáveis, release `COMPLETE` |
| HTTPS `/health`, `/login`, `/manifest.webmanifest` | HTTP 200 |
| JS global publicado | contém beforeinstallprompt e appinstalled |
| POST `/api/v1/pwa/eventos` sem autenticação | HTTP 401 |
| GET `/api/v1/admin/pwa/usuarios` sem autenticação | HTTP 401 |

Um preflight inicial pressupunha Central desativada e interrompeu antes de pausar serviços. Consulta live mostrou os três flags habilitados; verificação corrigida para comparar com os valores existentes. Houve HTTP 502 transitório durante a inicialização; nova validação pública confirmou 200 após serviços saudáveis. Não houve escrita de eventos sintéticos em contas de clientes para validar produção.

Os testes locais estão no [relatório de implementação](implementacao.md): 103 frontend, 434 backend e 4 skips existentes. Instalação nativa em Android real continua pendente de aceite; publicação dos assets e eventos simulados não demonstram que um aparelho efetivamente instalou. Após novo login, o convite aparece quando o navegador disponibilizar a instalação; alternativa em Mais → Instalar aplicativo. Se já estiver em modo aplicativo, não oferecer instalação.
