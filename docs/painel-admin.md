# Painel administrativo do Fornada

Revisão: 1, 07/10/2026. Responsável pelas decisões: Leonardo.
Status: proposta de painel completo; base de superusuário publicada e conta criada em 07/10/2026. Evidências no [relatório da entrega](admin-entrega-2026-10-07.md).
Fonte canônica de produto: [PRD.md](../PRD.md). Este documento detalha a adição administrativa sem substituir os requisitos anteriores ou os contratos do piloto.

## Problema e resultado esperado

Hoje não existe papel administrativo da plataforma. Cada usuário pertence a um negócio (`tenant`) e os módulos consultam exclusivamente esse negócio. Cadastro, login e autenticação por WhatsApp não oferecem um diretório administrativo. Manutenção depende de scripts, SSH e Docker.

O operador precisa localizar uma conta, acessar o negócio para suporte e executar rotinas de gestão e manutenção com formulários, botões, progresso e histórico. Cada ação deve ter um resultado verificável e uma mensagem que indique o próximo passo. As regras de estoque, produção e custos continuam nos serviços existentes.

Pedido confirmado: criar conta de superusuário com acesso aos demais usuários; planejar painel abrangente. O usuário definiu o e-mail e autorizou a publicação no site. A primeira entrega usa prazo de suporte de 15 minutos e motivo obrigatório. Módulos e ordem do painel completo continuam propostos; prioridades e políticas futuras permanecem para decisão.

## Perfis e limites

| Perfil | Permissões |
|---|---|
| Usuário do negócio | Operações existentes somente no próprio negócio; não lista contas da plataforma |
| Superusuário | Diretório global, abertura e encerramento de suporte e, nas entregas futuras, ações administrativas autorizadas |
| Superusuário em suporte | Opera os módulos de um negócio selecionado; mantém a identidade do operador na auditoria; não altera credenciais do cliente nem assume outro superusuário |

O cadastro público nunca concede privilégio administrativo. A conta administrativa fica separada da conta diária, com tenant próprio. Privilegiação é procedimento explícito de operação, sem promoção automática de e-mail já existente. A sessão de suporte exige que operador, usuário e empresa permaneçam ativos. Revogar o privilégio bloqueia novos acessos, inclusive com token anterior.

## Catálogo e dependências

Os IDs `ADM-*` preservam o padrão por domínio usado no PRD (`AUTH-*`, `FT-*`, `UX-*`).

| ID | Resultado | Prioridade proposta | Estado | Pré-requisitos | Fornece / consome |
|---|---|---|---|---|---|
| ADM-01 | Identidade de superusuário e suporte a contas | Imediata | Publicado; conta criada e API validada | Nenhum | Fornece autorização, diretório e contexto de suporte |
| ADM-02 | Gestão de usuários e negócios | Primeira versão | Proposta | ADM-01 | Consome autorização; fornece estado de contas |
| ADM-03 | Auditoria consultável | Primeira versão | Proposta | ADM-01 | Consome operador/contexto; fornece histórico para outras ações |
| ADM-04 | Gestão operacional do ERP | Segunda versão | Proposta | ADM-02, ADM-03 | Consome conta/autorizações; fornece rotinas por negócio |
| ADM-05 | Integrações e tarefas de processamento | Segunda versão | Proposta | ADM-02, ADM-03 | Consome conta/auditoria; fornece diagnósticos e processamento |
| ADM-06 | Manutenção da plataforma | Terceira versão | Proposta | ADM-03 | Consome auditoria; fornece operações de infraestrutura controladas |

### ADM-01 — Conta administrativa e suporte

Histórias: ADM-01.1: como operador, quero entrar com identidade administrativa separada. ADM-01.2: quero procurar uma conta por nome, negócio ou e-mail. ADM-01.3: quero abrir a conta, usar os módulos existentes e voltar à administração.

