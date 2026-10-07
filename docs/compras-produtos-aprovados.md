# Compras: produtos aprovados e histórico de preços

Data: 07/10/2026. Revisão 3 — primeiro incremento implementado localmente; escopo aprovado na revisão 2. Extensão do [PRD canônico](../prd.md).

Status: requisitos de produto aprovados por Leonardo em 07/10/2026: “Pode proseeguir com o plano. Essa proposta está aceita”. A aprovação abrange a estrutura, o primeiro incremento CMP-01 a CMP-03 e os critérios de aceite; CMP-04 permanece futuro. Implementação autorizada em seguida por “Validado. Implementar” e concluída localmente. [Especificações e sequência](compras/README.md); [relatório de implementação](compras/implementacao-2026-10-07.md).

## Problema e resultado esperado

A leitura do cupom identificou o Empório Ponto X e o item `COBERTURA EM BARRA DR.OETKER 1,01KG`, quantidade 1 e preço R$ 35,99. Entretanto, a confeiteira precisa indicar que esse produto corresponde ao ingrediente usado nas receitas, neste caso “Chocolate branco”. Criar um ingrediente com a descrição fiscal a cada compra fragmentaria estoque, custos e receitas.

O objetivo confirmado é cadastrar fabricantes, marcas e fornecedores aprovados para os materiais; direcionar as próximas leituras ao ingrediente correto; guardar loja, data, marca e preço da compra; e formar uma base para um relatório futuro de onde comprar. A compra de marca ou loja ainda não aprovada deve pedir revisão e permitir aprovação na hora, conforme resposta do usuário.

O reconhecimento preenche uma sugestão. A confeiteira continua conferindo e confirmando a compra antes de qualquer entrada no estoque. Aprovar um produto, aprovar uma loja e salvar uma compra são decisões distintas.

## Situação atual verificada no código

| Comportamento | Situação atual | Evolução necessária |
|---|---|---|
| Fotografia e extração dos itens | OCR devolve descrição, quantidade, unidade, preços, estabelecimento e data | Preservar informações originais e levar a data à revisão |
| Associação ao ingrediente | Similaridade de texto com o nome; tela permite escolher “Existente” | Reconhecer produtos aprovados e associações confirmadas anteriormente |
| Aprendizado da escolha | Não persiste a associação feita na revisão | Guardar vínculo explícito dentro da conta |
| Marca e fabricante | Ausentes do cadastro e do item de compra | Registrar identidade comercial sem deduzir fabricante da marca |
| Loja | Nome exibido e recebido na confirmação; não persistido pelo serviço de compras | Identificar fornecedor e conservar o nome observado na nota |
| Data de compra | Existe no resultado do OCR, mas não na resposta de compras nem na confirmação | Separar data da nota de data de registro |
| Histórico | Movimentação guarda quantidade, custo unitário e origem | Conservar também compra, item comercial, loja, data e embalagem |
| Conversão de unidades | Estoque aceita conversões métricas e alternativas do ingrediente | Acrescentar conteúdo específico da embalagem do produto aprovado |

Evidências: `backend/domain/compras/{matching,schemas,service}.py`, `backend/infrastructure/ocr/gemma_adapter.py`, `backend/domain/estoque/{schemas,service,unidades}.py`, `backend/infrastructure/database/models.py` e `frontend/app/(dashboard)/compras/page.tsx`. O fluxo de compras do WhatsApp também usa o serviço de compras; a futura evolução deve preservar revisão, confirmação e proteção contra repetição, sem presumir que os novos campos já existem nesse canal.

## Conceitos e proposta de cadastro

| Conceito | Papel | Exemplo desta compra |
|---|---|---|
| Ingrediente/matéria-prima | Material consumido pelas receitas, com saldo e custo médio | Chocolate branco, conforme classificação indicada pelo usuário |
| Produto aprovado para compra | Variante comercial vinculada a um único material, com conteúdo da embalagem | Cobertura branca em barra, Dr. Oetker, 1,01 kg; variante a confirmar |
| Marca | Nome comercial do produto | Dr. Oetker, extraído da descrição e sujeito a revisão |
| Fabricante | Empresa que fabrica o produto | Não identificado na evidência apresentada; campo opcional |
| Fornecedor/loja | Quem vendeu o produto; aprovação por material ou produto | Empório Ponto X |
| Descrição reconhecida | Texto da nota previamente associado a um produto | COBERTURA EM BARRA DR.OETKER 1,01KG |
| Compra | Ocorrência real com data, fornecedor, quantidades e valores próprios | Uma barra por R$ 35,99 |

