# F-COZ-01 — Plano de entrega

Revisão 3, 16/10/2026. [PRD](../../../prd.md), [spec](spec.md), [contrato r3](contract.md). Escopo/ID e quatro entregas aprovados na conversa. HEAD base `44835810044c912413f6dddd11a5c549a69bc791`. As quatro fatias têm implementação local; gates de integração e aceite real continuam pendentes. O contrato registra os refinamentos aplicados.

## Sequência e checkpoints

1. **Modo cozinha por toque — implementada localmente; aceite pendente.** O fluxo autenticado, estações, busca/abertura, projeção e navegação foram adicionados com persistência, lease/revisões/ACK e controles acessíveis. Ainda falta executar os testes de isolamento/CAS/ACK e validar a interface no Mac alvo. Não depende de conta Amazon. Ticket [01](../../../.scratch/modo-cozinha-alexa/issues/01-modo-cozinha-toque.md).
2. **Vinculação Alexa e abrir receitas por voz — implementada localmente; integração externa pendente.** OAuth authorization-code com PKCE opcional, consentimento, token restrito, skill pt-BR, vínculo de Echo/estação e endpoint assinado implementados; busca/desambiguação direciona a receita à tela. A checagem criptográfica está integrada ao ASK SDK fixado, mas não foi exercitada com solicitação Amazon real. Faltam instalar dependências do lock e configurar/testar credenciais, HTTPS público e skill de desenvolvimento. Ticket [02](../../../.scratch/modo-cozinha-alexa/issues/02-alexa-abrir-receitas.md).
3. **Ingredientes e etapas por voz — implementada localmente; aceite pendente.** Leitura em partes, seleção de ingredientes/preparo/montagem, navegação por blocos, repetir/continuar e retomada persistida estão conectados à mesma estação da tela. Cursor de fala em migration aditiva. Ainda falta executar testes de estado/idempotência e validar conteúdo com uma receita real na Echo. Ticket [03](../../../.scratch/modo-cozinha-alexa/issues/03-leitura-navegacao-voz.md).
4. **Retomada e reconexão — implementadas localmente; aceite real pendente.** Refresh/reabertura exige retomada explícita; a tela pausa comandos em segundo plano, offline ou quando não confirma estado/heartbeat, refaz heartbeat ao voltar e rejeita respostas de polling fora de ordem. `ALEXA_ENABLED` é opt-in e há roteiro de rollback. Testes com banco, Amazon, Mac e Echo seguem pendentes. [04](../../../.scratch/modo-cozinha-alexa/issues/04-retomada-aceite-real.md).

Não há paralelismo de implementação autorizado. Cada fatia é um caminho demonstrável pelas camadas relevantes; não criar tickets isolados “só backend”/“só frontend”. A fatia 1 já implementa persistência e fronteiras básicas; 4 verifica resiliência completa e integração real.

## Dependências externas e execução

- Confirmar versão exata do Chrome no Mac; funcionamento atual é relato do usuário. Não trocar navegador ou sistema operacional como pré-requisito presumido.
- Conta Amazon Developer e Echo na mesma conta de desenvolvimento, ou beta autorizado; idioma pt-BR. Nome de invocação “Fornada” depende de validação no console. Não é necessário publicar na loja para testar em development.
- Credenciais/client OAuth/skill ID/redirect URIs oficiais, hostname HTTPS e certificado válido. Configurar em ambiente de piloto isolado; nunca expor servidor local na internet sem desenho/configuração revisados. Aproveitar infraestrutura existente após autorização de publicação do piloto.
- Enquanto Amazon indisponível, desenvolvimento local e conformance HTTP seguem, mas ticket 2 não pode ser declarado integrado só com mocks. Sem acesso físico, ticket 4 permanece aguardando aceite do usuário.
- Migração local/teste via Alembic em banco exclusivo. Antes de produção: backup verificável e restauração em banco temporário, revisão de head/migration e aprovação explícita de deploy/migração. Nada disso é executado por esta spec.
- Implementar em checkout isolado se necessário, preservando alterações locais existentes. Sem commit/push/publicação nesta entrega documental.

## Roteiro de aceite no equipamento real

