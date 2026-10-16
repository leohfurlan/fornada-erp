# Registro de aceite do piloto F-COZ-01

Status em 16/10/2026: **aguardando validação presencial**. Os dados abaixo separam o que foi informado do que ainda precisa ser medido; nenhum resultado de voz ou tela foi simulado.

## Equipamentos e configuração a registrar

| Campo | Valor conhecido | Evidência pendente |
|---|---|---|
| Computador | MacBook Pro Mid 2010 | Confirmar identificação do modelo no equipamento |
| Sistema | macOS High Sierra 10.13.6 | Versão informada pelo usuário; conferir em Sobre Este Mac |
| Navegador | Google Chrome | Usuário confirmou que abriu o Fornada; registrar versão exata em `chrome://version` |
| Alexa | Echo Dot 3 | Modelo informado pelo usuário |
| Idioma da Echo/skill | Português do Brasil esperado | Confirmar idioma nos dois locais |
| Rede e posição | Conexão doméstica; posição de trabalho a registrar | Registrar distância da Echo, rede e condição da batedeira |
| Data e participante | A preencher no ensaio | Registrar nome/consentimento da confeiteira |

## Roteiro e resultado

Marcar cada cenário somente depois de executá-lo com a Echo e o Chrome. Registrar frase dita, texto ouvido, revisão/ACK visível e resultado; ocultar tokens, IDs Amazon e dados de clientes.

| Cenário | Resultado | Evidência/observação |
|---|---|---|
| Vincular conta, confirmar Echo e escolher estação | Pendente | — |
| Abrir receita com nome único e confirmar título na tela | Pendente | — |
| Busca ambígua, escolher número e abrir a opção correta | Pendente | — |
| Busca sem resultado; receita atual não é substituída | Pendente | — |
| Ler ingredientes em partes e conferir quantidade/unidade | Pendente | — |
| Mostrar preparo/montagem, avançar, voltar e repetir | Pendente | — |
| Continuar leitura e retomar posição após nova sessão Alexa | Pendente | — |
| Suspender e acordar Mac; retomar lease sem pular etapa | Pendente | — |
| Fechar/reabrir Chrome e recuperar estado persistido | Pendente | — |
| Internet indisponível; comandos pausados e conteúdo marcado possivelmente desatualizado | Pendente | — |
| Reiniciar API e retomar após recuperação do serviço | Pendente | — |
| Duas abas e takeover explícito; resposta antiga não regride a tela | Pendente | — |
| Logout, revogação, token vencido e usuário inativo | Pendente | — |
| Receita alterada/removida; leitura antiga interrompida | Pendente | — |
| Ruído habitual da cozinha; busca, leitura e avanço sem toque | Pendente | Registrar tentativas, frases reconhecidas e falhas |

## Opt-in e rollback

`ALEXA_ENABLED` é o kill switch de deployment e permanece `false` por padrão. A integração só fica ativa quando esse flag e a configuração completa da skill/OAuth estão válidos. Cada conta ainda exige consentimento OAuth; a Echo precisa ser confirmada na tela e associada a uma estação ativa.

Para interromper o piloto, definir `ALEXA_ENABLED=false` e reiniciar o serviço pelo processo operacional já aprovado. As rotas Alexa passam a responder indisponível; os dados e consentimentos ficam preservados para investigação. Para revogar uma conta, usar “Desvincular conta Alexa” na tela: isso revoga os grants OAuth ativos e remove o vínculo/dispositivo. Se houver incidente de credencial, desativar o flag e rotacionar o segredo OAuth antes de reabilitar.

As migrations da feature são aditivas. Não executar downgrade em um piloto que já contenha estações, grants ou recibos: a remoção das tabelas Alexa apagaria o vínculo e os recibos de auditoria. O rollback operacional é desligar a feature e preservar as tabelas; downgrade só cabe em banco descartável comprovadamente sem dados, após backup/restauração verificados. A cadeia foi aplicada em PostgreSQL temporário sem volume para validar a migração e o container foi removido em seguida. Nenhuma migration em banco persistente, ativação do flag ou publicação foi executada.
