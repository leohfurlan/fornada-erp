# Integração Fornada / whatsapp-admin — contrato v1

Implementação: 09/10/2026. Acesso por API; sem SSO ou compartilhamento de sessão.

## Identidade e confiança

Todas as rotas usam `Authorization: Bearer <CENTRAL_SERVICE_TOKEN>`. O segredo tem pelo menos 32 caracteres e pertence ao serviço. `CENTRAL_BUSINESS_TENANTS` concede explicitamente cada UUID de negócio da central a um UUID de tenant Fornada. A central é responsável por validar instância, webhook e telefone do remetente; o ID da mensagem é correlação, não assinatura independente.

A Fornada revalida usuário e tenant ativos, ausência de exclusão e usuário não superuser. A regra comercial acompanha a API atual: todo usuário comum ativo do tenant concedido pode revisar/receber compras. Não há papéis comerciais diferenciados no modelo atual. Um operador da central não substitui a identidade da confeiteira.

Propostas pertencem ao negócio, tenant, usuário, telefone e conversa. Trocar o telefone invalida execução da proposta anterior. Revogar usuário bloqueia passos seguintes; a transação em andamento já autorizada pode terminar antes da revogação adquirir o lock. Grants/token são configuração de servidor: atualizar API e workers conjuntamente.

## Endpoints

Todos são POSTs sob `/api/v1/central`, com JSON e sem redirecionamento.

| Rota | Entrada principal | Resultado |
|---|---|---|
| `resolve` | `business_id`, `sender_phone` E.164, `operation`, `scope?`, `resource_id?` | Identidade atual e escopo autorizado. Recurso informado deve pertencer à usuária. |
| `extract` | Identidade + `conversation_id`, `incoming_message_id`, `content_base64`, `mime` | Proposta sem efeito comercial; mesma imagem no mesmo contexto retorna a proposta existente. |
| `draft` | Identidade + `proposal_id` | Proposta e versão atuais. |
| `catalog` | Identidade | Materiais, até 200 produtos/lojas e indicação `truncated`. Catálogo parcial exige revisão no ERP quando a opção necessária não aparece. |
| `review` | Identidade + `proposal_id`, `expected_version`, `reviewed` | Prévia calculada pelo motor comercial e novo resumo/hash/versão. |
| `decision` | Identidade + `proposal_id`, `expected_version`, `summary_hash`, `approved`, `incoming_message_id` | Aprovação ou recusa específica; sem lançamento de estoque. |
| `approval` | Operação `stock.receive` | Evidência específica de aprovação e digest da requisição. |
| `execute` | Operação autorizada | Consulta de proposta/compra para `purchases.review`; compra e estoque para `stock.receive`. |
| `reconcile` | Referência da operação, negócio, capacidade, principal, scope e idempotency key | Resultado confirmado ou `unknown`; nunca executa lançamento. |

Uma operação contém `operation_id`, `command_id`, `business_id`, `capability_code`, `payload`, `idempotency_key`, `conversation_id`, `principal_ref`, `scope`, `expected_resource_version` e referências opcionais dos recibos da central. O payload admite somente `{"proposal_ref":"<uuid>"}` para `stock.receive` e `{"resource_ref":"<uuid>"}` para `purchases.review`.

`scope` é `{"tenant_id":"<uuid>","company_id":null}`. O contrato completo de tipos é o OpenAPI gerado pela aplicação e os modelos `Input`/`Identity`/`Operation` da rota. A central também valida schemas pelo seu registro de capacidades.

O digest é SHA-256 de `json.dumps(valor, sort_keys=True).encode()`, sobre a operação serializada em JSON, excluindo `authorization_receipt_ref`, `approval_receipt_ref`, `principal_ref` e `scope`. Não alterar serialização em apenas uma ponta. A Fornada usa a identidade/escopo revalidados e uma proposta persistida, sem executar valores livres enviados pelo agente.

## Estados e limites

Fornada: `review → awaiting_approval → approved → confirmed`; recusa termina em `rejected`. Revisar novamente incrementa versão e revoga aprovação anterior. Propostas expiram em 24 horas; repetir imagem não renova prazo. Resultado confirmado continua consultável.

A central possui estados próprios, incluindo `prepared`, `blocked`, `unknown` e `quarantined`; não confundir com os estados da origem. Salvar revisão não envia resumo. O envio explícito do resumo delega a aprovação à confeiteira. O comando é `APROVAR <codigo> <versao>` ou `RECUSAR <codigo> <versao>`; “ok” exige intervenção.

