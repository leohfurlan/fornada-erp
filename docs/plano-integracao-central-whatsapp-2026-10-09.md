# Avaliação e plano de integração da central WhatsApp

Data: 09/10/2026. Este documento reúne o plano aprovado e as evidências da avaliação inicial. A implementação local posterior está descrita abaixo; migrations foram executadas somente em bancos temporários.

## Situação após implementação local

INT-01 a INT-06 implementadas e verificadas localmente: serviço compatível com as mudanças existentes, merge Alembic `a85c10b7d302`, acesso por usuário/tenant, revisão humana com OCR desligado e ensaio HTTP real entre os projetos. INT-07 tem configuração desativada, imagem testada, lock de dependências Python e runbook preparados; infraestrutura real, segredos e backup/restauração da implantação permanecem para publicação autorizada. INT-08 depende de homologação Evolution/Baileys e piloto autorizado.

Consulte o [contrato e runbook](central-whatsapp-contrato-v1.md) e o [relatório de implementação](central-whatsapp-implementacao-2026-10-09.md). As seções de evidências e conclusão da avaliação inicial abaixo descrevem o estado anterior à implementação; não são instrução para reaplicar o patch antigo.

Revisão do plano: integração com o app [whatsapp-admin](https://github.com/leohfurlan/whatsapp-admin), conforme alinhamento entre os projetos. Fonte técnica consultada: checkout local `C:/Projetos TI/whatsapp-admin`, incluindo `backend/app/fornada_adapter.py`, `domain.py`, `software_contracts.py`, `authorization.py` e `purchases.py`. O acesso web ao GitHub não retornou o conteúdo nesta revisão; não se presume que o checkout e o remoto estejam sincronizados.

## Objetivo e definição de acesso

Permitir que uma usuária já vinculada à Fornada envie um cupom pelo WhatsApp comercial gerenciado pela central, tenha a compra revisada por um operador e aprove uma versão específica antes da entrada no estoque. A central acessa a API privada da Fornada em nome da usuária identificada; a Fornada permanece responsável pelos dados, validações e efeitos comerciais.

Há três identidades distintas: o operador autenticado da central, o serviço central autenticado pelo token dedicado e a usuária Fornada identificada pelo telefone verificado da conversa. Login do operador e posse do token não concedem autorização comercial em nome de qualquer cliente. O vínculo negócio→tenant e a identidade atual da usuária precisam ser validados em cada operação.

Neste piloto, acesso significa operação por API a partir da conversa. O patch não implementa SSO, login no navegador da Fornada pelo painel da central, compartilhamento de sessão ou criação automática de usuários. O acesso web continua pelo login existente da Fornada. Caso seja necessário abrir o ERP autenticado a partir da central, isso exige uma entrega própria com contrato de delegação, expiração, consumo único e auditoria; não transportar senha, JWT ou sessão por mensagem ou URL.

## Contrato entre os projetos

| Responsabilidade | whatsapp-admin | Fornada |
|---|---|---|
| Conversa e remetente | Validar evento/instância, resolver telefone verificado e controlar delegação/assunção humana. | Conferir que o telefone corresponde à usuária ativa no tenant concedido. |
| Acesso | Autenticar operador, limitar negócios/capacidades e auditar a solicitação. | Autenticar serviço, resolver identidade/escopo atuais e negar recursos de outro tenant/usuário. |
| Revisão | Exibir cupom, catálogo e pendências; salvar revisão sem enviar ou executar automaticamente. | Validar materiais, produtos, conversões, valores e prévia comercial. |
| Aprovação | Enviar resumo e receber `APROVAR <codigo> <versao>` ou recusa na conversa correta. | Vincular decisão à proposta, usuária, versão e hash; revalidar prévia. |
| Execução | Persistir tentativa antes da chamada e tratar resultado incerto por consulta. | Registrar compra/estoque e resultado atomicamente, com idempotência. |
| Operação | Supervisionar API e workers, intervenções e outbox. | Supervisionar API, banco, OCR opcional e integridade comercial. |

As capacidades efetivas iniciais são `purchases.review` e `stock.receive`. `orders.read` e `production.update` existem no registro de contratos da central, mas o adapter Fornada atual não as declara nem implementa. `agenda.read` está registrado para Moriah; não reutilizá-lo como capacidade Fornada. Ampliar acesso requer contrato explícito e implementação nos dois lados.

O serviço proposto oferece POSTs sob `/api/v1/central`: `resolve`, `extract`, `draft`, `catalog`, `review`, `decision`, `approval`, `execute` e `reconcile`. Documentar schemas, estados, limites, erros e exemplos sanitizados em um contrato versionado comum. Os dois registries, schemas e o cálculo de digest precisam permanecer compatíveis. Aprovação e execução não podem aceitar dados comerciais livres que contornem a proposta revisada.

## Entregas e dependências de desenvolvimento

| Entrega | Projeto responsável | Resultado obrigatório |
|---|---|---|
| INT-01 Base compatível | Fornada | Checkout isolado com mudanças atuais preservadas, dependências mínimas identificadas e diff revisável do serviço. |
| INT-02 Banco | Fornada | Grafo Alembic único, upgrade de banco vazio e de snapshot de teste com iFood, ensaio de reversão aplicável e preservação dos dados. |
| INT-03 Identidade e permissões | Ambos | Negócio→tenant explícito, telefone E.164, usuária ativa, recursos próprios e revalidação após revogação. Definir se todos os usuários ativos do tenant podem receber estoque; se não, implementar concessão por usuária/capacidade na Fornada antes de ativar. |
| INT-04 Fluxo humano | Ambos | Imagem sem OCR utilizável abre revisão, operador prepara itens manualmente, cliente aprova e recebe referência real da compra. |
| INT-05 Contrato HTTP | Ambos | Contrato versionado, erros distinguíveis de negócio/conflito/indisponibilidade e testes com aplicações reais em processos separados. |
| INT-06 Resiliência | Ambos | Concorrência, revogação, resposta perdida depois de commit, tomada humana e restauração cobertas por evidência. |
| INT-07 Publicação preparada | Ambos | Configuração desativada, imagens reproduzíveis, health checks, workers supervisionados, backups/restauração e runbook de desativação. |
| INT-08 Transporte e piloto | Ambos | Homologação Evolution/Baileys e ativação controlada por negócio e número comercial. |

Sequência: INT-01 → INT-02 → INT-03/INT-04 → INT-05 → INT-06 → INT-07 → INT-08. Não avançar para publicação antes de validar os serviços juntos e os cenários de falha.

## Conclusão

A arquitetura é adequada para um piloto de compras: a central controla conversas, revisão e transporte; a Fornada autentica o serviço, resolve o usuário/tenant e executa o motor comercial. O patch ainda não está pronto para aplicação direta neste checkout. Não equivale a uma integração completa de agenda, pedidos, produção ou iFood.

## Evidências atuais

- `git apply --check` falha em `backend/alembic/env.py`, `backend/core/config.py` e `backend/main.py`. Esses arquivos têm alterações locais, inclusive iFood; preservá-las é requisito.
- HEAD local: `de5b668`. Base declarada do patch: `f15604d40951a4eea06f8dea2d5f75b9ea2a2346`. O objeto da base existe no repositório, mas não se deve confundir a base do pacote com o estado atual do checkout ou da produção.
- O patch importa `infrastructure.ocr.hybrid.HybridReceiptExtractor`. `backend/infrastructure/ocr/hybrid.py` não existe neste checkout e não está no patch. A comparação HEAD→base também inclui `domain/compras/extraction.py`, alterações em reconhecimento/schemas e outros adapters. É necessário selecionar a cadeia mínima de dependências ou integrar a evolução de OCR já existente antes do serviço central.
- A migration proposta `73a5fcee0651` e o ramo iFood descendem de `0f6af4c60f80`; no checkout o ramo iFood termina em `f3197cd42901`. A inclusão literal produziria duas heads. Confirmar revisões efetivamente aplicadas antes de decidir entre reparentear uma migration inédita e adicionar uma merge revision.
- O teste novo da Fornada é um único cenário integrado amplo: autenticação, escopo inválido, extração repetida, revisão sem movimento, aprovação, execução repetida e reconciliação. Não demonstra sozinho concorrência real, revogação durante operação ou falha entre commits/respostas.
- O relatório da central declara 200 testes completos em uma rodada e testes direcionados posteriores; declara também que a suíte completa não foi repetida depois dos ajustes finais. Esses resultados são históricos do relatório, não testes reexecutados nesta avaliação.
- O OCR híbrido da worktree invoca `tesseract -l por`; seu parser local não extrai loja/data. A preparação automática exige fornecedor identificado. Portanto, a automação completa de cupons pode permanecer indisponível mesmo com leitura de itens correta. A imagem de desenvolvimento atual instala gcc, sem Tesseract; conferir e preparar especialmente a imagem de produção.

## O que preservar

Token dedicado, grant negócio→tenant, consulta atual de usuário ativo e exclusão de superusuário de suporte. Revisão com versão/hash e aprovação por código/versão. Execução comercial e resultado da proposta na mesma transação externa: o motor comercial declara que o chamador faz o commit. Sem repetição automática de lançamentos incertos; reconciliar consultivamente. Nenhum fallback de cupom para IA pública.

O token de serviço é uma fronteira de confiança: a Fornada confia na central para informar telefone e mensagem recebida. O identificador da mensagem é correlação, não uma assinatura independente do WhatsApp. Documentar essa responsabilidade e proteger o transporte e as credenciais.

## Plano de desenvolvimento

| Etapa | Trabalho | Critério de aceite |
|---|---|---|
| 1. Base e dependências | Identificar a versão a promover, preservar alterações locais/iFood, desenvolver em checkout isolado e incorporar o mínimo de OCR/contratos exigido pelo patch. | Imports e contratos compatíveis, mudanças revisáveis e nenhum arquivo existente perdido. |
| 2. Serviço Fornada | Integrar as oito alterações manualmente onde necessário; registrar modelo/rotas e validação de configuração; unificar Alembic; atualizar exemplos de produção e passagem de variáveis no deploy. | Uma head, upgrade em banco temporário, serviço desligado por padrão e autenticação/isolamento funcionando. |
| 3. Revisão humana e OCR opcional | Fazer o piloto funcionar com OCR desligado: cupom disponível ao operador, itens e vínculos preenchidos manualmente, prévia e resumo. Incorporar módulos necessários para imports mesmo com OCR desligado. Se habilitar leitura local, instalar Tesseract/idioma português na imagem usada. Harmonizar limite de imagem de 8 MiB com a central, que admite mídia de até 20 MiB; verificar limite de resposta de 1 MiB do adapter e catálogo sem paginação. | Compra completa com revisão humana e OCR indisponível; nenhum dado enviado a IA pública. |
| 4. Teste entre aplicações | Rodar central e Fornada reais em ambiente isolado, via HTTP, com bancos de teste; repetir suites depois da integração final. | Fluxo extract→review→decision→approval→execute→reconcile comprovado entre os serviços, sem depender somente de mocks. |
| 5. Endurecimento | Cobrir concorrência, expiração, revogação, catálogo alterado, tomada humana, indisponibilidade e timeout; estabelecer consulta e resolução de propostas incertas/expiradas, retenção e logs sem conteúdo sensível. | Uma compra/entrada por operação; zero efeito sem aprovação; contexto obsoleto bloqueado; falha recuperável com evidência. |
| 6. Homologação do transporte | Confirmar versão/payload/mídia/header secreto da Evolution/Baileys, roteamento do webhook e único responsável pela conversa. Separar resposta conversacional dos envios de OTP e alertas iFood. | Número comercial controlado recebe, resume, aprova e confirma sem duas respostas concorrentes. |
| 7. Piloto e publicação | Preparar backup/restauração, migrations, segredos, grants, proxy HTTPS e supervisão dos workers; publicar desativado, validar, depois ativar negócio e delegação com data/hora explícita. | Piloto autorizado com referência real de compra, estoque conferido e caminho de desativação documentado. |

## Matriz mínima de homologação

1. Sem token, token incorreto, negócio não concedido, outro tenant, telefone sem vínculo e usuário desativado: negar sem efeito comercial.
2. Extração, revisão, recusa, resumo vencido e versão antiga: zero movimentações.
3. Aprovação válida: exatamente uma compra e a quantidade convertida esperada em estoque.
4. Repetição da mesma imagem, entrega duplicada da mensagem, execução concorrente e execução repetida: nenhum lançamento adicional.
5. Produto/conversão alterados após resumo, revogação e tomada humana: invalidar autorização/contexto pertinente.
6. Resposta perdida depois do commit: reconciliação encontra compra real sem reenviar lançamento. Falha antes do commit: nunca informar sucesso.
7. OCR ausente, imagem inválida/grande, catálogo truncado e resposta acima do limite: intervenção utilizável, sem sucesso fictício.
8. Restauração: propostas e autorizações não retomam execução automática.
9. Operador sem acesso ao negócio e usuária sem concessão comercial, quando exigida: negar mesmo com token de serviço válido.
10. Rodar duas requisições realmente concorrentes por HTTP com conexões de banco distintas; depois consultar banco e confirmar exatamente uma compra e um efeito de estoque.
11. Simular commit bem-sucedido seguido de perda da resposta entre Fornada e central; a central deve marcar incerteza e reconciliar a mesma operação, sem executar outra compra.
12. Desativar usuária/revogar concessão entre revisão, aprovação e execução; o próximo passo protegido deve ser negado. Documentar o ponto transacional a partir do qual uma operação já em andamento pode concluir, evitando prometer cancelamento retroativo.
13. Fluxo positivo sem Tesseract/OCR: imagem→intervenção→revisão manual→resumo→aprovação identificada→compra→confirmação.

## Configuração e operação

Fornada: `CENTRAL_ENABLED`, `CENTRAL_SERVICE_TOKEN`, `CENTRAL_BUSINESS_TENANTS`, `CENTRAL_LOCAL_OCR_ENABLED`. Central: `CENTRAL_FORNADA_CONNECTORS`, capacidades `purchases.review`/`stock.receive`, conformance e ativação com timezone. API e workers devem compartilhar a configuração correta. Central precisa de API, worker de mensagens e worker de agentes; worker de operações participa quando backup/exportação estiver habilitado.

Confirmar UUID do negócio, UUID do tenant, usuário e telefone E.164 antes do piloto. Não desligar globalmente Evolution sem avaliar OTP e alertas iFood: o objetivo é retirar a resposta concorrente à conversa de compras, preservando os fluxos autorizados.

## Ordem recomendada e escopo posterior

Primeiro concluir a integração HTTP e o piloto com revisão humana. Depois medir OCR com cupons autorizados e evoluir loja/data, layouts e paginação. Botões de aprovação e continuidade de agenda/pedidos/produção são entregas posteriores: o adapter atual retorna nenhuma próxima ação.

O primeiro marco de conclusão é INT-06: duas aplicações reais integradas em ambiente temporário, compras com revisão humana, identidade/permissões comprovadas e recuperação de falhas validada. O segundo marco é INT-08: piloto homologado no transporte real. Preparar a implementação não equivale a autorizar publicação, migration em produção, troca de webhook, envio real ou alteração de estoque real.

Ao preparar publicação, separar desativação do conector de rollback de banco. Desativar novas operações preserva compras já confirmadas e operações incertas para reconciliação; não apagar tabelas/propostas para desligar a integração. Compatibilizar OTP e alertas iFood antes da troca de responsável pela conversa.

A avaliação inicial não confirmou o estado da VPS nem homologação real Evolution/Baileys. A implementação posterior executou suites e ensaios locais, conforme relatório; produção e transporte real continuam sem alterações.
