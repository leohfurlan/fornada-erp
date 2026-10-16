# Deploy OCR híbrido — 06/10/2026

Publicação autorizada pelo usuário, com commit e PR solicitados. Revisão de implementação instalada: `bae8bfa`. O envio ao repositório público e a abertura do PR dependem da autorização solicitada após bloqueio da revisão automática.

## Configuração efetiva

- `OCR_PROVIDER=hybrid`, `OCR_VISION_PROVIDER=gemma`.
- `GEMMA_OCR_MODEL=gemma-4-26b-a4b-it`.
- `GEMMA_OCR_TEMPERATURE=0.1`, `GEMMA_OCR_THINKING_LEVEL=minimal`.
- Credencial Google presente em backend após a publicação; segredo não copiado para o repositório nem exibido nos logs.

Imagens construídas localmente e transferidas à VPS Oracle, sem build na máquina de 1 GB. Deploy executado com `--mode public-micro --skip-pull --images`, incluindo worker. Fontes chegaram por bundle Git privado via SSH, preservando os ajustes anteriores do script remoto em stash e patch. Nenhuma mudança de configuração ou deploy foi feito na VPS Evolution.

## Backup e verificação

- Ambiente anterior: `/opt/fornada/backups/env-before-ocr-20261006T193924Z`, modo 600.
- Banco: `/opt/fornada/backups/fornada-20261006T194111Z-119960.dump`; restauração verificada em banco temporário antes das migrations.
- Imagens anteriores preservadas com tags `before-ocr-20261006T193924Z`.
- Migrations concluíram; revisão do schema permanece `2798d1537c70`.
- Backend, frontend, proxy, banco, Redis e worker iniciaram. Backend saudável; worker respondeu `pong`.
- HTTPS `/health` e `/login`: 200. Containers de backend, frontend e worker sem OOM.
- Evolution: sessão `fornada` em estado `open`.
- Tesseract real leu um item e total de R$ 11,80 de cupom sintético na VPS sem acionar IA.
- Chamada real ao Gemma 4 com a mesma imagem retornou um item e R$ 11,80. Nenhuma compra foi gravada pelo teste e nenhuma mensagem WhatsApp real foi enviada.

Imagens conferidas na VPS: backend/worker `sha256:78136d9f0037a58af3887b7f095e8f2b2d259c3ed077243e1cbdff51620f58a0`; frontend `sha256:8e320ca65b9ad57c16f46f41b93a95f0cd3287d9862f17b3e4eaa5c51f139abc`.

## Limites

196 testes backend e 34 frontend passaram, além de TypeScript, Ruff e builds. O teste sintético confirma instalação e inferência; não mede precisão em fotos reais. Validar conversa WhatsApp com número controlado e cupons reais de layouts variados. Jev/Decisions API, QR fiscal e documentos XML pelo WhatsApp seguem pendentes. Temperatura baixa não garante respostas idênticas ou correção.
