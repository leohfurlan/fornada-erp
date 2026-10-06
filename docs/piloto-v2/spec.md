# Especificação — revisão do piloto (06/10/2026)

Status: primeira implementação local de UX-01, FT-01/02/03/04 e AUTH-01/02/03; envio real Evolution e recuperação autônoma pendentes. Nenhum deploy nesta rodada. Situação detalhada em plan.md.

## Avaliação do PRD

O PRD original cobre receitas, ingredientes, preparo, custos e produção, mas não distingue preparo de uma receita-base da montagem de um produto vendável. WhatsApp aparece como integração futura, sem autenticação por código. A entrada em Início, boas-vindas e tutorial não têm critérios de aceite. Esta revisão acrescenta requisitos sem substituir as regras anteriores.

## Modelo aprovado pelo usuário

Receita-base representa massa, recheio ou brownie reutilizável. Produto representa o item vendido, com descrição, apresentação e ficha de montagem por unidade. Uma etapa consome receita-base, ingrediente direto, embalagem ou acabamento. O mesmo componente pode aparecer várias vezes: as linhas não devem ser agrupadas na apresentação. A consolidação para custos/estoque soma quantidades compatíveis posteriormente.

A ficha é vinculada à receita existente. Com composição desativada, mantém o modo editorial sem efeito nos custos. Com composição ativa, cada etapa exige ID de receita-base ou material; custos e consumo passam a usar a montagem, substituindo a lista tradicional de ingredientes. A API distingue receita-base/produto pela composição ativa, sem duplicar cadastro nem usar descrição livre como identidade de estoque.

## Requisitos e aceite

| ID novo | Requisito | Aceite |
|---|---|---|
| UX-01 | Entrada e tutorial | Novo cadastro abre boas-vindas, com guia estoque → receita → produção → venda e botão Início; guia reabrível em Início; ações dizem Nova Produção |
| AUTH-01 | Número internacional | País/região e máscara específica; BR aceita celular com DDD e nove dígitos; persistir E.164 completo, sem retirar o nono dígito |
| AUTH-02 | Código WhatsApp | Código gerado pelo ERP, uso único, expiração 5 min, até 5 tentativas, reenvio após 60 s, limites por telefone/IP; respostas não revelam existência de conta; nenhum código/chave em logs |
| AUTH-03 | Onboarding após validação | Nome, confeitaria/loja, endereço estruturado e e-mail; número verificado identifica login; impedir duplicação de conta; definir migração segura dos usuários atuais |
| FT-01 | Ficha editorial | Descrição, apresentação, etapas ordenadas, tipo, quantidade nominal, unidade, faixa opcional, dimensões e instrução; tenant isolado; revisão concorrente rejeitada com 409 |
| FT-02 | Composição reutilizável | Referências a receitas-base e ingredientes/embalagens; rendimento e unidades compatíveis; referências devem pertencer ao tenant; impedir ciclos e dependências apagadas |
| FT-03 | Custo determinístico | Somar consumo das camadas repetidas; custo proporcional ao rendimento da base; embalagem/acabamento entram no custo; perdas explícitas; sem conversão massa-volume sem densidade definida |
| FT-04 | Produção reproduzível | Copiar revisão da ficha para a produção; mudanças futuras não alteram execução histórica; definir modo de consumo de estoque da base versus ingredientes sem dupla baixa |

Esses IDs são novos para a revisão; não renumeram o catálogo antigo.

## Exemplos e limites

Bolo: tabuleiro 1 un com medidas; três camadas de massa com faixa 200–250 g cada. O operador define o nominal de cada camada (não presumir 225 g); recheios brigadeiro/ninho 100 g cada; chantilly azul 200 g; topper, pétalas e fitilhos precisam de quantidade/unidade próprias. Sem as medidas e quantidades restantes, a ficha fica incompleta para custo.

Sedução: copo 1 un, capacidade 300 ml; Nutella 40 g; morango 25 g; brigadeiro 30 g; brownie 50 g; brigadeiro 30 g; morango 25 g; chantilly 30 g; tampa 1 un; adesivo 1 un. Conteúdo nominal soma 230 g, morango 50 g e brigadeiro 60 g. Capacidade 300 ml não equivale a 300 g. A ordem original é preservada.

## Evolution API

Escolha indicada pelo usuário: Evolution API. O ERP gera e verifica os códigos; Evolution apenas transporta mensagem. Adaptador backend configurável por URL, instância e segredo, com timeout e tratamento de falha. A API key nunca chega ao navegador. Confirmar versão/contrato da instância antes de implementar o envio, pois payloads variam por versão. Não instalar esse serviço na Micro de 1 GB sem dimensionamento. Recebimento de aceite HTTP não comprova entrega ao destinatário.

Pendências: endereço/versão da instância, conexão WhatsApp e credencial; recuperação autônoma de conta e teste real de entrega. Vinculação segura de contas antigas está implementada: sessão atual autenticada + prova de posse do telefone. Desafios/provas expiram em Redis. Login atual continua disponível.
