# Plano CMP-02

r2, 07/10/2026. Fonte [PRD r2](../../compras-produtos-aprovados.md); [spec](spec.md); [contrato](contract.md). Depende de CMP-01 e CMP-03, sem exigir que OCR preceda a compra manual.

1. Demonstrar leitura com campos originais/data/loja, seleção de produto/material e prévia de conversão. Checkpoint: cupom de cobertura sem variante não seleciona branco só pela marca; escolha explícita permite entrada correta por CMP-03.
2. Integrar aprovação na hora, exceção e aprendizado transacional. Checkpoint: cancelar/ignorar não persiste; segunda leitura da mesma loja reconhece produto já confirmado.
3. Entregar identificação por código/GTIN confirmado, gestão de vínculos e resolução de conflitos. Checkpoint: outra loja, variante e embalagem diferente não recebem vínculo indevido; edição concorrente preserva revisão.
4. Validar contrato do adapter e consumidores v1/WhatsApp, UI desktop/390 px e [gates](../qualidade.md). Completar QA-01→QA-02 com PostgreSQL real e fixture OCR do contrato.

Definição de concluído: C2-B1 a B8/C2-E1 a E16 atendidos; prévia não converte por troca de rótulo; decisão da usuária preservada no histórico CMP-03; provider comercial real integrado. Nunca habilitar reconhecimento como entrega completa sem compra/histórico e revisão. Relatório CMP-04 e aprovação completa por conversa não integram esta feature.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
