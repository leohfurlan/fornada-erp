# Configurar a Alexa para o Modo cozinha

Este roteiro conecta uma Echo Dot 3 à conta Fornada e à estação aberta no Chrome. A skill permanece em modo de desenvolvimento; não é preciso publicá-la na loja para testar com a conta de desenvolvedor.

## 1. Criar a skill

1. Acesse o [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask) com a conta Amazon usada para testar a Echo.
2. Crie uma skill personalizada em Português (Brasil), com modelo personalizado e hospedagem fora da Amazon.
3. Em **Build → Interaction Model**, importe [alexa-interaction-model.pt-BR.json](alexa-interaction-model.pt-BR.json). O nome de invocação é **cozinha fornada**. Salve e compile o modelo.
4. Em **Build → Endpoint**, escolha HTTPS e configure:

   `https://fornada.atospd.com/api/v1/integrations/alexa/requests`

5. Copie o **Skill ID** apresentado no console. O backend compara esse identificador com o `applicationId` de cada pedido Amazon. Não use o ID do modelo de interação nem o ID da Echo nesse campo.

## 2. Configurar o vínculo seguro da conta

Em **Build → Account Linking**, habilite o vínculo e escolha **Authorization Code Grant**. Configure:

| Campo Amazon | Valor |
|---|---|
| Authorization URI | `https://fornada.atospd.com/api/v1/integrations/alexa/oauth/authorize` |
| Access Token URI | `https://fornada.atospd.com/api/v1/integrations/alexa/oauth/token` |
| Client authentication scheme | HTTP Basic |
| Scopes | `cozinha:read cozinha:control` |

Gere no servidor um `ALEXA_OAUTH_CLIENT_ID` e um `ALEXA_OAUTH_CLIENT_SECRET` próprios para esta skill e informe os mesmos valores na configuração de Account Linking. Use um segredo aleatório com pelo menos 24 caracteres. Copie **todas** as URLs exibidas pela Amazon em **Alexa Redirect URLs**; elas devem ser cadastradas literalmente no servidor, inclusive as de regiões que não serão usadas no primeiro teste.

No ambiente da API, configure:

```dotenv
ALEXA_ENABLED=true
ALEXA_SKILL_APPLICATION_ID=<Skill ID copiado do console>
ALEXA_OAUTH_CLIENT_ID=<mesmo Client ID configurado na Amazon>
ALEXA_OAUTH_CLIENT_SECRET=<mesmo Client Secret configurado na Amazon>
ALEXA_REDIRECT_URIS=["<Redirect URL 1>","<Redirect URL 2>"]
```

O `FRONTEND_URL` precisa apontar para `https://fornada.atospd.com`. Reinicie/deploy a API depois de configurar as variáveis. Com qualquer campo faltando, a integração permanece indisponível; não remova a validação de assinatura Amazon para contornar erros de configuração.

## 3. Vincular e confirmar a Echo

1. No console, deixe o teste da skill habilitado para **Development**.
2. No aplicativo Alexa, entre com a mesma conta Amazon da Echo Dot 3 e habilite a skill de desenvolvimento. Conclua o vínculo usando o usuário e a senha do Fornada.
3. No Mac, abra o Fornada no Chrome, entre em **Modo cozinha** e crie/ative uma estação.
4. Diga **“Alexa, abrir cozinha fornada”** e depois **“buscar receita de brownie”**.
5. Na tela do Fornada, confirme a Echo que acabou de solicitar acesso e selecione a estação. A Alexa só controla a estação depois dessa confirmação.

O backend valida a assinatura e o `applicationId` da skill em cada requisição. Depois do vínculo, associa a conta Alexa autenticada e o `deviceId` da Echo; a primeira Echo aparece como um candidato com horário, sem expor seu identificador Amazon. Essa confirmação impede que outra Echo vinculada à mesma conta Amazon passe a controlar a tela sem ação da confeiteira.

## Diagnóstico rápido

- **A skill não encontra o Fornada:** confira o Endpoint HTTPS e o locale/modelo pt-BR, salve e compile o modelo.
- **A API rejeita o pedido:** confira `ALEXA_SKILL_APPLICATION_ID` contra o Skill ID, a assinatura/HTTPS e o horário do servidor.
- **A tela de vínculo não abre:** confira Client ID, segredo, Authorization URI, HTTP Basic e Redirect URLs exatas.
- **A Alexa pede para confirmar a Echo:** isso é esperado na primeira invocação. Confirme em Modo cozinha dentro do prazo de cinco minutos.
- **A receita não aparece no Chrome:** mantenha a estação ativa e a página visível, e escolha a estação após confirmar a Echo.

As rotas e os requisitos de identificação estão descritos no [contrato](contract.md). O comportamento em dispositivo real ainda depende de aceite com a Echo Dot 3 e o Mac.
