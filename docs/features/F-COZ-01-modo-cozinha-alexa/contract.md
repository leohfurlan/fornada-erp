# F-COZ-01 — Contrato de cozinha e Alexa

Revisão 3, 16/10/2026. Fatias 01–04 implementadas localmente; aceite presencial e configuração externa continuam pendentes. `ALEXA_ENABLED=false` por padrão e a configuração completa exige HTTPS. Nenhum deploy ou migration foi aplicado. [PRD](../../../prd.md), [spec](spec.md), [plano](plan.md). Base inspecionada: HEAD `44835810044c912413f6dddd11a5c549a69bc791` com working tree existente. Compatibilidade aditiva; não alterar contratos de receitas/Central ou tokens de login atuais.

## Provedores e propriedade

| Provider → consumer | Capacidade e proprietário | Prontidão |
|---|---|---|
| Receitas → serviço Cozinha | Busca/projeção operacional, UUID e versão pertencem ao Fornada | Implementado em `domain/receitas/central_snapshot.py`; novos blocos ainda propostos |
| Auth → browser/consentimento | Ator e tenant via Bearer existente | Implementado em `api/dependencies.py`; rejeitar impersonação nesta feature |
| Cozinha → Chrome | Estado, lease, comando e ACK pertencem ao Fornada | Novo, r1 abaixo |
| OAuth Cozinha → Alexa | Código/token/scope pertencem ao Fornada; vinculação requer consentimento | Novo; não confundir `/auth/refresh` com OAuth |
| Alexa → adapter | Envelope ASK, requestId, applicationId, userId e deviceId pertencem à Amazon | Documentado externamente; configuração e prova real pendentes |

Receita é obtida por busca autenticada; UUID escolhido é revalidado no tenant. Estação é criada pela conta real e selecionada na interface. Identificadores Amazon não são identidade de tenant. Nenhuma rota aceita tenant arbitrário do cliente.

## Tipos e limites propostos

- UUID: identificador opaco; datetimes UTC ISO8601. `revision` inteiro não negativo crescente por estação; `expected_revision` obrigatório em comandos/lease que alteram estado.
- Estação: `id`, `name` (1–80 caracteres após trim), `status` (`active|paused|closed`), `revision`, `recipe_id: UUID|null`, `recipe_version: string|null`, `section: ingredients|preparation|assembly`, `block_index` base zero, `speech_part_index` base zero persistido em `cozinha_estacoes.parte_fala_indice`, `rendered_revision: integer|null`, `last_seen_at: datetime|null`, `notice: string|null`, `projection: Projection|null`.
- Projection: `recipe_id`, `recipe_version` fingerprint, `name`, `yield_quantity` decimal string, `yield_unit`, `ingredients[] {name, quantity: decimal string, unit}`, `blocks[] {id: string estável dentro da versão, section, title, markdown}`, `warnings: string[]`. Partes PlainText são derivadas deterministicamente da projeção no adapter de fala para evitar duplicar texto persistido. Nunca custos, credenciais ou outro tenant.
- Blocos/partes seguem a spec. Cada parte falada tem no máximo 1.500 unidades UTF-16 após escape SSML, com verificação do envelope ASK final contra o limite documentado pelo provider. Sem truncamento silencioso. Se um token isolado exceder limite, não vocalizá-lo; avisar para consultar texto na tela.
- Ingredientes constituem um bloco com partes de fala que preservam itens completos quando couberem. `continue_speech` move somente a parte dentro do bloco e mantém posição no fim; `next`/`previous` movem somente dentro da seção atual e reiniciam a parte em zero. Seção ausente é rejeitada sem trocar estado.
- Busca: 1–200 caracteres, página de até cinco resultados; seleção ordinal 1–5 na página salva, validade 5 minutos. Estado da busca pertence à estação/conta, não apenas sessionAttributes.
- Defaults de transporte: polling 2 segundos em aba visível, heartbeat 10 segundos, lease vencida após 30 segundos sem heartbeat. Lease ID aleatório é retornado só à aba que o possui. Em segundo plano pausar controle; ao voltar renovar/reivindicar explicitamente. Sem promessa de baixa latência em segundo plano.
- Recuperação do browser: lease permanece apenas na aba controladora; refresh/reabertura exige nova aquisição explícita, com revisão lida do servidor. Aba oculta, offline, heartbeat falho ou erro de estado pausam comandos e exibem que a receita pode estar desatualizada. Ao retomar visibilidade, o heartbeat é tentado imediatamente. Respostas de polling antigas não podem substituir uma revisão mais nova no cache.
- Estado e seleção sobrevivem a sessão Alexa. Recibos de idempotência por 24 horas; request Alexa com timestamp >150 segundos de diferença absoluta é rejeitado antes da deduplicação. Código OAuth 5 minutos e uso único; access token 15 minutos; refresh token 7 dias. Defaults ajustáveis via settings e testes, sem segredos em logs.

