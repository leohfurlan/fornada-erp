# 05: Consultar compras por material, marca, loja e período

**Status:** concluído localmente em 07/10/2026 — divisão aprovada e implementação autorizada.


**Blocked by:** 02. Requisitos: CMP-03. Não depende de OCR pronto.

Entrega: histórico com filtros, paginação e detalhes, mostrando embalagens, preços originais/normalizados, data e origem; dados desconhecidos continuam identificados. É consulta histórica, não ranking CMP-04.

Aceite:
- Filtros próprios funcionam; dois tenants com nomes iguais continuam isolados.
- Datas desconhecidas ficam visíveis sem filtro e não entram em filtro de período por suposição.
- Snapshot antigo permanece após edição/inativação do produto ou fornecedor.
- Último preço da compra não é apresentado como custo médio nem como oferta atual.
- Consulta utilizável em desktop/390 px, sem exigir marca/fabricante retroativos.

Evidência: [relatório da implementação](../../../docs/compras/implementacao-2026-10-07.md). Gates e limites de validação documentados; ticket não publicado externamente.
