# Publicação da integração — 09/10/2026

Publicação autorizada pelo proprietário: “Faça commit e deploy na vps”. Os dois backends foram atualizados. Os conectores comerciais continuam desativados até configuração dos vínculos e homologação. Nenhuma compra de produção foi criada para validar o deploy.

## Commits

- Fornada `817ec51`: registra as dependências de backend iFood que já estavam publicadas, necessárias para a integração e a união das migrations.
- Fornada `1c92f27`: API da central, aprovação identificada, revisão humana, idempotência, migrations e evidências de testes.
- whatsapp-admin `23d901c`: classificação dos erros HTTP e correção da elegibilidade da primeira mensagem após atraso no consumo da inbox.

Alterações locais de outras frentes foram preservadas. Não houve push. As releases foram transferidas diretamente, com verificação de integridade.

## Fornada — Oracle

- Anterior: `/opt/fornada/releases/ifood-alertas-20261007-01`.
- Atual: `/opt/fornada/releases/central-20261009-02`.
- Backend, Celery e monitor: `fornada-backend:central-20261009-02`.
- Imagem: `sha256:baed2ab0ea7802cc688c764b0a5400af0ec9948d6276c4e7893019b8f7260900`.
- Frontend preservado: `fornada-frontend:ifood-alertas-20261007-01`.
- Migration aplicada: `f3197cd42901` → `a85c10b7d302`.
- Backup: `/opt/fornada/backups/central-20261009T221151Z-1419601.dump`.

A release foi construída a partir dos fontes copiados da produção, preservando o OCR híbrido, fábrica de extração, administração e iFood. Não é uma substituição integral pelos fontes do checkout local mais antigo. O manifesto dos fontes está em `source-manifest.json` dentro da release. O arquivo-base sem segredos tem SHA-256 `63f986ccf0600a6ea7c45102e34c2b171a4df12818034e6cf85041e76bb94eb1`.

Pacote de fontes: SHA-256 `bf434c307b91e634121025af44765f1281a86fa4c7c29af5dfff68da7cc0c0c4`. Arquivo de imagem: `5a9fb18bcf8a5db928c6319ca622256df054a65ecce1c8d4c7a913d86ca26ddb`. Os hashes locais e remotos coincidiram.

O backup foi restaurado em banco temporário e a migration candidata foi aplicada nessa cópia antes do banco real. O banco temporário foi removido. API saudável, `/health` e `/login` com HTTP 200. OCR configurado como `hybrid`; monitor e alertas iFood continuam habilitados; Celery voltou a consumir `ifood.notify` com sucesso. Frontend, proxy, banco e Redis foram preservados.

## Central — KingHost

- Anterior: `/opt/talk2me/releases/20261009-layout-ed4c4d6`.
- Atual: `/opt/talk2me/releases/central-integration-20261009`; `/opt/talk2me/current` aponta para esta release.
- API, messaging, agents e operations: `talk2me-backend:central-integration-20261009`.
- Imagem: `sha256:194115f7debe7b49b8b0800c07de8024159f254337a3312890ac6127d05e0f70`.
- Frontend preservado: `talk2me-web:20261009-layout-ed4c4d6`.
- Schema preservado: `0012_purchases`; não houve migration da central.
- Backup: `/opt/talk2me/backups/central-integration-20261009T221143Z.dump`.

A imagem deriva do backend publicado, acrescentando somente `fornada_adapter.py` e `messaging.py`. Configuração compartilhada, chave de criptografia, credenciais, conexão Moriah e dados existentes foram preservados. Backup restaurado em banco temporário e removido após validação. API saudável; HTTPS público com HTTP 200; `/api/auth/me` sem sessão com HTTP 401.

## Validação e estado operacional

- Release Fornada baseada em produção: **344 testes aprovados, 4 ignorados**, usando PostgreSQL descartável local e migrations reais.
- Ensaio HTTP repetido com a release candidata: **19 verificações aprovadas**. Revisão humana, revogação, concorrência, tomada humana, resposta perdida após commit e reconciliação sem segundo execute. Evidência: `central-whatsapp-deploy-http-evidencia-2026-10-09.json`.
- Imagem Linux/amd64: importação da API e fábrica de OCR, head única e idioma Tesseract `por` conferidos.
- Chamada HTTPS do container da central para `/api/v1/central/resolve` da Fornada retornou HTTP 404, conforme a integração desativada. Durante a inicialização houve HTTP 502 transitório; o teste após inicialização passou.
- Fornada: `CENTRAL_ENABLED=false`. Central: `fornada_connectors` vazio. Publicar o código não ativou lançamentos comerciais via WhatsApp.

Para ativar o piloto faltam vínculo explícito negócio → tenant, identificação da usuária/telefone, segredo dedicado nos dois serviços e homologação do transporte Evolution/Baileys. Manter revisão humana. Agenda, pedidos e produção continuam fora deste escopo.

## Recuperação

As releases, imagens e backups anteriores permanecem disponíveis. Os scripts desta publicação contêm verificação das imagens de partida, bloqueio de deploy concorrente e retomada da release anterior em falha. Não devem ser repetidos sem adaptar os pré-requisitos para o estado corrente.

Para rollback de aplicação, usar os arquivos Compose e imagens da release anterior, preservando o banco e os volumes. A migration é aditiva; não executar downgrade destrutivo automaticamente. Uma restauração de dados exige avaliar as operações posteriores ao backup.