Proposta: incluir uma seção **Produtos aprovados** no cadastro do ingrediente, em vez de três listas de texto independentes. Cada produto contém nome comercial, marca, fabricante opcional, variante, conteúdo e unidade da embalagem, identificadores quando disponíveis, descrições confirmadas e fornecedores aprovados. O mesmo ingrediente pode aceitar várias marcas e embalagens. Uma marca ou fabricante pode atender vários ingredientes; aprovar a marca para um produto não aprova todas as suas variantes.

O fornecedor é reutilizável dentro da conta. Quando houver CNPJ confirmado, ele ajuda a distinguir estabelecimentos; nomes parecidos sem identificação suficiente exigem revisão. Fabricante e fornecedor podem ser a mesma empresa, mas seus papéis continuam separados. Campos desconhecidos permanecem ausentes, sem impedir o cadastro básico.

## Exemplo de funcionamento

1. A confeiteira fotografa a nota e confere loja, data, item e valores.
2. Na primeira compra, seleciona **Existente → Chocolate branco** e informa/confirma marca, variante e embalagem de 1,01 kg.
3. A revisão oferece **Guardar este produto para próximas compras**. A descrição é guardada para aquela loja; aprovar o produto não generaliza automaticamente a descrição para todos os mercados.
4. Se a marca ou loja ainda não estiver aprovada para esse uso, a tela mostra o motivo e oferece aprovação na hora. A usuária também pode registrar apenas esta compra revisada, sem criar uma aprovação permanente.
5. Ao confirmar, o sistema grava compra e histórico e dá entrada no ingrediente escolhido usando o conteúdo confirmado da embalagem.
6. Na próxima leitura compatível, o ingrediente e o produto vêm preenchidos. A confeiteira revisa quantidades e preço e confirma a entrada.

### Dados do cupom e conversão

| Campo | Valor ou tratamento |
|---|---|
| Loja observada | Empório Ponto X |
| Data impressa na nota | 03/10/2026, a confirmar na revisão; distinta do dia de envio da foto |
| Descrição original | COBERTURA EM BARRA DR.OETKER 1,01KG |
| Quantidade fiscal | 1 UN |
| Conteúdo da embalagem | 1,01 kg, após confirmação |
| Valor do item | R$ 35,99 |
| Material de destino | Chocolate branco, classificação indicada pelo usuário |
| Quantidade de estoque | 1,01 kg, ou 1.010 g se essa for a unidade principal |
| Preço comparável | 35,99 ÷ 1,01 ≈ R$ 35,63/kg |

A descrição não informa “branco”. O sistema não deve descobrir a variante só pela marca. Também não deve transformar “cobertura” em comprovação de composição: a classificação interna indicada pela confeiteira e a descrição comercial original precisam coexistir. Variante e adequação à receita exigem confirmação pelo produto/embalagem.

Comprar uma unidade não equivale a comprar um quilograma. O preço original por barra deve permanecer no histórico, junto com a quantidade convertida e o preço por kg. Um pacote de 1,01 kg e outro de 1,05 kg precisam ter conversões próprias; um fator genérico de “unidade” no ingrediente não resolve embalagens diferentes.

## Catálogo de requisitos

Mantém-se o esquema de IDs por área do PRD. Os IDs existentes não são renumerados.

