# Plano CMP-03

r2, 07/10/2026. Fonte [PRD r2](../../compras-produtos-aprovados.md); [spec](spec.md); [contrato](contract.md). Provider CMP-01 precisa existir para integração; núcleo comercial implementado e integrado.

1. Entregar compra manual demonstrável escolhendo produto/loja reais, com prévia de conversão, confirmação v2 e consulta histórica. Dependência: catálogo CMP-01. Checkpoint: 1 barra 1,01 kg/R$ 35,99 aparece no estoque e histórico exatamente uma vez.
2. Completar transação, revisão, protocolo idempotente, precisão e bloqueios de saldo. Checkpoint: duas conexões, replay após timeout, corpo alterado, dois itens com erro no último e compras distintas concorrentes. Preparar o núcleo para instruções de aprendizado de CMP-02 sem exigir OCR.
3. Integrar histórico consultável com filtros e snapshots e adaptar consumidores v1/WhatsApp. Checkpoint: fabricante/data ausentes, compra excepcional, edição comercial posterior e evento WhatsApp repetido. Rascunhos novos preservam metadados conhecidos; antigos mantêm compatibilidade.
4. Validar migration aditiva e todos os cenários C3-B/C3-E com os [gates](../qualidade.md). Integração final inclui CMP-02 e não só entrada manual.

Definição de concluído: histórico e estoque inseparáveis, protocolo v2 testado, compatibilidade legada comprovada, nenhuma perda de quantidade/total e isolamento. Desativação de UI mantém dados; downgrade destrutivo não é plano de recuperação. Deploy e migration de produção não fazem parte da implementação local.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