## API do browser

Prefixo `/api/v1/cozinha`. Todas as rotas exigem Bearer atual, ator real ativo e tenant correspondente. Impersonação rejeitada com 403. Resposta sem cache compartilhado (`Cache-Control: no-store`).

| Método/path | Entrada | Saída |
|---|---|---|
| POST `/stations` | `{name}` | 201 `{station: Station}` inicialmente paused, sem receita |
| GET `/stations` | Sem paginação no piloto; somente esta conta | 200 `{items: [{id, name, status, revision}]}` sem projeções ou leases |
| GET `/stations/{id}` | `lease_id: UUID` e `after_revision?: integer` | 200 `{changed: boolean, station: Station|null}`; unchanged pode omitir projeção/retornar station null. Não renova heartbeat |
| POST `/stations/{id}/lease` | `{expected_revision, takeover: boolean}` | 200 `{lease_id, expires_at, station}`; takeover explícito invalida lease anterior, ativa estação e incrementa revisão |
| POST `/stations/{id}/heartbeat` | `{lease_id}` | 200 `{expires_at}`; só renova lease ativa da conta, não muda revisão |
| POST `/stations/{id}/commands` | `{command_id, expected_revision, type, payload, lease_id}` (`Command` abaixo) | 200 `Receipt`; 409 conflito de revisão/lease |
| POST `/stations/{id}/ack` | `{lease_id, revision}` | 200 `{rendered_revision}` monotônica; ACK só após conteúdo renderizado e revisão previamente entregue a essa lease; não marca revisões futuras |
| POST `/stations/{id}/close` | `{lease_id}` | 204; status paused, incrementa revisão e invalida lease |
| GET `/alexa/link` | Sem parâmetros | 200 `{linked, station_id: UUID|null, pending_devices: [{id: UUID, first_seen_at: datetime}], approved_device_id: UUID|null}` sem IDs/token Amazon |
| PUT `/alexa/link/station` | `{station_id}` | 200 `{station_id}`; exige vínculo consentido e estação da mesma conta; troca limpa seleção pendente |
| PUT `/alexa/link/device` | `{pending_device_id: UUID}` | 200 `{approved_device_id: UUID}`; confirma candidato recebido em request Amazon validado e token desta conta; substitui dispositivo anterior |
| DELETE `/alexa/link` | Sem body | 204; revoga credenciais/associação e impede comandos seguintes |

`StationSummary` contém somente id/name/status. Estação é exclusiva do usuário e tenant no MVP, inclusive quando há outros usuários no mesmo tenant. Retomada exige nova lease se expirada; fechar não apaga cadastro de receita. Logout limpa cache UI e tenta close; se falhar, lease expira e UI não segue renovando. Trocar conta nunca reutiliza cache da estação anterior.

GET de estado revalida acesso à receita/versão mesmo quando `after_revision` coincide; se receita mudou, suspende projeção e devolve `RECIPE_CHANGED`, sem texto antigo; reload explícito substitui snapshot. Receita apagada/inacessível limpa recipe/projection, incrementa revisão e devolve estado vazio com aviso. Leitura de voz usa a mesma revalidação; nenhuma projeção é devolvida antes da checagem.

O backend só atende a integração Alexa quando `ALEXA_ENABLED=true`, IDs da skill e cliente OAuth estão presentes, o segredo tem ao menos 24 caracteres e os redirects e `FRONTEND_URL` usam HTTPS. O flag fica desligado por padrão e é o kill switch operacional; contas vinculadas continuam sujeitas a consentimento e revogação individuais.

`Command = {command_id: UUID, expected_revision: integer, type, payload, lease_id}`. Tipos/payloads exatos:

| type | payload |
|---|---|
| `search_recipe` | `{query: string, offset: integer >=0}` |
| `select_recipe` | `{selection_id: UUID, ordinal: integer 1..5}` |
| `open_recipe` | `{recipe_id: UUID}` somente browser (ID recebido da busca) |
| `show_section` | `{section: ingredients|preparation|assembly}` |
| `next`, `previous`, `repeat`, `continue_speech`, `cancel_selection`, `resume` | `{}` |
| `reload_recipe` | `{}` somente browser, após revisão explícita |

