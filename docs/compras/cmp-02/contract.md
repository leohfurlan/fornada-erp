# Contrato CMP-02 — leitura e associação

Contrato r2, 07/10/2026, implementado e validado localmente. Fonte [PRD r2](../../compras-produtos-aprovados.md); [spec](spec.md); [plano](plan.md).

## Boundaries e owners

| Provedor | Consumidor | Owner/interface | Prontidão |
|---|---|---|---|
| GemmaOCRAdapter | CMP-02 | Extração da imagem, valores originais e metadados | Adapter ampliado com campos opcionais e ausências |
| CMP-01 | CMP-02 | [Produto, fornecedor e revisão](../cmp-01/contract.md) | Implementado |
| CMP-02 | Web/WhatsApp | Sugestões, pendências e contexto original | Implementado |
| CMP-03 | CMP-02 | [Prévia e confirmação](../cmp-03/contract.md) | Implementado; owner da transação |
| CMP-02 | CMP-03 | Validar e persistir associação solicitada na mesma sessão | Implementado; sem commit próprio |

IDs de produtos/fornecedores vêm do catálogo; material vem de estoque. Todo lookup valida tenant efetivo do servidor. Prefixo /api/v1, autenticação e erros conforme CMP-01; nenhuma escrita de catálogo/estoque na leitura.

## HTTP implementado

POST /compras/v2/ocr recebe multipart arquivo, opcional fornecedor_id previamente escolhido. Aceitar os MIME já permitidos no router atual e limitar a 8 MB/20 leituras por minuto. Arquivo vazio/inválido é 422; rate limit 429; indisponibilidade OCR devolve erro recuperável em português conforme padrão de domínio, sem dados persistidos.

200 LeituraCompra:
- itens: ItemLido[], total_nota: moeda ou null, estabelecimento: string ou null, data_compra: data ISO ou null, data_original: texto observado ou null.
- fornecedor_id: UUID ou null; fornecedores_candidatos: [{id,nome,cnpj?}], cnpj_observado: string ou null. CNPJ confirmado pode resolver ID único; somente nome não escolhe em caso de dúvida.
- identidade_nota: string ou null, identidade_confirmada: false por default de extração não revisada.
- fonte: string atual (gemma4/mock), confianca: número 0–1; aviso_mock bool. Não usar confianca como aprovação.

ItemLido:
- indice int >= 0, descricao string, quantidade Decimal ou null, unidade string ou null, preco_unitario/preco_total/desconto_item Decimal ou null.
- marca_observada, fabricante_observado, variante_observada: string ou null, sem preenchimento a partir de suposição.
- conteudo_observado/unidade_conteudo_observada: Decimal/string ou null; meramente extraídos, não confirmação de embalagem.
- codigo_loja: string ou null; gtin: string ou null; gtin_confirmado bool default false.
- ingrediente_id/nome_match, produto_id/produto_revisao: referências ou null.
- reconhecimento: gtin_confirmado | codigo_loja | descricao_loja | similaridade | conflito | nenhum; score 0–1.
- explicacao string em português; pendencias string[]; candidatos [{produto_id,produto_revisao,ingrediente_id,nome_produto,nome_material}]; vinculo_id/vinculo_revisao ou null.
- tipo_sugerido/unidade_sugerida preservam intenção existente; unidade_sugerida NÃO altera unidade, quantidade ou preço originais.

POST /compras/v2/reconhecer recebe {fornecedor_id UUID ou null, itens: ItemObservado[]} e devolve {itens: ItemLido[]}. ItemObservado contém indice, descricao, campos originais/comerciais extraídos e gtin_confirmado; não contém candidatos/score/IDs sugeridos. Até 100 itens. Permite reavaliar ao selecionar a loja sem OCR repetido; é leitura, não confiança em classificações enviadas pelo cliente. gtin_confirmado true é declaração explícita da usuária, validada contra catálogo e dígitos; não aceita texto arbitrário como identificador. Request sem auth/tenant válido falha antes do lookup.

GET /compras/vinculos recebe fornecedor_id? e produto_id? UUID, limit=50 (1–200), offset>=0; retorna 200 {itens: Vinculo[], total:int}. Ativos apenas; referências alheias 404.
PATCH /compras/vinculos/{id} recebe {revisao, produto_id, produto_revisao}; responde 200 Vinculo revisado, sem tocar compras antigas. Material de destino deriva do produto. DELETE mesmo caminho com query revisao faz soft delete, 204. Correção/inativação deliberada fora da compra tem UI própria no cadastro, com confirmação de remoção.

Vinculo: id, fornecedor_id, produto_id, tipo (codigo_loja/descricao_loja), valor_original, valor_normalizado, revisao, produto_revisao_confirmada, ativo bool. Histórico de compra guarda a identificação aplicada; mudança de vínculo não o reclassifica.

## Resolução e aprendizagem

resolver_itens(tenant, fornecedor_id?, observados) usa catálogo e aliases ativos; não grava. Erro de metadado pode virar pendência, mas conflito entre identificadores conhecidos nunca vira match único por prioridade. Score atual 0,62 pode ser reaproveitado para sugestão de ingrediente; empate não seleciona por ordem.

validar_vinculo(tenant, fornecedor, produto/revisao, chave, conflito/revisao?) e persistir_vinculo(..., sessao) são chamadas do núcleo CMP-03 apenas para itens confirmados com guardar_vinculo=true. Fornecedor identificado e produto aprovado são obrigatórios. Alias existente igual é reutilizado; diferente exige revisão explícita; versão comercial mudou exige reconfirmação. Erro de qualquer vínculo desfaz a compra inteira.

Escopo universal só para GTIN confirmado; demais chaves incluem fornecedor/tenant. Normalização exata preserva conteúdo e variante; similaridade não cria alias nem aprovação. Não preencher fabricante observando apenas marca.

## Compatibilidade e testes

V1 /compras/ocr e /compras/confirmar conservam contratos; evoluir projeção do adapter em conjunto. Dados numéricos ausentes não devem virar “1” invisível no novo fluxo. Sucessos com campos completos permanecem equivalentes; ilegíveis levam à revisão/erro recuperável, não estoque. WhatsApp mantém confirmação explícita e rejeição de mock; revisão de aprovação completa por conversa fica futura.

Teste produtor: extração estruturada identifica ausência e preserva decimal/data originais. Teste consumidor: contrato retorna pendências/candidatos e UI chama prévia CMP-03 com valores originais. Integração real: primeira confirmação aprende alias e segunda leitura o usa sem alterar estoque até salvar. Incluir lojas/tenants distintos, score empatado, embalagem diferente, GTIN conflitante e alias revisado. Testes executados localmente; ver relatório abaixo.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
