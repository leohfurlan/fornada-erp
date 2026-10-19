# Conclusão de etapas no Modo Cozinha

Implementação local em 18/10/2026, preservando as alterações que já existiam no checkout.

## Investigação antes da implementação

- Aplicação Next.js/React/TypeScript, Tailwind e TanStack Query; API FastAPI/SQLAlchemy/PostgreSQL.
- Tela existente: `frontend/app/(dashboard)/cozinha/page.tsx`. Não foi criada outra rota ou tela de produto.
- Etapas: `projection.blocks`, com `id`, `section`, `title` e `markdown`. Ingredientes, preparo e montagem já tinham navegação independente.
- `backend/domain/cozinha/service.py` monta a projeção; `backend/api/routers/cozinha.py` controla navegação, revisão, lease, heartbeat e recibos idempotentes.
- `CozinhaEstacao.projection` já é JSONB persistido e isolado por tenant e usuário. Não havia checklist.
- Reutilizados: MarkdownContent, ícones Lucide, cards/bordas/espaçamentos Tailwind e cores semânticas. Como não havia token de sucesso, foram adicionados `success` e `success-foreground` à configuração existente.
- Os identificadores de blocos são posicionais. A edição da receita já invalidava sua projeção; essa proteção foi mantida.

## Comportamento entregue

- Todas as etapas da seção de preparo ou montagem ficam visíveis como cards, na ordem original.
- Toque no card ou no botão de 48 × 48 pixels marca/desmarca a etapa. A ordem de conclusão é livre.
- Círculo/check de sucesso, título riscado e descrição com opacidade de 90%, mantendo a leitura e a estrutura do card.
- Transições de cor, check, descrição e barra em 200 ms, desativadas por `prefers-reduced-motion`.
- Vibração opcional de 15 ms pela API nativa do navegador, quando permitida; suprimida com movimento reduzido.
- Botões acessíveis com estado pressionado e nomes como “Desmarcar etapa 2”. Links e outros controles internos não disparam o card.
- Contagem e barra incluem preparo e montagem; ingredientes não são etapas. Barra usa a razão exata; o percentual textual é arredondado. Zero etapas resulta em 0%, sem divisão por zero nem mensagem de conclusão.
- Ao concluir tudo: “Pronto! Bom apetite.”, mantendo a tela e os cards. Desmarcar remove a mensagem.
- “Reiniciar etapas” solicita confirmação nativa do navegador e limpa somente o checklist. O usuário continua na seção atual.
- Navegação anterior/próxima, repetição, abas de seção e controles de estação foram preservados.

## Persistência e concorrência

- `session_id` e `completed_block_ids` ficam na projeção JSONB existente. Sem dependências novas ou migration de schema.
- Pausa, retomada e reinício do aplicativo recuperam a sessão salva, após a ativação/retomada da estação pelo fluxo existente.
- Reabrir a mesma receita inalterada preserva o checklist, tanto por toque quanto pela Alexa.
- Trocar de receita começa uma nova sessão. Reiniciar etapas também gera outro identificador de sessão; não há histórico de preparos anteriores neste modelo de estação única.
- Projeções antigas recebem um identificador ao serem marcadas ou reabertas.
- Alterações da receita invalidam a projeção, impedindo reaproveitar conclusões em IDs posicionais que possam representar outras instruções. É necessário reabrir a versão atual.
- Os novos comandos usam a mesma autenticação, filtros tenant/usuário, bloqueio transacional, lease, revisão esperada e idempotência existentes.
- A atualização atribui um novo objeto JSON à estação, garantindo detecção e gravação pelo SQLAlchemy.
- A interface mostra o resultado imediatamente e aguarda confirmação do servidor. Em erro, remove a atualização otimista, consulta o estado persistido e mostra o aviso existente. Um bloqueio síncrono evita comandos duplicados antes do próximo render.

## Arquivos da implementação

Modificados:

- `backend/domain/cozinha/service.py`: estado e retomada do checklist na projeção.
- `backend/domain/cozinha/schemas.py`: comandos `set_step_completed` e `reset_steps`.
- `backend/api/routers/cozinha.py`: validação e persistência usando o fluxo existente.
- `backend/api/routers/alexa.py`: preservação do checklist ao reabrir a mesma receita; demais alterações locais preservadas.
- `frontend/app/(dashboard)/cozinha/page.tsx`: integração e feedback otimista com proteção contra duplicação.
- `frontend/app/globals.css` e `frontend/tailwind.config.ts`: tokens semânticos de sucesso; demais alterações locais preservadas.

Criados:

- `frontend/components/shared/kitchen-checklist.tsx`.
- `frontend/tests/kitchen-checklist.test.tsx`.
- `frontend/tests/kitchen-page.test.tsx`.
- `backend/tests/unit/test_cozinha_completion.py`.
- `backend/tests/integration/test_cozinha_completion.py`.
- Este relatório.

## Validação

- Frontend completo: **147 testes passaram em 29 arquivos** (`pnpm exec vitest run`).
- TypeScript: **passou**, `pnpm exec tsc --noEmit`.
- Backend completo: **509 passaram, 4 ignorados e 2 falharam** (`pytest -q --tb=short`). As duas falhas preexistentes estão detalhadas abaixo. Execução no PostgreSQL exclusivo de testes `fornada_central_test_checklist_20261018`, com schema aplicado via Alembic. Nenhuma conexão de teste foi apontada para produção.
- Cobertura nova: marcar/desmarcar, conclusão fora de ordem, progresso parcial/total e reversão, zero/uma etapa, confirmação de reinício, links internos, movimento reduzido, eventos duplicados, falha do servidor, remontagem da tela, recuperação JSONB após pausa/nova lease, repetição idempotente, reabertura por toque/Alexa, sessões/receitas distintas, acesso por outro usuário e edição da receita.
- Ruff dos arquivos Python do checklist: passou. A alteração da Alexa é restrita ao import e à preservação da projeção, em arquivo que já tinha outras alterações locais.
- Conferência visual do componente real em prévia temporária: **390 × 844 e 1280 × 900**; marcação fora de ordem e conclusão total verificadas. Prévia removida e servidor encerrado após a conferência. Não foi um aceite em aparelho físico ou validação ponta a ponta da Alexa.
- `pnpm lint` não executa verificações: o projeto abre o assistente de configuração do ESLint. Não foi adicionada configuração fora do escopo.

As duas falhas já existentes na integração da Central foram reproduzidas em uma cópia do backend com os três arquivos iniciais de cozinha restaurados a HEAD, preservando o checkout original:

- `test_integral_snapshot_has_no_costs_and_includes_components`: espera `0.1250 kg` na resposta.
- `test_assembly_material_links_are_resolved_in_same_snapshot`: espera `0.1234 g` nas seções.

Essas falhas dizem respeito à representação de quantidades na Central e não foram alteradas por este trabalho.

## Limitações operacionais

- O fluxo atual exige conexão e estação ativa para gravar comandos; não foi introduzida uma fila offline. Marcações confirmadas permanecem no servidor.
- Tempos já descritos nas instruções continuam visíveis. Os blocos atuais não oferecem um campo de duração estruturada; não foram inferidos tempos nem associados tempos de outras entidades por posição.
- Feedback tátil depende do navegador, dispositivo e permissões; o efeito físico não foi validado em celular real.
- Receitas em texto livre sem lista numerada continuam representadas como um único bloco, seguindo o parser existente.
- Não houve commit, push ou deploy.
