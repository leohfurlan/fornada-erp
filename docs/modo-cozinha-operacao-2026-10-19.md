# Modo Cozinha: programação, produção e entradas

## Entrega

- Resumo da agenda do dia e acessos rápidos a agenda, produção, pedidos e vendas, disponível antes de ativar a estação.
- OPs planejadas e em produção aparecem antes do catálogo de receitas. Filtro por nome ou número, sem distinção de acentos; prioridade por data prevista.
- Cada OP tem ações explícitas para abrir a receita, iniciar produção e finalizar com quantidade real produzida. Usa o hook e a máquina de estados existentes; início confirma reserva de materiais e finalização confirma consumo e entrada de produtos prontos. A sugestão de unidades é fornadas multiplicadas pelo rendimento.
- O checklist não altera automaticamente o status da OP e abrir a receita não inicia produção. A consulta da receita mantém o comportamento existente; ficha e quantidades da OP continuam acessíveis nos detalhes.
- Pedidos recebidos pelo monitor iFood e vendas registradas hoje nos canais WhatsApp/iFood são atualizados a cada 15 segundos. Pedidos de teste são identificados. O monitor mostra o último evento e a data recebida; não confirma pedidos nem cria OPs automaticamente.
- Ao abrir receita, os detalhes de programação e fila de OPs são recolhidos. O resumo mostra contadores de pedidos/vendas e permite reabrir a consulta sem sair do preparo.
- Instruções/configuração Alexa ficam ocultas quando conta, Echo e estação estão vinculadas. Gerenciamento permanece acessível por ação explícita. Falhas na consulta não simulam desconexão.

## Arquitetura

Apenas frontend, sem nova dependência, migration ou armazenamento. Reutiliza APIs autenticadas /agenda, /producao/ordens, /vendas, /integracoes/ifood/monitor e os comandos existentes da estação. Novas chaves TanStack Query incluem tenant, usuário e sessão de suporte. A mudança de status usa useMudarStatusOP e invalida agenda/resumo após resposta, inclusive quando há erro; bloqueia envio duplicado e preserva formulário após recusa.

## Limites

WhatsApp mostra vendas efetivamente registradas no Fornada. Não foi criada captura automática de vendas a partir de conversas. O iFood mantém o escopo/configuração e o histórico limitado do monitor existente. A data da agenda/vendas segue a data local do dispositivo e muda automaticamente na virada do dia. A integração Alexa continua com os comandos atuais; novos gatilhos de OP são por toque na tela.

## Verificação

159 testes do frontend passaram, incluindo priorização, busca, abertura da receita, início confirmado, bloqueio duplicado, quantidade em unidades, falha de finalização, isolamento de cache, chegada após atualização, indisponibilidade e Alexa configurada. TypeScript e build Next de produção aprovados. Playwright com APIs sintéticas: 390 × 844 e 1440 × 1000, início de OP, abertura de receita e ausência de overflow horizontal. Nenhum teste alterou OP, estoque, pedido ou venda reais.

Publicação incremental preserva a versão ativa ingredient-recipes-prod-6064927, rascunhos e checklist. Apenas o container frontend é substituído; backend e demais serviços permanecem intactos.
