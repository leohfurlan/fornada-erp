# Modo de preparo unificado

O Modo Cozinha apresenta o texto integral do modo de preparo no topo e as etapas cadastradas logo abaixo, na mesma seção. A aba separada Etapas foi removida; tanto a navegação interna em preparation quanto em steps apresenta essa visão conjunta. Um link ao final permite voltar ao início do modo de preparo.

O cabeçalho inteiro de cada card permite marcar/desmarcar a etapa, assim como o toque na área de instruções. O número muda para check, sem um controle de seleção pequeno separado. Links e demais controles internos continuam protegidos contra marcação incidental. O texto integral continua disponível para leitura e não é selecionável como conclusão.

A persistência por receita/sessão e a leitura Alexa usam os contratos existentes. Não houve alteração de backend, receita, ingredientes ou banco de dados.

Validação: testes de componente e página cobrem apresentação conjunta em preparation e steps, ordem do texto, cabeçalho amplo, progresso, reversão, recuperação e eventos internos. A publicação usa build Linux e preserva a versão ativa de receitas/rascunhos e os demais serviços.
