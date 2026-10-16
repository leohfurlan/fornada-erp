# Ticket 03 — Leitura e navegação por voz

Implementação local do incremento de leitura, retomada e navegação por voz. A Echo mantém a conversa aberta para comandos de leitura; o Chrome continua recebendo a revisão da mesma estação.

## Comandos

O modelo pt-BR agora inclui `ShowIngredientsIntent`, `ShowPreparationIntent`, `ShowAssemblyIntent`, `NextStepIntent`, `PreviousStepIntent`, `RepeatContentIntent` e `ContinueReadingIntent`. A primeira solicitação de uma seção seleciona o primeiro bloco e fala a primeira parte. Avançar/voltar muda um bloco cadastrado, repetir fala a parte atual sem mover o cursor e continuar move somente a parte de fala. Uma nova sessão retoma a receita e posição persistidas.

## Conteúdo e segurança

`backend/domain/cozinha/speech.py` prepara trechos determinísticos em PlainText, preserva nomes/quantidades/unidades, agrupa itens sem consolidar quantidades e divide conteúdo longo em partes limitadas. Markdown de link mantém o rótulo, URLs e marcação são retirados, e nenhum texto cadastrado é enviado como SSML executável. A montagem e o preparo seguem os blocos já produzidos pela projeção operacional; etapas de tempo não viram instruções.

A estação persiste `parte_fala_indice` junto de seção/bloco/revisão, compartilhado entre voz e navegador. Cada request Alexa revalida a versão da receita antes de reutilizar conteúdo; ao detectar alteração ou remoção, limpa a projeção e interrompe a leitura.

## Verificação e pendências

Ruff, compilação sintática Python, TypeScript, geração OpenAPI, JSON de intents e SQL offline da cadeia Alembic passaram. Cinco testes unitários cobrem quantidades/unidades, divisão sem truncamento, limpeza de Markdown/URLs, token longo e seleção de bloco. Testes de rota/estado com banco e aceitação real com Echo Dot 3 continuam pendentes; o SDK de validação Alexa ainda depende de instalação do lock e a conta/skill de desenvolvimento não foi configurada. A migration não foi aplicada a banco, e não houve deploy ou publicação.
