# F-PWA-01 — Contrato r1

Atualização: contrato implementado localmente após aprovação do usuário. [Evidência de conformidade e limitações](implementacao.md). Instalação Android real pendente de aceite.

12/10/2026. Desenho proposto; produto aprovado conforme [PRD](../../../prd.md), F-PWA-01 de 12/10/2026. [Spec](spec.md), [plano](plan.md). Interfaces abaixo são novas, não implementadas. Contrato aditivo, sem alteração nas respostas de autenticação ou `/admin/usuarios`.

## Provedores e consumidores

| Provedor | Consumidor | Capacidade / identidade | Estado |
|---|---|---|---|
| Navegador | frontend F-PWA-01 | beforeinstallprompt, prompt, escolha, appinstalled, display-mode | externo, suporte variável; validar no Chrome Android |
| Autenticação AUTH-01/02/03 | API e UI F-PWA-01 | JWT e usuário persistido; backend deriva IDs e valida usuário ativo | código existente; usar dependências atuais |
| Suporte ADM-01 | coleta F-PWA-01 | X-Admin-Session identifica impersonação | implementado; coleta deve rejeitar header presente |
| API F-PWA-01 | hook frontend | persistência autenticada de sinais | proposto |
| API administrativa F-PWA-01 | painel ADM-01 | consulta global restrita a superusuário persistido | proposto; reutilizar require_superuser |

## Eventos do navegador

Evento beforeinstallprompt retido em memória expõe `prompt()` e escolha `accepted|dismissed`; chamar somente em gesto explícito. Não assumir suporte ou emissão imediata. appinstalled registra sinal independente, sem assegurar conclusão do WebAPK ou instalação permanente. `matchMedia('(display-mode: standalone)')` ou fullscreen registra modo aplicativo, não origem de instalação comprovada. Eventos anteriores à identidade não são associados retroativamente a uma conta. Descartar callback se identidade/sessão mudou desde início da interação.

## POST /api/v1/pwa/eventos

Bearer JWT obrigatório, ator autenticado ativo via get_authenticated_actor. Rejeitar qualquer X-Admin-Session com 403, antes de gravar; não usar identidade efetiva de suporte. Payload não aceita usuario_id ou tenant_id. IDs próprios são derivados no servidor.

JSON com campos obrigatórios, extras proibidos:

- `event_id`: UUID, chave de idempotência gerada no cliente por ocorrência.
- `browser_id`: UUID aleatório persistido no navegador; se storage bloqueado, UUID em memória. Não é identidade física do aparelho.
- `session_id`: UUID por sessão de observação autenticada; token renovado mantém sessão, reload ou novo login cria outra.
- `tipo`: enum `convite_exibido|adiado|instalar_clicado|confirmacao_aceita|confirmacao_recusada|instalacao_sinalizada|acesso_app`.
- `origem`: enum `automatico|menu|navegador|abertura_app`.

Combinações válidas: convite_exibido/adiado apenas automatico; clique e confirmações automatico/menu; instalacao_sinalizada apenas navegador; acesso_app apenas abertura_app. Escolha desconhecida ou exceção de prompt não gera confirmação aceita/recusada. Não enviar texto livre, tokens, IP, user-agent bruto ou timestamp do cliente. Servidor gera UTC.

Exemplo: `{ "event_id":"10000000-0000-4000-8000-000000000001", "browser_id":"10000000-0000-4000-8000-000000000002", "session_id":"10000000-0000-4000-8000-000000000003", "tipo":"confirmacao_aceita", "origem":"menu" }`.

201 para novo evento, 200 para repetição idêntica: `{ "event_id":"...", "recebido_em":"2026-10-12T15:00:00Z" }`, timestamp original preservado. Unicidade `(tenant_id, usuario_id, event_id)`; mesma chave e payload diferente: 409 com `detail: "Evento já registrado com conteúdo diferente."`. Inserção concorrente deve convergir sem 500. Sem pré-requisito de eventos anteriores: chegada fora de ordem ou eventos ausentes são válidos; o sistema não inventa transições.

401 para sessão inválida conforme dependência atual; HTTPBearer pode retornar 403 por credencial ausente conforme versão instalada (preservar convenção e verificar nos testes). 403 para suporte; 422 padrão FastAPI/Pydantic para dados inválidos, extras ou combinação inválida. Demais erros seguem formato `detail` existente. Falha transacional não deixa evento parcial.

Cliente tenta uma vez e, em erro de rede/5xx, no máximo uma repetição com mesma chave durante a mesma sessão autenticada. Sem fila durável ou replay após troca de conta. Não repetir 4xx, exceto renovação 401 pelo cliente HTTP existente. Telemetria é best effort: falhas podem resultar em ausência de evidência e não interrompem operações do ERP. Não fazer retry de prompt nativo.

## GET /api/v1/admin/pwa/usuarios

Bearer e require_superuser, sem elevar privilégios por payload. Recusar X-Admin-Session com 403 para evitar ambiguidade operacional. Endpoint global explícito: usuário comum não consulta sequer o próprio resumo por esta rota.

Query: `q` string default vazio max 200 (nome/email/negócio, busca escapada como diretório atual); `limit` inteiro default 50, 1–100; `offset` inteiro default 0, mínimo 0. Ordenar email e usuario_id, incluir contas não deletadas e tenant não deletado mesmo sem eventos. Dados da conta seguem diretório administrativo; para eventos, junção obrigatória por tenant_id E usuario_id.

200: `{ "items": [...], "total": 0, "limit":50, "offset":0 }`. Item: `usuario_id`, `tenant_id` UUID; `nome`, `email`, `negocio` strings; `sinais` objeto com uma chave por tipo do POST, cada qual `{ "quantidade": inteiro >=0, "ultimo_em": timestamp UTC|null }`. Ausência = quantidade 0 e data null. Não expor browser_id/session_id no painel agregado. Tipos não são mutuamente exclusivos; o usuário pode ter adiado e acessado em outro aparelho. Não oferecer campo booleano instalado.

Consistência: consulta após commit do POST inclui evento; max(timestamp do servidor) por tipo, sem depender da ordem de chegada. Soma não representa aparelhos únicos nem número garantido de instalações. Paginação não promete snapshot durante inserções/edições concorrentes.

## Compatibilidade e verificação

Testes de API: validação, autenticação, isolamento entre dois tenants, exclusão de suporte, unicidade concorrente, agregados e paginação; mocks de navegador reproduzem apenas este contrato, sem declarar instalação real. UI valida tipos e estados sem depender de objetos privados do Chrome. Checkpoint integrado: login nos dois canais, convite, escolha real no Android, abertura pelo ícone e painel consultado com superusuário. Novo sinal futuro exige revisão coordenada de enums/API/UI; nenhum backfill inferido de dados históricos.

Referências do provedor: [beforeinstallprompt](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event), [experiência de instalação](https://web.dev/articles/customize-install). Revisão consultada nesta conversa; validar comportamento efetivo no aparelho antes do aceite.
