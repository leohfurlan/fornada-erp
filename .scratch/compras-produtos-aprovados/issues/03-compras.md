# 03: Conferir cupom e guardar a associação para a próxima compra

**Status:** concluído localmente em 07/10/2026 — divisão aprovada e implementação autorizada.


**Blocked by:** 01 e 02. Requisitos: CMP-02 e integração CMP-03.

Entrega: fotografar cupom, selecionar material existente/produto na primeira compra, aprovar produto/loja na hora ou registrar exceção e decidir guardar a descrição para aquela loja. Segunda leitura traz o produto correspondente, com revisão e conversão corretas.

Aceite:
- Cobertura sem variante não vira branco por marca; confeiteira confirma essa associação.
- Quantidade/unidade/preço originais e dados de estoque aparecem distintos na prévia.
- Aprendizado/aprovação só ocorre junto da compra; cancelar/ignorar/exceção não cria aprovação indevida.
- Segunda compra na mesma loja usa vínculo sem novo ingrediente. Outra loja exige confirmação quando não houver identidade universal.
- Dados ilegíveis ficam pendentes; formulário preservado após erro e fonte mock visível.

Evidência: [relatório da implementação](../../../docs/compras/implementacao-2026-10-07.md). Gates e limites de validação documentados; ticket não publicado externamente.
