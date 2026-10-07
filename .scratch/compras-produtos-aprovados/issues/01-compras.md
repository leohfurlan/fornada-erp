# 01: Cadastrar produto e fornecedores aprovados no ingrediente

**Status:** concluído localmente em 07/10/2026 — divisão aprovada e implementação autorizada.


**Blocked by:** nenhum, utiliza estoque/auth existentes. Requisitos: CMP-01.

Entrega: confeiteira cadastra duas marcas/embalagens para um ingrediente, informa fabricante quando conhecido e escolhe fornecedores aprovados para cada produto. Aprovação retirada/inativação preserva dados; cadastro não modifica saldo/custo.

Aceite:
- Produto aponta para um material próprio, tem conteúdo específico e permite fabricante desconhecido.
- Mesma loja é reutilizável sem aprovar todos os produtos automaticamente.
- Referências alheias, GTIN/CNPJ inválidos, conflito de identificador e revisão desatualizada falham sem gravar.
- Cadastro, edição e inativação demonstráveis em desktop/390 px; estoque/custo continuam iguais.

Evidência: [relatório da implementação](../../../docs/compras/implementacao-2026-10-07.md). Gates e limites de validação documentados; ticket não publicado externamente.
