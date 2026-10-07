# CMP-01 — Produtos aprovados

Spec r2, 07/10/2026. Produto aprovado no [PRD Compras r2](../../compras-produtos-aprovados.md). Interface: [contract.md](contract.md). Execução: [plan.md](plan.md). Requisito aprovado; implementação local concluída. Decisões técnicas abaixo refinam o escopo e serão consumidas pelos tickets.

## Evidência anterior à implementação e escopo

Ingrediente, unidade principal e alternativas já existem em estoque; API atual permite criar/editar ingrediente. Não há entidade de produto comercial, fornecedor ou aprovação. Reutilizar IDs e autenticação existentes. Não modificar receitas, PROD-01 ou saldo ao cadastrar produto.

## Comportamento verificável

- C1-B1: material próprio ativo admite vários produtos comerciais. Cada produto aponta para um único material e contém marca, variante opcional, fabricante opcional e conteúdo/unidade. Uma loja pode atender vários produtos, com aprovação independente.
- C1-B2: cadastrar, editar, aprovar, retirar aprovação e inativar produto/fornecedor nunca muda saldo/custo nem compras existentes. Inativação é soft delete; retirar aprovação permite compra excepcional revisada.
- C1-B3: ID de outra conta/inativo retorna 404. Nome parecido de loja não é fundido automaticamente. CNPJ confirmado identifica fornecedor na conta.
- C1-B4: embalagem, variante ou marca alterada exige revisão atual; concorrência é 409. Vínculos aprendidos sob identidade anterior deixam de reconhecer automaticamente após alteração comercial, até reconfirmação.
- C1-B5: código universal validado ativo identifica no máximo um produto por conta. Código de loja pertence à combinação fornecedor/código. Duplicidade incompatível é 409, nunca mesclagem silenciosa.
- C1-B6: produto com unidade de conteúdo incompatível com o material exige conversão explícita própria; não inventar densidade nem alterar conversão métrica exata. Item que não consegue converter não pode ser confirmado no estoque.

## Casos de borda e rastreabilidade

| Caso | Entrada/estado | Resultado | Verificação |
|---|---|---|---|
| C1-E1 | Nome vazio, conteúdo zero/negativo, decimal fora do limite | 422, nenhum cadastro | C1-B1/B6; QA-07 |
| C1-E2 | fabricante/variante/CNPJ ausentes | Cadastro válido; null preservado | C1-B1; QA-01/12 |
| C1-E3 | ID de material/fornecedor de outra conta | 404 sem efeito | C1-B3; QA-10 |
| C1-E4 | Dois produtos de marca igual branco/ao leite | Cadastros distintos, nenhuma aprovação cruzada | C1-B1/B5; QA-05 |
| C1-E5 | Trocar conteúdo 1,01 → 1,05 | Revisão incrementada; compras antigas imutáveis; alias pendente | C1-B2/B4; QA-04/11 |
| C1-E6 | Dois PATCH com mesma revisão | Um sucesso; outro 409 | C1-B4; QA-11 |
| C1-E7 | GTIN inválido ou duplicado ativo | 422 inválido; 409 conflitante | C1-B5; QA-07 |
| C1-E8 | g/kg versus ml/g | Métrica exata permitida; dimensão incompatível sem fator rejeitada | C1-B6; QA-15 |
| C1-E9 | Produto/loja inativados | Não oferecidos como ativos; histórico preservado | C1-B2/B3; QA-11 |
| C1-E10 | Fornecedor sem CNPJ com nome igual a outro | IDs distintos; escolha explícita | C1-B3; QA-12 |

Todos os seis critérios CMP-01 do PRD são cobertos por C1-B1 a B6 e casos acima. Temporização de jobs/eventos não se aplica ao CRUD síncrono; retry de criação sem ID requer resolução de duplicidade, sem afirmar identidade por nome.

## Decisões técnicas e persistência

Propor módulo de catálogo comercial em domain/compras com repository próprio e modelos novos em infrastructure/database/compras_models.py; serviços de compras dependem de interfaces mínimas de leitura/escrita. Evitar segunda cópia de EstoqueService.

Tabelas propostas: produtos_compra, fornecedores_compra e aprovacoes_fornecedor_produto. UUID, tenant_id, timestamps e deleted_at em todas; sem CASCADE DELETE. Produto armazena strings marca/fabricante, conteúdo Decimal, unidade, aprovado, revisão e material. Relação fornecedor/produto única por conta; fabricante não exige tabela própria. Índices por tenant, material e identificadores ativos; relações devem garantir igualdade de tenant também na escrita.

Escolha de fornecedor por produto é mais restrita que por material e satisfaz a aprovação na hora aceita; reutilização da loja continua possível. Revisão otimista segue o padrão da ficha técnica existente. Alterar identidade incrementa revisão; alias referencia revisão comercial aprovada e não será reutilizado sem reconfirmação. Alterar somente aprovação não precisa alterar embalagem histórica.

```mermaid
sequenceDiagram
  actor U as Confeiteira
  participant UI as Cadastro do ingrediente
  participant API as Catalogo de compras
  participant DB as PostgreSQL
  U->>UI: Adicionar produto e embalagem
  UI->>API: POST produto com material proprio
  API->>DB: Validar tenant, unidade e identificadores
  alt invalido ou conflitante
    API-->>UI: 404, 422 ou 409; sem gravacao
  else valido
    API->>DB: Gravar produto e revisao
    API-->>UI: Produto cadastrado; saldo inalterado
  end
```

## Integração, regressão e readiness

CMP-01 fornece IDs revisados a CMP-02/CMP-03, conforme contrato. IDs de material vêm da API real de estoque; integração deve testar material válido e inválido, não apenas catálogo mockado. CRUD precisa de cenário HTTP + PostgreSQL e UI desktop/390 px.

Aplicar [gates compartilhados](../qualidade.md). Migration aditiva sem recadastro/backfill de produtos. A spec está preparada para tickets; provider comercial ainda não implementado. Nenhuma mudança de contrato de receitas ou de estoque existente é necessária para o CRUD.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
