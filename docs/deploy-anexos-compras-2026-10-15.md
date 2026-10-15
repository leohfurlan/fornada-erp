# Deploy de anexos de compras — 15/10/2026

Publicado após autorização explícita do usuário para deploy.

- Release: `/opt/fornada/releases/receipt-20261015`, estado `COMPLETE`.
- Backend, Celery e iFood: `fornada-backend:receipt-20261015`.
- Frontend: `fornada-frontend:receipt-20261015`.
- Base anterior: `decimals-2311d3c`; imagens e cadeia Compose anteriores preservadas para reversão.
- Backup conferido por `pg_restore --list`: `/opt/fornada/backups/receipt-20261015T120915Z.dump`.
- Sem migração ou edição de dados de clientes. Sem commit/push nesta publicação.

O seletor de imagens/PDF não força captura de câmera; fotografar usa um controle separado. O endpoint aceita PDF de até 8 MB e converte todas as páginas, com limite de cinco, para imagem antes do OCR. Dependência `pypdfium2==4.30.0` instalada na imagem backend.

A release foi composta sobre a produção, preservando o factory de OCR híbrido que difere do checkout local. O frontend foi reconstruído dos fontes da publicação PWA com as alterações commitadas até `2311d3c` e apenas a correção do componente de compras. Outras alterações locais não foram publicadas. Compose efetivo anterior foi obtido dos labels dos containers e acrescido de `compose.receipt.yml`; manifesto e procedimento estão na pasta da release.

Validação: nove testes frontend e três testes de PDF locais passaram; TypeScript, lint Python e build Linux aprovados. Na imagem de produção, o endpoint real recebeu PDF sintético e entregou PNG ao serviço de leitura simulado (`PDF_ENDPOINT_OK`); arquivo inválido foi rejeitado. Factory de OCR e rota confirmados (`OCR_ROUTE_OK`). A imagem não contém pytest, portanto o preflight remoto usou script independente. Nenhuma chamada real de IA ou movimentação de estoque foi feita por esses testes.

Após a troca: backend saudável, Celery/iFood/frontend ativos, HTTPS `/health` retornou `{"status":"ok","version":"0.1.0"}` e login acessível. Bundle público de `/compras` confirmado com o seletor `image/*,application/pdf,.pdf`, texto “Escolher imagem ou PDF” e captura separada. Houve 502 transitório durante a recriação dos serviços; verificação final aprovada.

Pendente apenas o aceite no aparelho Android: atualizar/reabrir a aplicação e escolher foto da galeria ou PDF. Abertura nativa da galeria não foi verificada em aparelho físico nesta publicação.
