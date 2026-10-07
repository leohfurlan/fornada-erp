# Divisão proposta — CMP-01 a CMP-03

Data: 07/10/2026. Fontes: [PRD aprovado r2](../compras-produtos-aprovados.md) e [specs/contratos/planos](README.md). Workflow to-tickets aplicado após to-specs. Status: divisão aprovada em 07/10/2026 e seis fatias concluídas localmente, sem issues externas publicadas. [Relatório](implementacao-2026-10-07.md).

Não há tracker/triagem configurado identificado na inspeção. Os seis tickets locais estão em `.scratch/compras-produtos-aprovados/issues/`, um arquivo por fatia, com evidência da implementação. Aprovação dos requisitos de produto já está registrada e não precisa ser repetida.

## Fatias propostas

Cada fatia inclui persistência, API, interface e verificações do comportamento; infraestrutura e migrations entram na fatia que usa os dados, não como entrega horizontal separada.

### 01 — Cadastrar produto e fornecedores aprovados no ingrediente

Blocked by: nenhum, utiliza estoque/auth existentes. Requisitos: CMP-01.

Entrega: confeiteira cadastra duas marcas/embalagens para um ingrediente, informa fabricante quando conhecido e escolhe fornecedores aprovados para cada produto. Aprovação retirada/inativação preserva dados; cadastro não modifica saldo/custo.

Aceite:
- Produto aponta para um material próprio, tem conteúdo específico e permite fabricante desconhecido.
- Mesma loja é reutilizável sem aprovar todos os produtos automaticamente.
- Referências alheias, GTIN/CNPJ inválidos, conflito de identificador e revisão desatualizada falham sem gravar.
- Cadastro, edição e inativação demonstráveis em desktop/390 px; estoque/custo continuam iguais.

### 02 — Registrar compra com embalagem, preço e histórico

Blocked by: 01. Requisitos: CMP-03.

Entrega: selecionar produto/loja, conferir data/quantidade/valores e confirmar uma compra manual com prévia de conversão, histórico e estoque no mesmo salvamento. Núcleo já inclui idempotência e rollback; não entregar escrita insegura para completar depois.

Aceite:
- 1 barra de 1,01 kg/R$ 35,99 gera 1,01 kg ou 1.010 g, preservando preço original e preço normalizado.
- Duas barras, outra embalagem, descontos e unidade incompatível têm resultados conforme contrato.
- Retry/timeout com mesma chave não duplica; payload diferente retorna 409; erro no último item desfaz tudo.
- Compras distintas concorrentes não perdem saldo/custo; histórico continua após editar produto.
- Material novo não recebe entrada em duplicidade. Data desconhecida não vira data do scan.

### 03 — Conferir cupom e guardar a associação para a próxima compra

Blocked by: 01 e 02. Requisitos: CMP-02 e integração CMP-03.

Entrega: fotografar cupom, selecionar material existente/produto na primeira compra, aprovar produto/loja na hora ou registrar exceção e decidir guardar a descrição para aquela loja. Segunda leitura traz o produto correspondente, com revisão e conversão corretas.

Aceite:
- Cobertura sem variante não vira branco por marca; confeiteira confirma essa associação.
- Quantidade/unidade/preço originais e dados de estoque aparecem distintos na prévia.
- Aprendizado/aprovação só ocorre junto da compra; cancelar/ignorar/exceção não cria aprovação indevida.
- Segunda compra na mesma loja usa vínculo sem novo ingrediente. Outra loja exige confirmação quando não houver identidade universal.
- Dados ilegíveis ficam pendentes; formulário preservado após erro e fonte mock visível.

### 04 — Reconhecer identificadores e corrigir vínculos conflitantes

Blocked by: 03. Requisitos: CMP-01/CMP-02.

Entrega: aproveitar GTIN confirmado ou código de loja quando disponíveis; gerir/corrigir/inativar associações no cadastro sem reclassificar compras anteriores.

Aceite:
- GTIN confirmado pode reconhecer produto em outra loja da própria conta; código de loja permanece local.
- Código interno não vira universal por parecer um EAN. Identificadores contraditórios pedem revisão.
- Mesma marca com branco/ao leite e pacotes 1,01/1,05 kg não recebe associação arbitrária.
- Revisão conflitante retorna 409; edição/inativação deixa alias antigo pendente e preserva histórico.

### 05 — Consultar compras por material, marca, loja e período

Blocked by: 02. Requisitos: CMP-03. Não depende de OCR pronto.

Entrega: histórico com filtros, paginação e detalhes, mostrando embalagens, preços originais/normalizados, data e origem; dados desconhecidos continuam identificados. É consulta histórica, não ranking CMP-04.

Aceite:
- Filtros próprios funcionam; dois tenants com nomes iguais continuam isolados.
- Datas desconhecidas ficam visíveis sem filtro e não entram em filtro de período por suposição.
- Snapshot antigo permanece após edição/inativação do produto ou fornecedor.
- Último preço da compra não é apresentado como custo médio nem como oferta atual.
- Consulta utilizável em desktop/390 px, sem exigir marca/fabricante retroativos.

### 06 — Preservar o fluxo de compras do WhatsApp e concluir a integração

Blocked by: 02 e 03. Requisitos: compatibilidade CMP-02/CMP-03.

Entrega: consumidor existente usa o núcleo da compra/histórico, conserva metadados disponíveis da foto e chave do rascunho; compras legadas continuam válidas. Repetição de evento/CONFIRMAR não duplica entrada.

Aceite:
- Comandos existentes e rascunhos antigos funcionam com campos novos opcionais e histórico incompleto explícito.
- Foto com dados conhecidos conserva loja/data/descrição; não há troca de unidade sem conversão confirmada.
- Revisão/erro/cancelamento não deixam efeito parcial, mock continua rejeitado neste canal.
- Teste usa transporte fake + serviço/banco reais; não enviar mensagem real como efeito da validação local.
- Gates/regressões e cenário integrado web/WhatsApp documentados. Aprovação completa de produtos por conversa permanece futura.

## Bloqueios e fronteira

01 → 02 → 03 → 04.
02 → 05.
02 + 03 → 06.

Após 02, 05 pode iniciar sem 03. Após 03, 04 e 06 não se bloqueiam mutuamente, mas contratos/arquivos compartilhados e migrations precisam de coordenação. Esta descrição não autoriza agentes paralelos.

Não há prefatoração ampla separada: o protocolo transacional e de lock necessário entra na fatia 02, onde é verificável. Nenhum ticket pode ser declarado concluído apenas por mocks. O primeiro incremento completo exige 01 a 06; CMP-04 não recebe ticket nesta rodada.

## Revisão solicitada pelo workflow

Validar se seis fatias têm tamanho adequado e se os bloqueios correspondem a pré-requisitos reais; indicar fusões/divisões necessárias. to-tickets exige aprovação da divisão antes de publicar os tickets. Após aprovação, usar um arquivo por ticket no destino local da skill se esse for o destino escolhido; publicação externa precisa de destino/autorização explícitos.
