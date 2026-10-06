# Contratos — FT-01 e próximos fluxos

## Evolução implementada

Ficha aceita `composicao_ativa` (default false). Passos aceitam `receita_base_id` ou `ingrediente_id`, nunca ambos. No modo ativo, todos os passos exigem referência válida do tenant; embalagem deve corresponder ao tipo do material. Códigos de resposta de unidade/ciclo/referência inválida: 422. Escritas no grafo serializadas por tenant. Remover componente em uso retorna 409.

`GET /receitas/{id}/consumo-composicao` devolve materiais/bases consolidados por fornada, com nome, ID, unidade do estoque e quantidade decimal. Ficha descreve uma unidade de rendimento; consumo por fornada multiplica pelo rendimento da receita.

Ordens novas devolvem `ficha_snapshot`: instruções/revisão, nome, rendimento/unidade e consumo agregado congelados. Planejado continua sendo número de fornadas; produzido é quantidade final na unidade de rendimento. Estoque pronto guarda saldo físico e reserva; API de saldo apresenta quantidade livre e reserva separadamente. Venda/pedido não pode consumir a parte reservada. O snapshot não reconstrói ordens históricas já em execução.

Auth implementado em `/auth/whatsapp`: disponibilidade, solicitar, verificar, entrar, cadastro e vincular. Verificar retorna prova opaca curta; entrar consome a prova e retorna tokens ou nova prova para onboarding; cadastro consome a prova para criar conta; vincular exige sessão autenticada. Prova/OTP não é logada. Telefone em usuarios é E.164, nullable e único; endereço da loja está no tenant. Migrações geradas: 756dcb38fc17 e a42f344c4565, além da ficha original.

As seções seguintes registram o contrato editorial original e a intenção dos fluxos que foram concretizados nesta continuação.

## Ficha editorial implementada

GET `/api/v1/receitas/{id}/ficha-tecnica`: autenticado, restrito ao tenant e receitas ativas. Receita sem ficha retorna descrição vazia, passos vazios, revisão 0; receita inexistente ou de outro tenant retorna 404.

PUT no mesmo caminho: `descricao_produto` (1–2000 caracteres), `especificacao_final` (até 1000), `revisao` inteiro não negativo e `passos` (1–100).

Cada passo: `descricao`, `tipo` (componente/ingrediente/embalagem/acabamento), `quantidade` decimal positivo com até 4 casas, `unidade` (g/kg/ml/l/un), `quantidade_minima` e `quantidade_maxima` opcionais em par, `especificacao`, `instrucao`. O nominal deve estar dentro da faixa. Decimais são serializados como strings. A ordem do array é a ordem de montagem.

Gravação compara revisão atomicamente. Sucesso incrementa revisão e retorna documento; revisão desatualizada retorna 409; payload inválido 422. Não altera estoque nem custo. JSONB nullable + revisão default 0 em receitas preservam cadastros anteriores. Não há histórico de versões nesta fatia, somente controle de concorrência. Migração Alembic gerada: eb1a9dcd61f4; remoções de índices não relacionados detectadas pelo autogenerate foram descartadas.

## Contratos planejados (não expostos ainda)

Solicitar código recebe telefone E.164 e devolve identificador opaco do desafio e tempo de reenvio. Verificar recebe desafio/código; prova curta de onboarding para telefone novo ou sessão para conta existente. Concluir onboarding exige prova verificada de uso único e dados cadastrais. Senha/e-mail não devem ser trocados por telefone sem comprovação da titularidade da conta atual.

O armazenamento OTP deve usar hash autenticado com segredo servidor, expiração e consumo atômico. Não persistir código em texto claro. Limites e tentativas permanecem funcionais entre processos. Falha de envio invalida o desafio e devolve erro genérico recuperável.
