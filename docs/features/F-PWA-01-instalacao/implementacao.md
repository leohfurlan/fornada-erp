# F-PWA-01 — Implementação local em 12/10/2026

Código implementado e validado localmente. Aceite nativo Android e publicação pendentes. [Spec](spec.md), [contrato](contract.md), [plano](plan.md). Escopo e divisão aprovados pelo usuário; alterações preexistentes e trabalho concorrente preservados. Sem commit, push ou deploy.

## Entrega

- Convite após hidratação e identidade autenticada, compartilhado pelos acessos e-mail/WhatsApp. Listener global captura evento nativo antes da entrada; navegador incompatível não recebe oferta inoperante.
- Instalar abre prompt diretamente no gesto. Agora não, Escape e fechamento adiam por sete dias por usuário/navegador. Mais → Instalar aplicativo permite ação manual quando houver evento disponível.
- Modo standalone/fullscreen oculta instalação e registra sinal de acesso uma vez por sessão. Troca de conta descarta eventos pendentes e cancela requisições antigas; escolha e sinal nativo são separados.
- API deriva tenant/usuário do JWT, rejeita identidade no payload e qualquer sessão de suporte. Eventos idempotentes com conflito de conteúdo; duplicatas concorrentes comprovadas em PostgreSQL real.
- Administração inclui usuários sem eventos, datas e contagens independentes. Não declara ausência de instalação nem detecta desinstalação. Telemetria best effort com uma repetição da mesma chave, sem bloquear o ERP.

## Arquivos centrais

`frontend/components/shared/pwa-provider.tsx`, `pwa-install.tsx`, `pwa-admin.tsx`; `frontend/lib/pwa.ts`; integração em providers, layout autenticado e página administrativa. `backend/api/routers/pwa.py`, `backend/infrastructure/database/pwa_models.py`, registro de rota em main e de metadata em Alembic. Migration aditiva `2a86c837f345_pwa_eventos.py`, gerada via Alembic e preenchida com tabela e índices.

A migration parte de `f17d5b4e421d`, preexistente no working tree. Outra sessão criou ramo `b208d193ca01` e merge `c409e872a103` durante o trabalho; ambos foram preservados. O merge atual inclui o ramo PWA. Revalidar grafo antes de uma futura release; não publicar migration PWA sem seus predecessores. Nenhuma migration de outro trabalho foi editada.

## Evidência

| Verificação | Resultado |
|---|---|
| `pnpm test --run`, frontend | 103 aprovados, 20 arquivos |
| `pnpm tsc --noEmit`, frontend | aprovado |
| `pnpm build`, frontend | aprovado, 30 páginas geradas |
| `pytest --tb=short -q`, backend | 434 aprovados, 4 skips existentes |
| `pytest tests/integration/test_pwa.py --tb=short -q`, backend | 5 aprovados após ajuste final de logs |
| Ruff nos novos módulos Python e teste | aprovado |
| Alembic upgrade heads | cadeia completa aplicada em banco vazio exclusivo |
| `git diff --check` | aprovado; avisos de conversão LF/CRLF em arquivos existentes |
| Playwright desktop 1366×900 e mobile 390×844 | modal, adiamento, menu e painel revisados; sem overflow horizontal |

Banco efêmero PostgreSQL 16, localhost porta 54130, banco `fornada_central_test_pwa`, sem dados de desenvolvimento ou produção. A primeira regressão em `fornada_test` teve 411 aprovados, 4 skips e 20 erros de setup por guarda preexistente que exige prefixo `fornada_central_test_`. Banco novo com esse prefixo resolveu a guarda, sem modificar testes alheios. A primeira execução de frontend exigiu adaptar isolamento dos testes administrativos para a nova seção, mantendo testes próprios da seção. Um build intermediário encontrou arquivos em uso no Windows; servidores locais foram encerrados e o build final passou.

QA visual usa dados sintéticos, API interceptada e evento de instalação simulado; comprova interface, não instalação real ou integração navegador/API de ponta a ponta. Testes de API usam banco real, JWT real, dois tenants, usuário revogado e reenvio concorrente. Login WhatsApp é coberto por regressão existente e integração comum no provider; nenhuma mensagem externa foi enviada.

Imagens: [convite mobile](../../../output/playwright/pwa-convite-mobile.png), [convite desktop](../../../output/playwright/pwa-convite-desktop.png), [painel mobile](../../../output/playwright/pwa-admin-mobile.png). Roteiros locais em `.scratch/pwa-instalacao/visual.js` e `visual-admin.js`; tickets em `.scratch/pwa-instalacao/issues/`.

## Pendências de aceite e release

Instalar em Chrome Android real, confirmar ícone, abrir e consultar o sinal no painel com API real. Validar no domínio HTTPS após deploy autorizado; o servidor exige aplicação coordenada da migration antes da nova API. A implementação não faz download de APK nem instala sem confirmação. Não há evidência de instalação nativa nesta execução. Release e migration em ambiente real permanecem sem autorização.
