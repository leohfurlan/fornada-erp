# Plano CMP-01

r2, 07/10/2026. Fonte [PRD Compras r2](../../compras-produtos-aprovados.md); [spec](spec.md); [contrato](contract.md). Implementação local concluída.

1. Entregar cadastro demonstrável de produto/embalagem dentro do ingrediente existente, com marca e fabricante opcional. Dependência: estoque/auth existentes. Checkpoint: cadastrar duas marcas sem novos ingredientes e sem alterar saldo.
2. Integrar fornecedor reutilizável e aprovação por produto, revisão otimista, inativação e validação de identificadores. Checkpoint: aprovar a mesma loja para um produto e verificar que outro continua pendente; edição concorrente retorna 409.
3. Validar isolamento, mudanças de identidade e migração aditiva em banco temporário; fornecer IDs e revisão reais para integração CMP-03 e CMP-02. Checkpoint: histórico futuro pode referenciar produto inativado sem perder snapshot.

Definição de concluído: C1-B1 a B6/C1-E1 a E10 demonstrados por UI, HTTP e banco real; [gates](../qualidade.md) aplicáveis com evidência; migration sem mudanças alheias. Nenhuma aprovação genérica de todas as marcas/lojas. Especificação pronta para decomposição não significa catálogo implementado.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