Imagens: PNG, JPEG ou WebP, até 20 MiB, assinatura/formato conferidos e até 25 milhões de pixels. JSON/base64 exige limite de proxy compatível, pelo menos 28 MiB. O adapter limita respostas a 1 MiB; catálogo grande pode exigir tratamento direto no ERP. OCR local é opcional, Tesseract com idioma `por`, sem fallback para visão pública. O piloto é funcional com OCR desligado.

HTTP: 401 credencial ausente/inválida; 403 vínculo/escopo/recurso negado; 404 integração desativada ou proposta ausente; 409 versão obsoleta, expiração, aprovação ausente ou contexto alterado; 422 entrada inválida. O adapter classifica falhas sem repassar corpo privado da origem; 403 na resolução vira `DENIED`, enquanto falha do serviço/credencial permanece indisponibilidade. Falha de transporte durante mutação continua sendo incerteza: consultar a operação, sem retry automático de lançamento.

## Consistência e recuperação

Compra, movimentos e resultado da proposta são confirmados na mesma transação externa. Requisições simultâneas da mesma operação são serializadas; repetição retorna a compra existente. Outra operação tentando consumir proposta confirmada é recusada. Nenhum efeito ocorre antes de aprovação específica e prévia atual.

Após resposta perdida, a central mantém a tentativa persistida, marca incerteza e usa `/reconcile`. Resultado incerto sem referência não é sucesso. Após restauração, autorizações da central e propostas de fluxo ficam em quarentena; não reiniciar execução automática.

## Configuração desativada por padrão

Fornada: `CENTRAL_ENABLED=false`, `CENTRAL_SERVICE_TOKEN=`, `CENTRAL_BUSINESS_TENANTS={}`, `CENTRAL_LOCAL_OCR_ENABLED=false`. Compose repassa a mesma configuração para backend e workers, preservando as variáveis iFood/OTP.

Central: `CENTRAL_FORNADA_CONNECTORS` por UUID do negócio, com `base_url`, token dedicado, `verified`, `conformance_ref`, `automation_enabled=false`, `activated_after=null`. API e workers de mensagens/agentes devem usar a mesma configuração. Habilitar capacidades `purchases.review`/`stock.receive` somente no negócio correto; não declarar pedidos, agenda ou produção neste piloto.

Antes de ativar: validar HTTPS, segredo dedicado, concessão exata, telefone da usuária, backup/restauração, versão Evolution e único responsável pela conversa. Manter OTP/alertas iFood conforme o roteamento autorizado. Nenhuma configuração real foi alterada na implementação local.

## Ensaio reproduzível

Criar PostgreSQL descartável exclusivo em `127.0.0.1:55446`, usuário `integration`, senha local de teste `integration_local_only`, banco inicial `postgres`. Não reaproveitar produção. O ensaio recusa outro host/porta/banco inicial e cria/remove somente dois bancos de nomes aleatórios próprios.

Na raiz Fornada, PowerShell:

```powershell
& 'C:\Projetos TI\whatsapp-admin\backend\.venv\Scripts\python.exe' `
  backend/scripts/validar_central_http.py `
  --central-backend 'C:\Projetos TI\whatsapp-admin\backend' `
  --fornada-python 'C:\Projetos TI\fornada\backend\.venv\Scripts\python.exe' `
  --postgres-url 'postgresql://integration:integration_local_only@127.0.0.1:55446/postgres' `
  --evidence '.scratch/central-http-evidence.json'
```

O ensaio aplica migrations reais, inicia ambas as APIs em portas locais temporárias e chama os workers reais da central. Apenas envio/download Evolution e perda de resposta de rede são simulados. Evidência é sintética; não homologa WhatsApp real. Credencial do operador é uma sessão sintética provisionada diretamente para o ensaio, sem modificar login de produção.

## Preparação de publicação e desativação

Publicar somente após autorização operacional e homologação. Gerar novo segredo, guardar no mecanismo de segredos, fazer backup e ensaio de restauração, aplicar `alembic upgrade head`, publicar API/workers com configuração desativada e testar. A head esperada desta entrega é `a85c10b7d302`.

Para interromper novas operações: desativar automação do conector e assumir conversas. Não derrubar indiscriminadamente Evolution, OTP ou alertas. Preservar propostas/compra/estoque e reconciliações pendentes; a UI pode bloquear consulta quando conector/vínculo está desativado, exigindo investigação autenticada no ERP ou reabilitação controlada somente após verificação. Não remover dados nem fazer downgrade como mecanismo de desativação. Não repetir lançamentos incertos.

Propostas expiradas, catálogo truncado, cupons grandes e conflitos de prévia requerem tratamento no ERP. Retenção da central segue seu cleanup; limpeza das propostas persistidas na Fornada exige política própria antes de expandir o piloto para grande volume. Agenda/pedidos/produção e SSO ficam para contratos posteriores.