| ID | Resultado | Ator | Prioridade | Situação | Pré-requisitos obrigatórios | Fornece/consome |
|---|---|---|---|---|---|---|
| CMP-01 | Produtos, marcas, fabricantes e fornecedores aprovados por material | Usuária da confeitaria | Primeiro incremento | Implementado e validado localmente | Cadastro de ingredientes já existente | Fornece identidade comercial e conteúdo das embalagens |
| CMP-02 | Vínculo reutilizável entre item lido e produto/material correto | Usuária da confeitaria | Primeiro incremento | Implementado e validado localmente | CMP-01 e OCR existente | Consome produtos aprovados; fornece sugestões e vínculos revisados |
| CMP-03 | Histórico completo de compras e preços normalizados | Usuária da confeitaria | Primeiro incremento | Implementado e validado localmente | CMP-01 e entrada de estoque existente | Consome identidade comercial; fornece ocorrências e valores comparáveis |
| CMP-04 | Comparação de locais e marcas para orientar compras | Usuária da confeitaria | Futuro | Intenção confirmada; formato e prioridade pendentes | CMP-03 | Consome histórico próprio; fornece comparação por período e unidade |

### CMP-01 — Produtos aprovados

Histórias:

1. CMP-01.1: como confeiteira, quero vincular produtos comerciais ao material das receitas, para comprar marcas diferentes sem duplicar o ingrediente.
2. CMP-01.2: quero informar conteúdo, variante e identificadores, para distinguir produtos e embalagens.
3. CMP-01.3: quero aprovar ou retirar aprovação de produtos e fornecedores, para manter minhas preferências de compra.

Critérios de aceite aprovados:

- A seção Produtos aprovados permite cadastrar, editar e inativar um produto, sua marca, fabricante opcional e fornecedores aprovados, mostrando o material de destino.
- Cada variante/embalagem possui conteúdo e unidade próprios, confirmados pela usuária. Trocar tamanho ou composição não redefine retroativamente compras antigas.
- Identificadores como GTIN/EAN são opcionais e validados quando informados. Código interno da loja não é tratado automaticamente como código universal.
- A marca aprovada para cobertura branca não basta para reconhecer cobertura ao leite, meio amarga ou outro produto da mesma marca.
- O cadastro não altera estoque. Inativar uma aprovação preserva histórico e impede seu uso como vínculo automático nas próximas compras.
- Cadastros e aprovações pertencem à conta; outra confeitaria não herda os vínculos ou fornecedores aprovados.

### CMP-02 — Reconhecimento e aprovação na revisão

Histórias:

1. CMP-02.1: como confeiteira, quero escolher um material existente na primeira leitura e guardar o vínculo, para evitar repetir o cadastro.
2. CMP-02.2: quero receber o produto correto preenchido nas próximas notas, para revisar apenas os dados da compra quando forem compatíveis.
3. CMP-02.3: quero resolver marcas e lojas ainda não aprovadas durante a revisão, para concluir a compra sem abandonar a tela.

Critérios de aceite aprovados:

- Prioridade de reconhecimento: identificador universal validado e sem conflito → código do produto confirmado naquela loja → descrição confirmada naquela loja → sugestão por similaridade de texto. Conflitos em dados da variante ou embalagem levam à revisão, mesmo com identificador conhecido.
- Uma descrição genérica de cobertura Dr. Oetker, sem vínculo anterior, não seleciona branco por dedução. Marca ou fornecedor isoladamente não determina o ingrediente.
- Vínculos exatos ativos preenchem produto, material e conversão com uma explicação simples, como “Produto que você já confirmou nesta loja”. Similaridade é apresentada como sugestão para conferir.
- Descrições mantêm tamanho e termos que distinguem variantes. Não remover “branco”, “meio amargo” ou conteúdo da embalagem ao normalizar para reconhecimento.
- Se houver mais de um candidato ou evidência insuficiente, pedir escolha; não selecionar arbitrariamente nem exigir criação de ingrediente novo.
- A usuária consegue escolher material existente, ignorar item, corrigir produto/embalagem e decidir se guarda o vínculo. Descrição reconhecida em outra loja exige nova confirmação, salvo identificador universal validado.
- Marca ou fornecedor ainda não aprovado mostra pendência e permite aprovar na hora, conforme decisão confirmada. Permitir uma compra excepcional revisada sem aprovação permanente; essa opção fica identificada no histórico.
- Aprovação salva deve explicitar seu alcance: produto para o material, fornecedor para esse material/produto e descrição para aquela loja. Não ampliar a aprovação para todas as marcas, produtos ou lojas.
- Leitura e preenchimento não geram estoque. Compra, aprovação solicitada e vínculo aprendido são gravados na confirmação; cancelar descarta a prévia e seus novos vínculos.
- Se uma descrição da loja já aponta para outro produto, mostrar conflito e pedir correção explícita, preservando compras antigas.

