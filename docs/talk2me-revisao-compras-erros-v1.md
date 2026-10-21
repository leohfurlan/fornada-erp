# Contrato de erros de revisão de compras — v1

Endpoint Fornada: `POST /api/v1/central/review`. Autenticação de serviço, vínculo negócio/tenant e identidade verificada continuam obrigatórios. A revisão é uma preparação, sem criação de cadastros ou entrada de estoque.

## Resposta

HTTP **422**: corrigir campos, conversões ou aprovações propostas. HTTP **409**: versão/conflito ou proposta expirada. Erros de acesso/identidade permanecem 401/403/404, sem revelar cadastros de outras contas. Uma referência de catálogo indisponível na conta autorizada pode ser indicada como erro seguro de seleção, sem diferenciar “inexistente” de “outra conta”.

Exemplo sintético de loja ausente:

```json
{
  "detail": {
    "code": "purchase_review_invalid",
    "message": "Confira os campos indicados antes de preparar o resumo.",
    "errors": [{
      "code": "supplier_required",
      "item_index": 1,
      "field": "fornecedor_id",
      "action": "select_supplier",
      "message": "Selecione uma loja ou prepare o cadastro de uma nova antes de aprová-la."
    }]
  }
}
```

`item_index` é **zero-based**, relativo a `reviewed.itens` efetivamente enviado após remover/agrupar itens. A UI mostra `item_index + 1`. `null` identifica um problema da compra/proposta. `field` é o nome lógico do campo; para produto novo, pode ser `produto_novo.marca`. Uma aprovação de loja pertence a um item, mas sua referência é global (`fornecedor_id`/`fornecedor_novo`). Para produto existente, erros de embalagem/conteúdo apontam a seleção `produto_id`.

`errors` contém até 100 erros de schema; validações de domínio param na primeira recusa impeditiva. Pendências de aprovação da prévia podem produzir vários erros. Não representa uma lista exaustiva de todos os problemas possíveis da compra. Corrigir, conferir e salvar novamente; não aplicar correções comerciais automaticamente.

Não há `input`, conteúdo do cupom, valor financeiro, telefone, UUID de cadastro, credencial, traceback ou texto bruto da exceção nos diagnósticos. Mensagens são orientações fixas. Código/ação são o contrato; não interpretar texto para decidir comportamento.

## Exemplos sintéticos de revisão

Fornecedor não selecionado, com aprovação solicitada:

```json
{"fornecedor_id": null, "fornecedor_novo": null, "itens": [{"aprovar_fornecedor": true}]}
```

Esse fragmento é inválido. O operador deve escolher fornecedor autorizado ou preparar `fornecedor_novo: {"nome": "Loja sintética"}`. `estabelecimento: "Loja sintética"` sozinho não cria nem seleciona um fornecedor. Para aprovar a loja para um produto, também é necessário selecionar/preparar esse produto.

Produto não selecionado, com aprovação solicitada:

```json
{"produto_id": null, "produto_novo": null, "aprovar_produto": true}
```

Esse fragmento é inválido. Selecionar produto com sua `produto_revisao`, ou preparar um `produto_novo` com marca e conteúdo confirmados. `ingrediente_id` identifica o material de estoque e não substitui o produto comercial.

Seleção parcial e grupo já somado, com os demais campos válidos:

```json
{
  "total_nota": "100.00",
  "itens": [{
    "criar_novo": true,
    "nome": "Material sintético",
    "tipo": "ingrediente",
    "unidade_principal": "kg",
    "descricao_original": "FARINHA",
    "quantidade": "3",
    "unidade": "kg",
    "custo_unitario": "10",
    "desconto_item": "2",
    "preco_total": "28.00",
    "aceitar_excecao": true
  }]
}
```

Total selecionado = 28, menor que 100, é permitido. O grupo contém quantidade 3 e desconto 2 **já somados**; não multiplicar novamente por quantidade de ocorrências. Esse exemplo prepara novo material como proposta; salvar não o cria. Aprovação identificada posterior continua necessária para a execução.

