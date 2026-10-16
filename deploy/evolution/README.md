# Evolution API — VPS dedicada atos-pd

## Instalação atual — 06/10/2026

Instalada em `ssh atos-pd`, IP `191.252.159.77`, Ubuntu 24.04 amd64, 6 vCPUs e 8 GB de RAM. Diretório `/opt/evolution-fornada`, projeto `fornada-evolution`. O registro A de `evolution.atospd.com` foi atualizado pelo painel Cloudflare, mantendo Somente DNS. Painel: https://evolution.atospd.com/manager/.

A stack usa `compose.yml` junto de `dedicated.yml` e Caddy próprio (`Caddyfile`). PostgreSQL e Redis não publicam portas; a API publica 8081 somente em loopback. Limites de memória: API 2 GB (heap Node 1536 MB), PostgreSQL 256 MB, Redis 128 MB e proxy 128 MB. Segredos novos foram gerados na VPS, em `.env` com modo 600. Não foram transferidos segredos da instalação anterior.

Comandos nesta VPS:

```sh
cd /opt/evolution-fornada
python3 configure.py env --url https://evolution.atospd.com
docker compose -f compose.yml -f dedicated.yml config --quiet
docker compose -f compose.yml -f dedicated.yml pull
python3 configure.py pin
docker compose -f compose.yml -f dedicated.yml up -d postgres redis api
python3 configure.py instance
docker compose -f compose.yml -f dedicated.yml up -d proxy
python3 configure.py status
docker compose -f compose.yml -f dedicated.yml ps
```

Verificação realizada: migrations concluídas; API/PostgreSQL/Redis saudáveis e sem OOM; HTTPS com certificado validado, raiz 200, painel de login aberto no navegador, API sem chave 401 e criação/consulta autenticadas funcionando. Consumo inicial dos quatro containers aproximadamente 173 MiB, sem swap usada. A imagem Evolution está fixada no digest descrito abaixo.

A instância `fornada` foi pareada pelo operador e está em estado `open`. O webhook autenticado está ativo para `MESSAGES_UPSERT` na Fornada, com backend saudável e worker online. A chave global do painel está em `AUTHENTICATION_API_KEY` no `.env` remoto; o token da instância e o segredo de webhook são separados. Cadastro e compras manuais estão habilitados; OCR aguarda chave Google AI Studio. Validações e pendências estão em `docs/evolution-whatsapp.md`.

Os scripts `publish.py` e `public-network.yml` abaixo são exclusivos da antiga instalação Oracle com proxy compartilhado: não executar na VPS atos-pd. A instalação antiga permanece parada, com volumes preservados. A Fornada não foi reiniciada nesta instalação.

## Histórico — piloto na Oracle

Instalação separada da aplicação em `/opt/evolution-fornada`, projeto Compose `fornada-evolution`, com PostgreSQL, Redis e volume de sessões próprios. Imagem estável `evoapicloud/evolution-api:v2.3.7`, fixada antes de uso. Não utiliza banco ou cache da Fornada. A instalação exige Docker/Compose já disponíveis e gera segredos apenas na VPS, em `.env` com permissão 600.

