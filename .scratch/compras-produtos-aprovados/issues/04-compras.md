# 04: Reconhecer identificadores e corrigir vínculos conflitantes

**Status:** concluído localmente em 07/10/2026 — divisão aprovada e implementação autorizada.


**Blocked by:** 03. Requisitos: CMP-01/CMP-02.

Entrega: aproveitar GTIN confirmado ou código de loja quando disponíveis; gerir/corrigir/inativar associações no cadastro sem reclassificar compras anteriores.

Aceite:
- GTIN confirmado pode reconhecer produto em outra loja da própria conta; código de loja permanece local.
- Código interno não vira universal por parecer um EAN. Identificadores contraditórios pedem revisão.
- Mesma marca com branco/ao leite e pacotes 1,01/1,05 kg não recebe associação arbitrária.
- Revisão conflitante retorna 409; edição/inativação deixa alias antigo pendente e preserva histórico.

Evidência: [relatório da implementação](../../../docs/compras/implementacao-2026-10-07.md). Gates e limites de validação documentados; ticket não publicado externamente.
