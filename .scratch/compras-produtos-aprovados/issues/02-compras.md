# 02: Registrar compra com embalagem, preço e histórico

**Status:** concluído localmente em 07/10/2026 — divisão aprovada e implementação autorizada.


**Blocked by:** 01. Requisitos: CMP-03.

Entrega: selecionar produto/loja, conferir data/quantidade/valores e confirmar uma compra manual com prévia de conversão, histórico e estoque no mesmo salvamento. Núcleo já inclui idempotência e rollback; não entregar escrita insegura para completar depois.

Aceite:
- 1 barra de 1,01 kg/R$ 35,99 gera 1,01 kg ou 1.010 g, preservando preço original e preço normalizado.
- Duas barras, outra embalagem, descontos e unidade incompatível têm resultados conforme contrato.
- Retry/timeout com mesma chave não duplica; payload diferente retorna 409; erro no último item desfaz tudo.
- Compras distintas concorrentes não perdem saldo/custo; histórico continua após editar produto.
- Material novo não recebe entrada em duplicidade. Data desconhecida não vira data do scan.

Evidência: [relatório da implementação](../../../docs/compras/implementacao-2026-10-07.md). Gates e limites de validação documentados; ticket não publicado externamente.
