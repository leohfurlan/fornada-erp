# Ticket 04 — Retomada, reconexão e aceite real

## Implementado localmente

- A estação não persiste a lease no browser. Depois de refresh ou reabertura do Chrome, a pessoa precisa retomar explicitamente e a tela lê a revisão atual do servidor antes de pedir uma nova lease.
- A interface acompanha online/offline e visibilidade da aba. Ela pausa busca/ações quando está offline, em segundo plano, sem heartbeat confirmado ou com erro de estado, e sinaliza que o conteúdo exibido pode estar desatualizado.
- Ao voltar para a aba, tenta heartbeat imediatamente. Se a lease expirou ou foi tomada por outra aba, limpa a lease local e pede retomada explícita.
- Respostas de polling tardias não substituem uma revisão mais nova que já esteja no cache, inclusive quando a resposta tardia informa que nada mudou.
- `ALEXA_ENABLED` funciona como opt-in global, desligado por padrão. Quando ligado, exige IDs da skill e OAuth, segredo de pelo menos 24 caracteres e frontend/redirects HTTPS. O vínculo individual ainda exige consentimento; a tela oferece revogação.
- O registro de aceite contém o roteiro de Chrome/Mac/Echo, ruído da cozinha, retomada, revogação e rollback. Nenhum cenário físico foi marcado como executado.

## Arquivos centrais

- `frontend/app/(dashboard)/cozinha/page.tsx` — retomada, detecção de indisponibilidade, heartbeat e proteção contra revisão regressiva.
- `backend/core/config.py`, `.env.example` e `backend/tests/unit/test_alexa_feature_flag.py` — configuração e validação do kill switch.
- `docs/features/F-COZ-01-modo-cozinha-alexa/contract.md`, `plan.md` e `aceite-piloto.md` — contrato atualizado, estado e evidências pendentes.

## Validação local

- `pnpm exec tsc --noEmit` — passou.
- `backend/.venv` Python 3.12: 9 testes focados de feature flag e fala passaram; `py_compile` passou nos módulos focados.
- PostgreSQL temporário `fornada_central_test_fcoz04`, sem volume: todas as migrations aplicadas até `c7e5f2a901bd`; container removido depois da validação.
- Teste de integração novo para a estação, junto dos 9 testes focados: 10 passaram. O cenário cobre retomada/takeover, lease antiga rejeitada, recuperação de revisão e ACK futuro/atrasado.
- Suíte completa do backend: 479 passaram, 4 ignorados, 2 falharam em testes de receitas da Central (`test_integral_snapshot_has_no_costs_and_includes_components` e `test_assembly_material_links_are_resolved_in_same_snapshot`). As falhas não foram modificadas neste ticket e não foram comprovadas contra uma execução de baseline.
- Ruff passou nos novos testes e no módulo de fala; no `config.py` reportou duas linhas longas em linhas fora deste diff.
- `git diff --check` passou; o Git mostrou avisos LF/CRLF de arquivos já alterados no checkout.

## Aceite ainda pendente

O teste automatizado cobre takeover sequencial e ACK monotônico; concorrência real de duas requisições/abas, build completa, navegador no Mac High Sierra, Echo Dot 3, skill Amazon, OAuth real, ruído da batedeira, suspensão/reinício real e demais cenários de AC6/AC7 ainda não foram validados. O Chrome funcionou segundo relato do usuário; falta registrar a versão em `chrome://version`. O registro em `aceite-piloto.md` mantém os resultados físicos como pendentes.

Não houve commit, push, publicação, ativação do flag, configuração Amazon nem aplicação de migration. A aceitação física e qualquer promoção operacional continuam fora do resultado local deste ticket.