Fontes: [release estável](https://github.com/evolution-foundation/evolution-api/releases/tag/2.3.7), [variáveis da versão](https://github.com/evolution-foundation/evolution-api/blob/2.3.7/.env.example), [instalação Docker oficial](https://github.com/evolution-foundation/docs-evolution/blob/main/v2/en/install/docker.mdx).

## Instalar

Transfira `compose.yml` e `configure.py` para o diretório. No servidor:

```sh
cd /opt/evolution-fornada
python3 configure.py env
sudo docker compose -f compose.yml config --quiet
sudo docker compose -f compose.yml pull
python3 configure.py pin
sudo docker compose -f compose.yml up -d
sudo docker compose -f compose.yml ps
python3 configure.py instance
python3 configure.py status
```

A API começa disponível apenas em `127.0.0.1:8081`, sem abrir portas externas novas. Para acesso privado no PowerShell:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8081:127.0.0.1:8081 fornada
```

Abra `http://localhost:8081/manager`. A API key de administração está em `AUTHENTICATION_API_KEY` no `.env` remoto; nunca versionar ou copiar esse arquivo indiscriminadamente. `configure.py` não imprime chaves nem respostas com tokens. Instância `fornada` é criada com token separado, grupos ignorados, histórico completo desligado, mensagens/status sem leitura automática e webhook inicialmente desligado.

## Publicação HTTPS

Depois de confirmar o subdomínio e seu DNS:

1. Atualize `SERVER_URL` no `.env` da Evolution para a URL HTTPS exata. CORS usa `*`, sem cookies/credentials: esta versão rejeita requests sem `Origin` quando a lista é restrita, inclusive requests server-to-server. A autenticação continua obrigatória por `apikey`.
2. Transfira `public-network.yml` e aplique os dois arquivos Compose. Somente a API passa a participar da rede do proxy; PostgreSQL e Redis continuam na rede privada da Evolution.
3. Preserve o Caddyfile existente e acrescente um bloco para o hostname confirmado, com `reverse_proxy evolution-api:8080`. Valide a configuração antes de recarregar o Caddy, sem recriar a aplicação.
4. Verifique certificado válido, `/manager`, API sem credencial recusada e API autenticada acessível. O limite de tamanho da requisição e headers devem atender ao envio de fotos.

Para esta VPS e este proxy, `python3 publish.py evolution.atospd.com` automatiza essas etapas: valida DNS, atualiza somente o `.env` da Evolution, liga a API à rede do proxy, espera readiness, salva backup do Caddyfile, valida a candidata e recarrega Caddy. Se o reload falhar, restaura a configuração anterior. Não reinicia backend/frontend/banco da Fornada. Preserve o bloco Evolution no Caddyfile ao atualizar os fontes da aplicação; a alteração remota precisa ser conciliada antes de um deploy que exija working tree limpo.

Não exponha PostgreSQL/Redis, não abra a porta 8081 e não use uma imagem `latest`. A versão 2.4 estava em pré-release na consulta de 06/10/2026 e introduz ativação; não foi escolhida para este piloto.

## Operação

VPS inspecionada: Ubuntu 26.04, amd64, 951 MiB de RAM, swap de 2 GiB. A aplicação existente usa a mesma VPS. Limites da Evolution: API 384 MiB (heap Node 256 MiB), PostgreSQL 96 MiB, Redis 48 MiB. São limites de piloto e exigem monitoramento após conectar o WhatsApp e executar OCR. CPU total dos três containers limitada a 0,85 CPU. Não prometem capacidade de produção para múltiplas instâncias.

O cadastro da instância não pareia um telefone. O operador precisa escanear o QR no WhatsApp escolhido. Só então validar recebimento/envio com um número de teste autorizado. A integração no `.env.production` da Fornada é uma etapa posterior: URL HTTPS, token da instância, nome `fornada`, segredo do webhook, worker ativo e webhook `MESSAGES_UPSERT` autenticado. O segredo do webhook é diferente da API key de administração.

Volumes persistem entre reinicializações. Antes de atualizar a imagem, faça backup do banco e das sessões em diretório restrito, e guarde cópia externa. Não executar `down -v`. Banco da Evolution contém metadados/mensagens: definir rotina de retenção antes de uso amplo.

## Situação em 06/10/2026 — aguardando VM dedicada

O usuário decidiu criar uma segunda VM gratuita e pediu para aguardar a publicação. Os três containers Evolution foram parados; volumes e segredos estão preservados em `/opt/evolution-fornada`. DNS de `evolution.atospd.com` ainda aponta à VM atual, `163.176.96.250`. Não foi modificado o Caddy nem publicada a Evolution. Nenhum WhatsApp foi pareado e nenhuma mensagem real foi enviada.

A imagem foi baixada e fixada como `evoapicloud/evolution-api@sha256:1bd8afc4a6cf48822e6cf02469aeae7bd35a12a6b616eacd1291926307f4d339`. Migrations e geração do Prisma concluíram. A primeira verificação HTTP revelou a rejeição CORS a requests sem `Origin`; a configuração foi corrigida para `CORS_ORIGIN=*` e `CORS_CREDENTIALS=false`. Como os containers foram parados a pedido de aguardar a nova VM, a configuração corrigida ainda precisa ser validada em runtime ao retomar.

O deploy simultâneo da Fornada foi identificado por processo: `deploy/deploy.sh --mode public-micro --skip-pull --images /opt/fornada/fornada-images-catalogo.tar`. A parada temporária do proxy/frontend/backend ocorreu nessa operação, com proxy sem OOM; esta instalação não os reiniciou. Na última inspeção, os serviços da aplicação estavam novamente ativos, backend saudável.

Próxima etapa: receber IP/alias SSH, usuário e shape/RAM da nova VM, confirmar arquitetura e acesso, instalar a stack isolada e publicar `evolution.atospd.com` na nova VM após ajustar DNS. Os scripts `publish.py`/`public-network.yml` desta pasta atendem especificamente ao proxy compartilhado da VM atual; para VM dedicada, preparar Caddy próprio antes de publicar. Não reutilizar o endereço antigo por suposição.
