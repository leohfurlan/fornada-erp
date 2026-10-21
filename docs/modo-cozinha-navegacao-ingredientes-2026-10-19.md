# Modo Cozinha: navegação e conferência de ingredientes

## Comportamento

O rodapé percorre as seções disponíveis: Ingredientes, Modo de preparo e Montagem. O preparo é uma visão conjunta do texto e das etapas; montagem com vários blocos mantém os controles entre montagens. Seções ausentes são ignoradas. A navegação fica no fluxo normal, com espaçamento acima da barra inferior do aplicativo, sem sobrepor instruções.

Ao abrir uma receita por resultado da busca ou OP, os resultados são fechados, o termo é limpo e a fila de OPs se recolhe. O foco e a rolagem vão para o cabeçalho Receita aberta, com margem para o cabeçalho fixo. Reabrir a mesma receita também realiza esse comportamento. Falhas de abertura mantêm os resultados para nova tentativa. Navegar entre seções leva a leitura de volta ao cabeçalho. Movimento reduzido desativa a rolagem suave.

Cada ingrediente é um botão amplo com nome e quantidade, círculo/check de sucesso e texto riscado após conferência. A quantidade permanece legível. O toque é reversível, independente e otimista, com proteção contra duplicação e reversão em falha. Conferir ingrediente não movimenta estoque nem altera a receita ou o progresso das etapas.

## Persistência e compatibilidade

checked_ingredient_ids é salvo na projeção JSON da estação já existente, por usuário, receita, versão e sessão. O novo comando set_ingredient_checked reutiliza lease, CAS e recibos idempotentes. A retomada por toque ou Alexa conserva a conferência se a receita e a versão forem iguais. Alterações na receita invalidam a projeção antes de aplicar marcações.

IDs ingredient-N são posições da lista ordenada dentro da versão imutável da receita. Projeções antigas sem IDs continuam funcionando sem migração. Reiniciar etapas preserva a conferência dos ingredientes e limpa somente a conclusão das etapas, conforme a ação exibida. Abrir outra receita inicia uma sessão independente. Não há alteração de schema, nova dependência ou mudança de comandos Alexa.

## Validação

163 testes do frontend e 25 testes backend focados passaram, incluindo integração PostgreSQL isolada: marcação, desmarcação, recuperação depois de pausar e renovar lease, reabertura, isolamento, comando inválido e ausência de alteração de estoque. TypeScript e build Next aprovados. Fluxo visual validado em navegador com dados sintéticos, incluindo lista longa de ingredientes, foco ao abrir receita e passagem para preparo/montagem.

A publicação usa imagens incrementais sobre as bases ativas, backup de banco verificado, preservação de ambiente e rollback. Não executa migrações nem testes que alterem dados reais.
