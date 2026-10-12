# F-PWA-01 — Plano r1

Atualização: duas fatias implementadas localmente após aprovação do usuário. [Relatório de execução](implementacao.md). Tickets locais criados; testes, build e QA visual aprovados. Aceite Android e release permanecem pendentes; o texto abaixo preserva o planejamento aprovado.

12/10/2026. [PRD](../../../prd.md) F-PWA-01, revisão 12/10/2026; [spec r1](spec.md); [contrato r1](contract.md). Escopo confirmado; desenho e tickets aguardam revisão. Nenhuma implementação, migration aplicada ou publicação feita nesta formalização.

## Fases e checkpoints

1. Revisar contrato e fatias abaixo. Dependências existentes: autenticação e ADM-01; fornecedor externo navegador exige teste real. Conciliar alterações concorrentes no working tree, especialmente layout, modelos e migration de receitas. Não substituir essas alterações ou presumir que HEAD contém seu comportamento.
2. Entregar convite até evidência administrativa de clique/escolha. Backend de eventos idempotente, migration aditiva isolada, UI após hidratação nos dois canais e consulta/painel mínimos devem funcionar juntos. Checkpoint: conta de teste recebe convite, aceita/recusa/adia e administrador encontra os sinais corretos; usuário comum não lê painel.
3. Completar sinais de instalação e uso e opção manual; validar troca de conta, suporte, storage indisponível, evento tardio, modos standalone/fullscreen e erros de rede. Checkpoint: abrir pelo ícone reflete acesso_app sem inferir estado permanente; sete dias e supressão durante suporte cobertos.
4. Rodar gates da spec, revisão de segurança e mobile 390px; ensaiar migration sobre banco isolado atualizado com cadeia local de Alembic. Chrome Android real confirma fluxo completo. Registrar comandos, resultados e limitações, sem transformar mocks em prova de instalação.
5. Preparar relatório de implementação e sequência de release. Commit/push, aplicação em banco real e deploy dependem de autorização correspondente; preparar não é publicar. Reversão de código preserva tabela/eventos; não derrubar coleta com downgrade destrutivo.

## Proposta de tickets — to-tickets

Proposta local para aprovação de granularidade e dependências. Tracker e labels não confirmados; nada publicado. Após aprovação, um arquivo por ticket em `.scratch/pwa-instalacao/issues/`, ou destino externo explicitamente autorizado. Não exigir configuração externa para manter os documentos locais.

1. **Convite após login com acompanhamento administrativo.** Bloqueado por: nenhum, após confirmação do desenho. Entrega vertical: persistência e consulta restritas, convite elegível nos dois canais, adiamento sete dias, clique e escolha nativa visíveis no painel, testes de identidade, isolamento, suporte, idempotência e hidratação. AC1–3, AC5–8; B1–3/B5–8; E1–5/E7–12 na parte aplicável. Demo independente com sinais efetivamente coletados, sem prometer instalação.
2. **Instalação manual e evidências de uso pelo aplicativo.** Bloqueado por: ticket 1 (contrato e coleta integrados). Entrega vertical: opção manual, appinstalled e acesso_app persistidos e exibidos separadamente, supressão em modo app, diferenças entre aparelhos e aceite real Android. AC4–8; B4–8; E2/E5–12 na parte aplicável. Inclui regressão completa e roteiro de instalação real.

## Definition of done

Todos AC1–8, B1–8 e E1–12 com evidência pública de aprovação/rejeição; contrato e API conformes; nenhum acesso de suporte atribuído a cliente; painel distingue sinais e desconhecidos; testes obrigatórios e TypeScript aprovados ou impedimentos reportados sem declarar conclusão; migration ensaiada isoladamente; Chrome Android e viewport mobile verificados. Documentos prontos não significam código implementado ou produção validada.