1. Registrar Chrome exato, macOS 10.13.6, modelo Echo Dot 3, idioma e data. Abrir Fornada, logar na conta correta, ativar modo cozinha, parear e confirmar estação na interface.
2. Com receita de teste cadastrada, buscar por voz: nome único, ambíguo e inexistente. Conferir título/ingredientes no Mac e recibo/ACK no backend; fala sem ACK não pode alegar exibição.
3. Ouvir ingredientes completos por partes; mostrar preparo/montagem e avançar/voltar/repetir. Confrontar cada quantidade/unidade com cadastro. Testar receita sem preparo e texto longo.
4. Deixar sessão Alexa encerrar, invocar novamente e conferir mesma receita/posição. Recarregar Chrome; depois fechar e reabrir aba/reativar estação. Sem execução dupla ou comandos antigos.
5. Desconectar rede e suspender Mac; tentar comando. Conferir orientação de abrir tela, ausência de confirmação falsa e recuperação ao retornar. Testar duas abas, logout e revogação de vínculo.
6. Repetir busca, leitura e avanço com a batedeira na condição habitual de trabalho e à distância usual da Echo. Registrar tentativas, frases reconhecidas, falhas e resultado visual. Usuária deve completar o fluxo sem toque; se não conseguir, ajustar frases/posição da Echo e repetir antes do aceite.

Metas de latência/carga ainda não são SLA aprovado. Registrar tempo comando→revisão e revisão→ACK com aba visível, uma Echo/estação, rede e volume de receitas conhecidos; propor limite com base na medição. Não declarar “tempo real” sem evidência.

## Definição de concluído

- Especificação: escopo/ID/aceites, fronteiras e quatro fatias documentados; links e whitespace conferidos. **Esta entrega documental não prova implementação.**
- Implementação local: AC1–AC7 e casos E01–E16 cobertos conforme spec, migrations isoladas, testes/tipos obrigatórios e revisão de isolamento aprovados, sem regressões em consultas existentes.
- Integração piloto: account linking e webhook reais mais AC8 no Mac/Echo, evidência visual/voz e ruído, configuração opt-in revogável. Simulador não encerra esse checkpoint.
- Deploy/loja: etapas posteriores com autorização própria; não decorrem de aprovar spec ou tickets.

## Tickets e publicação

Skill `to-tickets` aplicada após `to-specs`. Quatro fatias e dependências aprovadas pelo usuário em 16/10/2026. Arquivos locais em `.scratch/modo-cozinha-alexa/issues/`, um por ticket, com status pronto para a fronteira indicada e gates externos explícitos. `.scratch` é área de entrega local e pode ser ignorada pelo Git; este plano versionável preserva a sequência e os critérios principais.

Não foi identificado tracker/labels configurados para esta feature; nenhum issue externo criado. Para configurar publicação externa, usar `/setup-matt-pocock-skills`; isso não impede a entrega dos arquivos locais. Falta de credenciais/recursos externos não é aprovação implícita de provisionamento.

## Estado de implementação local

Em 16/10/2026: fatias 1–4 implementadas no working tree. TypeScript e `py_compile` passaram; 9 testes focados passaram no virtualenv Python 3.12; Ruff passou nos novos testes e no módulo de fala. A cadeia Alembic tem um head (`c7e5f2a901bd`), SQL offline foi gerado e todas as migrations foram aplicadas com sucesso a um PostgreSQL temporário sem volume, depois removido. Um teste novo de integração da estação, junto dos 9 testes focados, passou (10 passed): retomada/takeover, rejeição da lease antiga, revisão recuperada e ACK futuro/atrasado. A suíte completa, executada antes de adicionar esse teste, terminou com 479 passed, 4 skipped e 2 falhas nos testes existentes `test_integral_snapshot_has_no_costs_and_includes_components` e `test_assembly_material_links_are_resolved_in_same_snapshot`, ambos em receitas da Central; não foram alterados neste ticket e não há baseline confirmado. O Ruff do arquivo de configuração ainda aponta duas linhas longas em código fora do diff deste ticket. `git diff --check` passou com avisos de conversão LF/CRLF. Ainda faltam testes concorrentes em navegador, build, navegador real, Echo real e integração OAuth com Amazon. Nenhum commit, push, deploy ou configuração Amazon foi realizado.