Para três embalagens de 500 g, usar quantidade fiscal 3, unidade `un`, conteúdo comercial 500 e unidade de conteúdo `g`; estoque em kg resulta em 1,5 kg. Não usar 500 como quantidade fiscal quando o preço foi cobrado por embalagem.

## Recuperação no Talk2Me

- `refresh_catalog`: operador atualiza catálogo e confere material/produto e embalagem antes de salvar.
- `refresh_proposal`: `POST /api/businesses/{business_id}/conversations/{conversation_id}/purchases/{flow_id}/refresh-source`, com `expected_version` da **central** e `expected_control_version` da conversa. Requer controle humano, vínculo atual e compra em estado revisável. Consulta `draft`, atualiza a cópia local e sua versão, volta para `review`. Não salva revisão no Fornada, não aprova, não envia mensagem e não executa compra.
- Substituir edição não salva exige confirmação na interface. Nenhuma recuperação é automática ao receber erro.
- `review_in_fornada`: concluir verificação diretamente no ERP (por exemplo, expiração ou duplicidade); não forçar override pelo bot.
- Os demais códigos orientam correção manual dos campos ou configuração explícita de conversões.

Salvar outra revisão invalida resumos/aprovações anteriores. O cliente não deve reutilizar hash/versão de resumo obsoleto. A adição de `pendencias_codigos` à prévia também participa do hash; propostas antigas precisam gerar resumo atual, sem contornar a verificação.

O adaptador aceita esse envelope somente em erros 409/422 de `review`, até 64 KiB. Códigos desconhecidos, corpos privados/internos ou acima do limite resultam em erro genérico. Catálogos de mensagens do backend/frontend Talk2Me devem acompanhar os códigos publicados pelo Fornada.

## Códigos

O índice e o campo podem ser refinados pelo caminho do schema. Catálogo atual:

| Código | Campo padrão | Ação |
|---|---|---|
| supplier_required | fornecedor_id | select_supplier |
| product_required | produto_id | select_product |
| product_approval_required | aprovar_produto | review_approval |
| supplier_approval_required | aprovar_fornecedor | review_approval |
| product_version_changed | produto_revisao | refresh_catalog |
| proposal_version_changed | expected_version | refresh_proposal |
| proposal_expired | proposal_id | review_in_fornada |
| product_material_mismatch | produto_id | select_product |
| material_unavailable | ingrediente_id | refresh_catalog |
| product_unavailable | produto_id | refresh_catalog |
| supplier_unavailable | fornecedor_id | refresh_catalog |
| supplier_exists | fornecedor_novo | select_supplier |
| content_conversion_required | produto_novo.unidade_conteudo | configure_conversion |
| content_conversion_conflict | produto_novo.fator_para_principal | configure_conversion |
| fiscal_conversion_required | unidade | configure_conversion |
| variant_mismatch | produto_novo.variante | check_package |
| package_mismatch | produto_novo.conteudo_embalagem | check_package |
| gtin_mismatch | gtin_confirmado | select_product |
| gtin_exists | gtin_confirmado | select_product |
| item_total_mismatch | preco_total | check_amounts |
| stock_precision_exceeded | quantidade | check_amounts |
| stock_limit_exceeded | quantidade | check_amounts |
| cost_limit_exceeded | custo_unitario | check_amounts |
| future_purchase_date | data_compra | check_date |
| duplicate_review_required | confirmar_duplicidade | review_in_fornada |
| link_requirements | guardar_vinculo | review_approval |
| review_conflict | conflito_vinculo | refresh_catalog |
| review_invalid | reviewed | check_fields |
| material_selection_invalid | ingrediente_id | select_material |
| product_selection_invalid | produto_id | select_product |
| exception_link_conflict | guardar_vinculo | review_approval |
| supplier_selection_invalid | fornecedor_id | select_supplier |
| receipt_identity_required | identidade_nota | check_fields |
| field_required | reviewed | check_fields |
| invalid_value | reviewed | check_fields |
| brand_required | produto_novo.marca | check_fields |
| invalid_gtin | gtin | check_fields |
| invalid_cnpj | fornecedor_novo.cnpj | check_fields |