Campos desconhecidos rejeitados. `search_recipe` cria seleção paginada e cancela anterior; offset >0 requer busca/termo atual ainda válidos. Um resultado na busca inicial abre; páginas seguintes sempre exigem seleção. Uma busca com vários resultados não muda a receita exibida. `repeat`/`resume` sem movimento retornam estado atual. Nenhum comando altera dados de negócio. Tela respeita revisão atual ao aplicar retorno concorrente de polling/comando.

`Receipt = {command_id: UUID, revision: integer, status: accepted|rendered|selection_required|no_results|no_change, station_id: UUID, selection: Selection|null, speech_parts: string[], error: null}`.

`Selection = {id: UUID, expires_at: datetime, query: string, offset: integer, items: [{ordinal, recipe_id, name}], next_offset: integer|null}`. Pode ser incluída no estado de GET quando ativa, sob as mesmas permissões. Não aceitar recipe_id de fora da página via select. `rendered` só significa revisão confirmada por ACK; accepted não equivale a exibido.

Erros novos HTTP: `{detail: string pt-BR, code: string, current_revision?: integer}`. 401 `AUTH_REQUIRED`; 403 `FORBIDDEN`/`IMPERSONATION_FORBIDDEN`; 404 `NOT_FOUND` também para recurso alheio; 409 `REVISION_CONFLICT`, `STATION_IN_USE`, `STATION_OFFLINE`, `RECIPE_CHANGED`; 410 `SELECTION_EXPIRED`; 422 `INVALID_COMMAND`, `INVALID_RECIPE`, `SECTION_UNAVAILABLE`, `NO_RECIPE`; 429 `RATE_LIMITED`. Sem stack/receita alheia em detail. Errors 401/429 já produzidos por infraestrutura podem manter shape global existente, consumido pelo adapter. Limites específicos: proposta 60 comandos/minuto por conta e rate limit de consentimento/token; fixar política por testes antes de expor endpoint.

CAS: mutações de estado incrementam revisão atomicamente; ações sem alteração não incrementam. `expected_revision` divergente devolve conflito e não reexecuta automaticamente next/previous. Lookup de idempotência só após validar conta/acesso. Chave única `(tenant_id, user_id, station_id, command_id)` no browser; mesmo ID com payload diferente →409 `IDEMPOTENCY_CONFLICT`. Resposta duplicada mantém revisão/recibo originais e nunca devolve dados atualmente proibidos. Estado+recibo persistidos na mesma transação.

## Alexa ASK e account linking

POST `/api/v1/integrations/alexa/requests`: envelope ASK oficial, não `Command` público. Exige assinatura/cadeia/certificado Amazon válidos, timestamp dentro da janela e applicationId exatamente configurado. Assinatura/origem inválida →400 sem consultar receita. Verificação não pode ser desativada em produção. Certificado só pode ser obtido de origem Amazon validada; proteger fetch contra SSRF.

Após origem validada, `context.System.user.accessToken` deve resolver vínculo OAuth ativo e conta/tenant ativos. `deviceId` é associado à estação durante ativação explícita do piloto; dispositivo diferente não pode controlar a estação sem confirmação na interface. Usuário Alexa sem vínculo recebe resposta ASK 200 com `LinkAccount` e orientação; token revogado não reaproveita recibos. Erros de negócio após validação são resposta ASK 200 falada e sem mutação. Não deixar `SessionEndedRequest` devolver fala/continuar sessão.

Primeira invocação assinada com token válido registra candidato de dispositivo opaco, visível na interface por horário. Alexa orienta confirmar dispositivo no modo cozinha; antes dessa confirmação não busca/fala receitas. UI confirma candidato de sua conta via `/alexa/link/device`. Candidato expira em 5 minutos; só um dispositivo aprovado por vínculo no piloto. Não aceitar ID Amazon fornecido pelo browser como prova de identidade.

Mapa de intents proposto pt-BR:

| Intent | Slots → ação |
|---|---|
| LaunchRequest / `ResumeKitchenIntent` | Retomar; se sem estação/receita orientar configuração/busca |
| `SearchRecipeIntent` | `recipe_name` → search_recipe; pedir slot se ausente |
| `SelectRecipeIntent` | `ordinal` → seleção salva |
| `MoreRecipesIntent` | próxima página da seleção |
| `ShowIngredientsIntent` | selecionar ingredientes e falar a primeira parte |
| `ShowPreparationIntent`, `ShowAssemblyIntent` | selecionar seção e falar a primeira parte do primeiro bloco |
| `NextStepIntent`, `PreviousStepIntent` | mover bloco dentro da seção atual e falar a primeira parte |
| `RepeatContentIntent`, `ContinueReadingIntent` | repetir a parte atual sem mover; continuar move somente parte falada |
| `ShowIngredientsIntent` | show_section ingredients e primeira parte de leitura |
| `ShowPreparationIntent`, `ShowAssemblyIntent` | seção correspondente, primeiro bloco/parte |
| `NextStepIntent`, `PreviousStepIntent` | next/previous; mover bloco e ler primeira parte |
| `RepeatContentIntent`, `ContinueReadingIntent` | repeat/continue_speech; sem avançar bloco ao repetir |
| `AMAZON.HelpIntent` | Exemplos disponíveis, sem mudar estado |
| `AMAZON.StopIntent` | Encerrar sessão Alexa, manter estação |
| `AMAZON.CancelIntent` | Cancelar seleção e encerrar sessão, manter receita |
| SessionEndedRequest | Registrar encerramento sem destruir estado ou enviar outputSpeech |

Frases são propostas, a confirmar no console/Echo: “Alexa, abrir cozinha fornada”; “buscar receita de brownie”; “ler ingredientes”; “mostrar preparo”; “próxima etapa”; “voltar etapa”; “repetir”; “continuar leitura”. O nome de invocação está definido no modelo pt-BR; o aceite de voz depende do console Amazon e do teste na Echo. Consulte [configurar-alexa.md](configurar-alexa.md) para rotas, Skill ID, OAuth e confirmação da Echo.

O adapter lê revisão atual e executa sob lock; não usa sessionAttributes como revisão autoritativa. Idempotência Alexa por `(applicationId, userId, requestId)` associado à conta e comando; persistir hash do payload para rejeitar reutilização divergente. Comandos concorrentes Alexa são serializados por estação; duplicatas retornam recibo. Concorrência com browser respeita transação/CAS. Fala pode afirmar “receita enviada”; só usa “na tela” se a revisão retornada tiver ACK. Não esperar polling dentro da transação/webhook.

OAuth proposto (isolado do JWT do ERP):

| Interface | Regras |
|---|---|
| GET `/api/v1/integrations/alexa/oauth/authorize` | `response_type=code`, `client_id`, `redirect_uri` exatamente allowlisted, `state` obrigatório, `scope` conjunto cozinha:read/cozinha:control; aceitar PKCE S256 quando configurado. Redirecionar para UI `/integracoes/alexa/autorizar` com contexto opaco; não autorizar apenas por GET |
| POST `/api/v1/integrations/alexa/oauth/consent` | Bearer real + contexto opaco de uso único + decisão aprovar/recusar; validar origem/CSRF e identidade. Retorna redirect URL validada contendo code e state originais, ou error access_denied. Nunca colocar JWT ERP nessa URL |
| POST `/api/v1/integrations/alexa/oauth/token` | Form-urlencoded, client HTTP Basic configurado; authorization_code com code+redirect_uri e code_verifier se PKCE, ou refresh_token. Valida cliente, binding, expiração e uso único. Retorna access_token, token_type Bearer, expires_in, refresh_token e scope; no-store. Erros OAuth `{error, error_description}` com 400; cliente inválido 401 |

Tokens opacos gerados criptograficamente, hashes persistidos; segredos fora do código. Refresh rotaciona atomicamente e reuso revoga a família; acesso negado depois de revogação. Códigos vinculados ao client/redirect/usuário/tenant e PKCE quando solicitado. Não confiar em userId Alexa sozinho. Conta vinculada pode consultar suas receitas por voz; não é autenticação biométrica de quem fala próximo à Echo.

## Compatibilidade e conformance

Revisão r2 mantém compatibilidade aditiva. Consumidores novos versionam schemas coordenadamente antes da primeira integração; mudança posterior de semântica/blocos exige revisar fingerprint e invalidar navegação antiga. A migration `c7e5f2a901bd` adiciona o cursor falado à estação; migrations aditivas e feature flag preservam os dados de receitas.

Fixtures: receitas sintéticas com ingredientes/unidades, Markdown, composição e tenants distintos; envelopes conforme documentação ASK com assinatura verificável em teste. Mock de assinatura só em teste unitário de adapter; integração deve cobrir verificador real com cadeia/tempo controlados. Testar provider de projeção e consumer de tela/fala contra os mesmos exemplos, mais busca real→seleção→estado→ACK. Prova final: account linking real + Echo Dot 3 + Chrome do Mac; mocks/simulador não provam prontidão externa.