Aceite: login identifica o perfil; diretório mostra conta e negócio sem hash/senhas; conta normal recebe acesso negado nas rotas administrativas; abertura exige motivo e conta ativa; banner identifica o negócio e operador; sessão expira e pode ser encerrada; ações continuam limitadas à empresa selecionada; troca de conta descarta formulários e consultas da anterior; sessão de um operador não serve a outro; cadastro público não concede privilégios.

Entrega publicada: perfil persistido, migration, comando de criação com senha oculta, `/admin`, listagem paginada de usuários, suporte temporário, banner e retorno. O suporte reutiliza receitas, estoque, pedidos/clientes, produção, produtos acabados, vendas, compras, agenda e configurações. Não substitui um painel completo de manutenção.

Dependências externas: banco PostgreSQL e procedimento de publicação atual. Ativar em produção requer código compatível, backup/restauração verificada e migration explícita.

### ADM-02 — Usuários e negócios

Histórias: ADM-02.1: consultar cadastro, negócio, plano, situação e vínculo WhatsApp. ADM-02.2: ativar/desativar acesso e corrigir dados permitidos com justificativa. ADM-02.3: iniciar recuperação de acesso por canal comprovado.

Aceite proposto: pesquisa e paginação; tela de detalhes; confirmação identifica exatamente a conta afetada; desativação bloqueia login, refresh e suporte; mudanças exigem motivo e ficam no histórico; recuperação não expõe senha; não é possível remover o último operador da plataforma; falhas devolvem o formulário com os valores preenchidos. Planos só podem ser alterados após definir seu efeito real sobre permissões e cobrança.

Consome autorização de ADM-01. Fornece identidade/estado às rotinas operacionais. Pendentes: política de recuperação, campos editáveis, permissões de futuros operadores e aplicação real dos planos.

### ADM-03 — Auditoria

Histórias: ADM-03.1: pesquisar quem fez cada ação, em qual negócio e quando. ADM-03.2: distinguir atividade do cliente de atendimento administrativo.

Aceite proposto: filtros por período, operador, negócio, entidade, resultado e ação; histórico de início/fim/expiração de suporte; alterações administrativas mostram valores anteriores/posteriores pertinentes; tokens e segredos não aparecem; exportação limitada ao perfil autorizado; retenção definida. Falha ao gravar evento impede ações administrativas de alteração que exijam auditoria.

Estado atual: tabela de sessões com operador, destino, motivo, início, prazo e encerramento; logs estruturados identificam operador nas requisições de suporte. Ainda não existe interface de auditoria nem histórico completo de antes/depois de cada alteração. Consome ADM-01; fornece trilha às entregas seguintes. Decisão pendente: retenção e armazenamento consultável dos eventos.

### ADM-04 — Operações do negócio

Histórias: ADM-04.1: resolver demandas de cadastro e operação pela própria tela do negócio. ADM-04.2: executar importações e correções repetíveis sem escrever comandos.

Aceite proposto: entrada visual para todos os módulos existentes; importação de materiais/etapas com prévia, contagens e confirmação; unidades e durações ambíguas ficam pendentes; repetir importação não duplica dados; recálculo apresenta impacto antes de aplicar; correções de estoque usam movimentações com justificativa; estornos/cancelamentos respeitam regras existentes; progresso e resultado disponíveis após fechar a tela; erro não produz execução parcial silenciosa.

Reutilização comprovada: importador de catálogo, serviços de estoque, receitas/composição, pedidos, produção e vendas. Novas rotinas devem chamar esses serviços, preservando tenant e precisão decimal. Consome conta de ADM-02 e auditoria de ADM-03. Pendente: quais correções exigem aprovação adicional e quais operações em lote entram primeiro.

### ADM-05 — Integrações e processamento

Histórias: ADM-05.1: consultar situação de WhatsApp, OCR e tarefas. ADM-05.2: resolver falhas conhecidas por ações específicas.

Aceite proposto: separar configuração, conectividade, pareamento, webhook e worker; mostrar última evidência e hora; distinguir erro de credencial, indisponibilidade e tarefa em andamento; reenfileiramento só para operações idempotentes; prévia identifica conta/documento e impacto; não reenviar compras nem mensagens só por atualizar status; segredos mascarados; configurar ou girar credenciais não as devolve em histórico; nenhuma ativação real de telefone sem seleção explícita.

