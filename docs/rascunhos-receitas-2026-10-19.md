# Rascunhos de receitas e fichas técnicas

Receitas novas, edição de receitas e fichas técnicas salvam alterações imediatamente no armazenamento local do navegador, sem exigir que campos obrigatórios estejam completos ou que haja conexão com a API.

Ao voltar ao mesmo formulário, o rascunho é recuperado automaticamente com um aviso. Ingredientes, etapas, ordem de montagem, quantidades, vínculos e Markdown são preservados. A versão/revisão original também é mantida, para que a API continue detectando conflitos com alterações feitas por outra pessoa.

Links para sair da página, Cancelar, Sair da conta e voltar do dispositivo oferecem:

- Salvar rascunho e sair;
- Continuar editando;
- Descartar e sair.

Ao recarregar/fechar a aba, o navegador pode exibir sua confirmação padrão. No encerramento do app pelo sistema operacional não se pode depender de uma confirmação ou de eventos de fechamento: a proteção é a gravação síncrona durante cada alteração. `pagehide` e mudança de visibilidade reforçam a persistência.

Cada rascunho é separado por tenant, usuário, tipo de formulário e ID da receita. O rascunho de receita nova usa uma chave própria. Salvar definitivamente remove o rascunho apenas após sucesso da API; erros mantêm o conteúdo recuperável. Alterações feitas enquanto uma requisição está em andamento continuam protegidas. Falhas no armazenamento mostram um aviso e impedem confirmar “Salvar rascunho e sair”.

Os rascunhos ficam neste dispositivo e neste navegador; não são sincronizados entre aparelhos. Limpar os dados do navegador também remove os rascunhos. Não há alteração no banco ou nas regras de custo/publicação das receitas.

Validação automatizada: `cd frontend`, `npx vitest run` e `npx tsc --noEmit`. Testes de regressão em `tests/rascunho.test.tsx` e `tests/ficha-tecnica.test.tsx` cobrem recuperação após desmontagem, listas dinâmicas, Markdown, revisão, confirmação, descarte, logout, voltar/recarregar, isolamento e falhas de armazenamento/API.

## Preparação para produção

Release isolada sobre `53a6a11`, preservando os fontes e a imagem de produção do checklist de cozinha. Somente o frontend é atualizado; backend, workers, banco, Redis e proxy permanecem nas versões ativas.

- Checkout de desenvolvimento: 156 testes frontend aprovados e TypeScript aprovado.
- Imagem Linux exata da release: 147 testes frontend aprovados (28 arquivos), TypeScript e `next build` aprovados. Os fontes de produção possuem um conjunto de testes diferente do workspace de desenvolvimento.
- Navegador Chromium em 390 × 844: confirmação ao cancelar e ao voltar pelo navegador, continuar editando, salvar e sair, recuperação da receita após reabrir/recarregar, confirmação de logout, descarte e recuperação da ficha técnica com revisão original. API simulada em prévia local, sem dados de cliente.
- Backend do checkout isolado: 519 testes aprovados, 4 ignorados por ausência de Redis de testes e 2 falhas preexistentes em `test_integral_snapshot_has_no_costs_and_includes_components` e `test_assembly_material_links_are_resolved_in_same_snapshot`, já registradas na publicação anterior. Banco PostgreSQL local exclusivo de testes; nenhum arquivo backend faz parte desta alteração.
- ESLint não tem configuração no projeto; nenhuma configuração adicional foi introduzida.

O deploy registra imagem anterior, arquivos Compose ativos, hashes do pacote e validação HTTPS, com rollback restrito ao frontend em caso de falha.