### CMP-03 — Compra e histórico

Histórias:

1. CMP-03.1: como confeiteira, quero guardar data, loja, marca, quantidade e valor, para saber o que comprei e onde.
2. CMP-03.2: quero consultar preços por unidade comparável, para avaliar compras com tamanhos de embalagem diferentes.
3. CMP-03.3: quero que histórico, estoque e custo médio representem a mesma compra, para confiar nos números.

Critérios de aceite aprovados:

- A revisão permite conferir/corrigir estabelecimento e data da compra. Data ausente ou ilegível exige informar a data ou manter “não identificada”, sem substituir silenciosamente pelo dia do registro.
- Cada item conserva descrição e identificadores disponíveis da nota, material escolhido, produto/variante, marca, fabricante conhecido, fornecedor, data da compra e data de registro, origem e responsável pela confirmação.
- Guardar quantidade/unidade originais, quantidade de embalagens, conteúdo por embalagem, preço original, total confirmado, quantidade convertida, unidade principal e preço normalizado. Dados comerciais e fator usados na confirmação permanecem como fotografia histórica, mesmo após edição do cadastro.
- Preço normalizado deriva do total efetivo do item dividido pela quantidade convertida. Descontos explícitos podem ser considerados; descontos gerais sem distribuição e valores divergentes exigem revisão, sem inventar rateio.
- Se conteúdo ou conversão estiverem ausentes, a entrada no material que exige conversão fica pendente de correção; o item não aparece como preço comparável até resolver a pendência.
- Confirmação gera histórico, entrada de estoque e custo médio na mesma operação: falha em qualquer item não deixa compra parcial. Repetir o envio da mesma confirmação não duplica compra nem estoque.
- Quando houver identidade confiável da nota, uma nova importação dela alerta sobre duplicidade. Sem essa identidade, coincidência de loja/data/valor é apenas alerta para revisão, pois duas compras legítimas podem ser iguais.
- Histórico permite consultar material, marca, fornecedor e período, mostrando a origem dos valores. Custo médio do ingrediente continua distinto do último preço de compra.
- Histórico e consultas respeitam isolamento entre contas. Compras anteriores continuam disponíveis com seus dados atuais; campos novos ausentes são apresentados como desconhecidos, sem reconstruir marcas ou lojas por suposição.

### CMP-04 — Onde comprar (futuro)

Histórias:

1. CMP-04.1: como confeiteira, quero comparar lojas para o mesmo material/produto, para planejar minhas compras.
2. CMP-04.2: quero ver data e quantidade de observações, para avaliar se um preço antigo ainda ajuda na decisão.

Critérios de aceite propostos:

- Comparar o mesmo produto entre lojas e, separadamente, alternativas aprovadas para o mesmo material; marcas/variantes ficam visíveis, sem presumir qualidade equivalente.
- Exibir preço por kg/litro/unidade compatível, embalagem, marca, loja, data da última compra e quantidade de observações no período. Não comparar peso e volume sem conversão explícita.
- Mostrar último preço pago e menor preço observado no período como indicadores distintos. Período e ordenação são visíveis; não afirmar preço atual ou disponibilidade da loja com base no histórico.
- Dados incompletos ou não comparáveis ficam identificados e fora do ranking por preço normalizado. Compras excepcionais de produtos não aprovados não viram alternativas recomendadas automaticamente.
- A comparação usa compras da própria conta. Deslocamento, frete, estoque da loja e vantagens de qualidade não estão medidos nesta primeira proposta; “melhor compra” dependerá desses critérios se forem acrescentados depois.

## Dependências e sequência de entrega