Consome ADM-02 e ADM-03. Dependências externas: Evolution, Redis/Celery e provedor OCR já configurados. O estado real deve ser consultado em cada diagnóstico. Pendentes: primeiras ações permitidas e se a manutenção da Evolution fará parte desta interface ou será link para o Manager.

### ADM-06 — Manutenção

Histórias: ADM-06.1: consultar saúde real dos componentes. ADM-06.2: executar backups e rotinas aprovadas com botões e histórico.

Aceite proposto: status separado de API, banco, cache, worker e integrações; `/health` atual é apenas evidência do processo da API; backup informa início/fim, tamanho, retenção e última restauração de teste; limpeza mostra simulação e escopo antes de executar; tarefas longas rodam em background com identificador; repetição não dispara trabalho duplicado; falha informa o que foi aplicado. Restaurar backup, publicar versão e reiniciar componentes exige fluxo específico com impacto, confirmação e evidência de recuperação.

Consome ADM-03. Operações de infraestrutura exigem executor com uma lista restrita de ações e permissões mínimas, sem conceder ao servidor web acesso irrestrito ao host ou ao socket Docker. Reutilizar o procedimento atual de backup e deploy quando apropriado. Pendentes: acesso do executor à VPS, armazenamento externo de backups, retenção, recuperação e disponibilidade aceitável.

## Sequência proposta

| Etapa | Features | Entrada e saída |
|---|---|---|
| Base | ADM-01 | Concluída: conta criada no site e acesso validado; aceite visual desktop/celular segue pendente |
| Gestão | ADM-02, ADM-03 | Definir contrato de eventos antes de ligar alterações de cadastro; entregar diretório e histórico |
| Operação | ADM-04, ADM-05 | Rotinas reaproveitam autorização/auditoria; definir idempotência e limites de tarefas |
| Manutenção | ADM-06 | Definir executor e recuperação antes de ações sobre infraestrutura |

O grafo de pré-requisitos não tem ciclos. Gestão e auditoria compartilham autorização; operações e integrações compartilham eventos/tarefas, exigindo acordar esses contratos antes da implementação. Esta sequência não autoriza implementação automática de todas as propostas.

## Validação e medidas de sucesso

Validar login do operador, negação para contas normais, suporte com duas empresas reais de teste e recurso que existe em apenas uma delas, escrita restrita ao destino, revogação, expiração, encerramento, identidade original no refresh e tentativa de promover-se no cadastro. Validar formulário, banner e retorno em desktop e largura de 390 px. Usar banco isolado e provar migration desde a versão anterior.

Metas propostas para o painel: 100% das ações administrativas de alteração com operador/empresa/resultado auditados; nenhuma quebra de isolamento nos testes; cadastro/suporte/importação/diagnóstico de integrações realizados pela interface; medir proporção de atendimentos que ainda exigem terminal e tempo para concluir as rotinas. Não há linha de base medida nem prazo comercial acordado.

## Escopo posterior e decisões abertas

Console livre de SQL/terminal, edição arbitrária do banco, acesso à senha do cliente e reconstrução dos módulos do ERP ficam fora da proposta. As ações devem ser explícitas, reconhecíveis e reutilizar regras de negócio. Novos módulos fiscais e financeiro/cobrança não surgem apenas porque existe um botão administrativo.

Para proteger uma conta que acessa toda a plataforma, especificar autenticação adicional e migração dos tokens para cookies httpOnly; hoje os tokens permanecem no armazenamento do navegador. Ainda precisam de decisão: MFA, sessão máxima, restrição de IP, política de recuperação de superusuário e quantidade de operadores. Não apresentar esses controles como já implementados.

Próximo handoff: ADM-02 e ADM-03, consumindo ADM-01, para especificações técnicas após confirmar prioridades e política de auditoria. Não foram criados tickets externos nem commit. A publicação autorizada de ADM-01 está registrada no relatório da entrega; os demais módulos não foram implementados.
