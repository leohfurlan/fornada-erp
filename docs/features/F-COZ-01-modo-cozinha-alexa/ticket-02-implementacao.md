# Ticket 02 — Vínculo Alexa e abertura por voz

Implementação local do vínculo de conta e do comando de busca/abertura por voz. O fluxo usa uma skill customizada pt-BR, OAuth authorization-code e o endpoint HTTPS do Fornada.

## Rotas

- `GET /api/v1/integrations/alexa/oauth/authorize`: valida cliente, redirect URI exata, escopos e PKCE S256 quando enviado; cria contexto curto e redireciona para consentimento autenticado.
- `POST /api/v1/integrations/alexa/oauth/consent`: exige Bearer da conta real e origem do frontend; aprova ou nega uma vez e devolve code/state à redirect URI allowlisted.
- `POST /api/v1/integrations/alexa/oauth/token`: Basic client authentication; troca code ou rotaciona refresh token. Os valores persistidos são hashes.
- `POST /api/v1/integrations/alexa/requests`: valida timestamp (150 s), assinatura/certificado com ASK SDK, application ID e access token antes de acessar receita. Busca única abre; resultados múltiplos ficam salvos cinco minutos para seleção; duplicatas devolvem o mesmo recibo.
- `GET /api/v1/cozinha/alexa/link`, `PUT /link/device`, `PUT /link/station`, `DELETE /link`: confirmam a Echo candidata, escolhem a estação e revogam o vínculo. O identificador da Echo nunca é devolvido ao browser.

A busca por voz só altera a projeção da estação, sem gravar alteração no cadastro da receita. A fala informa “enviada para a estação” e evita confirmar exibição sem ACK da tela. A primeira solicitação válida cria uma Echo candidata que expira em cinco minutos; ela precisa ser aprovada na tela antes de controlar a estação.

## Configuração externa pendente

As variáveis `ALEXA_SKILL_APPLICATION_ID`, `ALEXA_OAUTH_CLIENT_ID`, `ALEXA_OAUTH_CLIENT_SECRET` e `ALEXA_REDIRECT_URIS` ficam em branco no exemplo. Sem todas elas, as rotas de integração retornam indisponível. O segredo OAuth precisa ser aleatório e guardado no ambiente secreto do servidor. `ALEXA_REDIRECT_URIS` deve ser um array JSON com as URIs copiadas exatamente do console de desenvolvimento da Alexa.

No console da Alexa, criar uma Custom Skill em pt-BR, importar [alexa-interaction-model.pt-BR.json](alexa-interaction-model.pt-BR.json), apontar o endpoint de desenvolvimento para `https://<host>/api/v1/integrations/alexa/requests` e configurar Account Linking como Authorization Code Grant, incluindo as URLs `/api/v1/integrations/alexa/oauth/authorize` e `/api/v1/integrations/alexa/oauth/token`. Copiar o Client ID, Client Secret e as redirect URIs geradas pela Alexa para a configuração acima. As URLs devem usar HTTPS público. Não ativar ou publicar a skill até provar o vínculo real e o fluxo Echo → Fornada → Chrome.

## Validação ainda necessária

O código e a migration foram preparados, mas esta máquina não alcança PyPI pelo terminal, então a nova dependência ainda não está instalada no ambiente local. Também não há Application ID, credenciais OAuth, redirect URIs, endpoint público HTTPS nem acesso à conta Alexa da família. Portanto, o simulador pode ser configurado depois da instalação do lock, mas a prova real com Echo Dot 3 continua pendente; nenhum deploy, migration em banco real ou publicação foi feito.
