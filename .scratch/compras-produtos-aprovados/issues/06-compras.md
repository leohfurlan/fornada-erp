# 06: Preservar o fluxo de compras do WhatsApp e concluir a integração

**Status:** concluído localmente em 07/10/2026 — divisão aprovada e implementação autorizada.


**Blocked by:** 02 e 03. Requisitos: compatibilidade CMP-02/CMP-03.

Entrega: consumidor existente usa o núcleo da compra/histórico, conserva metadados disponíveis da foto e chave do rascunho; compras legadas continuam válidas. Repetição de evento/CONFIRMAR não duplica entrada.

Aceite:
- Comandos existentes e rascunhos antigos funcionam com campos novos opcionais e histórico incompleto explícito.
- Foto com dados conhecidos conserva loja/data/descrição; não há troca de unidade sem conversão confirmada.
- Revisão/erro/cancelamento não deixam efeito parcial, mock continua rejeitado neste canal.
- Teste usa transporte fake + serviço/banco reais; não enviar mensagem real como efeito da validação local.
- Gates/regressões e cenário integrado web/WhatsApp documentados. Aprovação completa de produtos por conversa permanece futura.

Evidência: [relatório da implementação](../../../docs/compras/implementacao-2026-10-07.md). Gates e limites de validação documentados; ticket não publicado externamente.