| Provedor → consumidor | Motivo |
|---|---|
| Cadastro de ingredientes existente → CMP-01 | Material de destino, unidade principal e identidade da conta |
| CMP-01 → CMP-02 | Produtos aprovados, identificadores e conteúdo por embalagem |
| CMP-01 → CMP-03 | Identidade comercial e conversão registrada na compra |
| OCR existente → CMP-02 | Descrição, quantidades e valores extraídos |
| Entrada de estoque existente → CMP-03 | Conversão, movimentação e custo médio |
| CMP-03 → CMP-04 | Histórico persistido para comparação |

Primeira onda: CMP-01. Segunda onda: CMP-02 e CMP-03, coordenados pela mesma confirmação de compra; entregar ao usuário o fluxo integrado, com histórico, antes de considerar o reconhecimento concluído. Os contratos compartilhados exigem especificação conjunta; a sequência não autoriza trabalho de agentes em paralelo. Terceira onda: CMP-04, após acumular dados comparáveis e decidir o formato do relatório.

OCR é uma integração já existente. O primeiro incremento mantém o canal web por foto. Na especificação, avaliar a compatibilidade do consumidor WhatsApp e garantir que não perca dados nem aplique conversões diferentes; a experiência completa de aprovar produtos por conversa pode ser um incremento próprio. Não é necessário contratar outro serviço de IA para os vínculos confirmados.

## Validação proposta

Usar o cupom apresentado como cenário de referência, com valores revisados; validar o cadastro e o fluxo web em desktop e celular de 390 px. As verificações observáveis devem cobrir:

- Primeira associação a Chocolate branco e segunda leitura do mesmo produto, com histórico correto e sem ingrediente duplicado.
- Marca igual com variantes branca e ao leite; descrição sem variante, vínculo conflitante e fornecedor ainda não aprovado.
- Embalagens de 1,01 kg e 1,05 kg, quantidade de duas barras e material em g/kg, preservando total e custo médio.
- Aprovação na hora, compra excepcional sem aprovação permanente, cancelamento e item ignorado.
- Data da compra diferente do dia do scan, dados ausentes e preço divergente sujeito a revisão.
- Repetição de confirmação, segunda importação da mesma nota e falha no último item sem efeitos parciais.
- Duas contas com produtos/lojas de nomes iguais, sem compartilhamento de dados ou sugestões.
- Edição/inativação do produto sem alteração do histórico; comportamento compatível do fluxo de compras do WhatsApp.

Medidas de acompanhamento: proporção de itens vinculados sem novo ingrediente na segunda compra, frequência de correções por vínculo incorreto, cobertura do histórico com unidade comparável e tempo de revisão. Não há metas numéricas ou linha de base medidas nesta revisão; essas métricas não são gates de entrega. Os cenários de validação acima foram aceitos com a proposta.

## Limites e decisões pendentes

- Estrutura de Produtos aprovados, critérios de aceite e compra excepcional sem aprovação permanente aceitos com a proposta em 07/10/2026.
- Na especificação, adotar fornecedor aprovado por produto específico como alcance inicial, sem aprovação implícita para todos os materiais. O fornecedor continua reutilizável na conta.
- Confirmar na embalagem a variante do exemplo e se “Chocolate branco” deve ser o nome interno, mantendo a descrição de cobertura no histórico.
- Histórico entregue com filtros e detalhes; definir futuramente período padrão e critérios do relatório CMP-04. Relatório futuro não bloqueia a coleta de dados no primeiro incremento.
- Fotos de embalagens, cadastro compartilhado entre confeitarias, preços coletados na internet, consulta de disponibilidade, marketplace, pedidos automáticos e emissão fiscal ficam fora desta proposta.
- QR Code/XML são canais previstos no PRD original; adicioná-los não é requisito deste incremento por fotografia. A guarda da foto integral e sua política de retenção ficam para decisão específica; histórico não depende de guardar a imagem para sempre.

## Passagem para especificação

Referência: PRD, extensão Compras revisão 2 de 07/10/2026. Seleção aceita: CMP-01, seguido de CMP-02 e CMP-03 como primeiro incremento integrado; CMP-04 permanece futuro. [Especificações, contratos e plano](compras/README.md) detalham os vínculos, compras, conversões por embalagem e compatibilidade com WhatsApp. Publicação de tickets, commit, migration de produção e deploy permanecem ações separadas.
