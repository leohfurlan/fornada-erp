# Evolution API — cadastro e compras pela conversa

## Ativação em produção — 06/10/2026

Evolution 2.3.7 na VPS `atos-pd` (`https://evolution.atospd.com`), instância `fornada` pareada e em estado `open`. Backend da Fornada em `ssh fornada`, `/opt/fornada`, com migrations já aplicadas até `2798d1537c70`. Integração e autenticação WhatsApp ativadas no `.env.production`; token da instância e segredo de webhook transferidos por pipe SSH sem exposição. Backup restrito do ambiente anterior: `backups/env-before-whatsapp-20261006T184706Z`.

Somente backend foi recriado e worker foi iniciado com concorrência 1, preservando banco, Redis, frontend e proxy. Backend saudável; worker registrou `whatsapp.process`; evento próprio de teste publicado e consumido pela fila terminou em `SUCCESS` sem dados de negócio ou mensagem real. Webhook autenticado configurado para `https://fornada.atospd.com/api/v1/whatsapp/webhook`, somente `MESSAGES_UPSERT`, `byEvents=false`, `base64=false`, header `X-Webhook-Secret`. Na versão 2.3.7, `byEvents` e `base64` são os campos da requisição; a resposta persistida usa `webhookByEvents` e `webhookBase64`.

Validação de transporte: POST sem segredo 401; POST autenticado com evento próprio ignorado 202. Esses testes atestam infraestrutura e autenticação, não uma conversa real. Teste solicitado ao operador: enviar “Oi” de outro número e verificar resposta de cadastro. Nenhuma mensagem real de teste foi enviada pelo agente.

**OCR ainda depende de configurar `GOOGLE_AI_API_KEY`** no ambiente de produção e recriar backend/worker. Sem a chave, fotos recebem aviso de leitura indisponível e não geram compras; cadastro e compra manual estão habilitados. Não usar cupons fictícios como compras reais durante o teste. Compra modifica estoque apenas depois de `CONFIRMAR`.

Scripts operacionais: `deploy/evolution/activate_fornada.py` executa na Fornada, usa o lock de deploy e faz backup/restauração do ambiente; `connect_fornada.py` executa na Evolution para configurar/verificar/desligar o webhook. A ação `export` contém segredos: usar somente canalizada ao SSH da Fornada, nunca isoladamente no terminal ou em logs. Antes de nova ativação, verificar deploys simultâneos e preservar a configuração existente.

## Implementação e validação anteriores

Implementação local de 06/10/2026. Integração com Evolution API v2 externa. Não instala Evolution no servidor da Fornada e não publica nem envia mensagens reais durante os testes.

## Fluxo

Um contato novo recebe cadastro guiado: nome, confeitaria, e-mail e endereço estruturado. `CONFIRMAR CADASTRO` cria tenant e usuário, vincula o remetente e entrega o guia de onboarding. O cadastro expira em 30 minutos. Não coleta senha na conversa: o usuário acessa o aplicativo pelo código WhatsApp da autenticação existente. Contas existentes devem vincular o telefone pela tela autenticada de Configurações > WhatsApp; informar um e-mail na conversa não concede acesso a uma conta existente.

Após cadastro/vínculo:

| Mensagem | Ação |
| --- | --- |
| `COMPRAR` | Solicita foto do cupom |
| Foto JPG, PNG ou WebP até 8 MB | Processa OCR em Celery e guarda uma prévia, sem mudar estoque |
| `ITEM Açúcar; 2; kg; 5,90` | Cria prévia manual de novo ingrediente; custo por unidade informada |
| `REVISAR` | Exibe a prévia pendente |
| `CORRIGIR 1; Açúcar; 2; kg; 5,90` | Corrige os dados do item 1 antes de salvar |
| `CONFIRMAR` | Salva pelo serviço de compras e recalcula estoque/custo |
| `CANCELAR` | Descarta prévia/cadastro |
| `ONBOARDING` | Exibe os primeiros passos |
| `ENTRAR` | Indica o acesso no aplicativo |

Uma prévia pendente por remetente; validade de 24 horas. OCR sugere vínculos com ingredientes existentes e a mensagem identifica novo cadastro ou ingrediente existente. Não converte quantidades/custos automaticamente entre kg/g ou l/ml: divergência de unidades exige cadastro manual. Mock de OCR nunca gera compra pelo WhatsApp. Fotos não são persistidas no banco nem baixadas de URLs recebidas do webhook.

## Configuração

Backend e worker precisam das mesmas variáveis:

```dotenv
WHATSAPP_AUTH_ENABLED=true
EVOLUTION_ENABLED=true
EVOLUTION_API_URL=https://evolution.exemplo.com
EVOLUTION_API_KEY=<credencial do servidor>
EVOLUTION_INSTANCE=fornada
EVOLUTION_WEBHOOK_SECRET=<segredo aleatório com no mínimo 32 caracteres>
FRONTEND_URL=https://fornada.exemplo.com
GOOGLE_AI_API_KEY=<credencial OCR>
```

Não coloque credenciais em variáveis `NEXT_PUBLIC_*`. A integração permanece desligada nos exemplos. Produção exige HTTPS. Configure o webhook da instância para `POST https://fornada.exemplo.com/api/v1/whatsapp/webhook`, evento `MESSAGES_UPSERT`, `webhookByEvents=false`, `webhookBase64=false`, com header `X-Webhook-Secret` igual ao segredo configurado. Confirme que a versão instalada aceita headers personalizados. Não use a API key da Evolution como segredo do webhook.

Contrato de transporte: envio em `POST /message/sendText/{instance}` com `number`, `text` e header `apikey`; mídia em `POST /chat/getBase64FromMediaMessage/{instance}` com `message` e `convertToMp4=false`. Envelope recebido deve conter `instance`, `event`, `data.key.id`, `data.key.fromMe=false`, `data.key.remoteJid` no formato telefone `@s.whatsapp.net`, além de `data.message`. Grupos, status, mensagens próprias e JIDs opacos `@lid` são ignorados. Suporte a LID necessita resolução oficial de identidade e não está incluído.

Fontes consultadas: [rotas de chat da Evolution](https://github.com/evolution-foundation/evolution-api/blob/main/src/api/routes/chat.router.ts), [transporte oficial Evolution](https://github.com/evolution-foundation/evolution-api/blob/main/src/api/integrations/channel/evolution/evolution.channel.service.ts), [eventos de webhook oficiais](https://github.com/evolution-foundation/evolution-docs/blob/main/docs/02-Configuration/Webhooks.md). O último documento descreve também contratos antigos; confirme versão e payload real antes de ativar.

Headers personalizados constam também nos [tipos oficiais de configuração](https://github.com/evolution-foundation/evolution-api/blob/main/src/api/types/wa.types.ts) e no [controller de instâncias](https://github.com/evolution-foundation/evolution-api/blob/main/src/api/controllers/instance.controller.ts).

Migration: `6d0a753dbf1c` após `a42f344c4565`. API devolve 202 somente quando conseguiu publicar na fila; falha no broker devolve 503 para permitir reentrega. Reinicie/recrie o worker ao atualizar o código para carregar `infrastructure.celery.whatsapp_tasks`. Para um piloto, use **um único worker com concorrência 1** para manter a ordem da conversa; paralelismo com ordenação por remetente exige evolução adicional.

No Compose Micro, o serviço Celery exige `--profile worker`. Ativar o webhook sem esse profile recebe mensagens na fila, mas não executa a conversa. O Compose de produção foi configurado com concorrência 1; ao rodar manualmente no Windows, Celery exige uma estratégia de pool compatível (o deploy recomendado usa Linux).

## Persistência e garantias

`whatsapp_cadastros` mantém estado pré-tenant, por remetente. `whatsapp_eventos` é inbox/outbox de transporte. São exceções explícitas ao tenant obrigatório porque recebem contatos sem conta; não expõem endpoints de leitura públicos. `whatsapp_compras` possui tenant obrigatório, usuário, telefone, validade, status e itens revisáveis. Toda busca de prévia filtra tenant, usuário e telefone. Conta/tenant inativo não pode comprar nem recadastrar o mesmo número.

Um lock Redis serializa cada remetente. Confirmação e inbox/outbox são persistidos na mesma transação; savepoint desfaz entradas parciais se algum item falhar. Reentrega do mesmo evento reproduz apenas resposta pendente, sem repetir estoque. Uma confirmação nova após salvar também não encontra prévia pendente. Se Evolution aceitar uma resposta e houver falha antes de marcar `enviado`, a resposta pode chegar novamente; os efeitos da compra não se repetem.

O estado de cadastro expirado não é utilizado. Dados temporários e respostas permanecem armazenados até rotina de retenção; definir prazo operacional e implementar limpeza antes de uma operação ampla. Falhas transitórias são repetidas até cinco vezes. Após esgotar retries, uma operação deve inspecionar a task e reentregá-la; não há tela de suporte ou reprocessamento automático de outbox neste primeiro fluxo.

## Validação e ativação pendente

Testes com PostgreSQL temporário verificam cadastro completo, foto com OCR fake, ausência de estoque antes da revisão, confirmação única e tentativa de acesso a prévia de outro tenant. Testes unitários cobrem webhook autenticado, envelope, mídia, decimais, expiração, replay e divergência de unidades. Serviço de compras existente foi incluído na regressão.

Resultado final: **195 testes passaram, 4 foram ignorados** na suíte backend. O teste adicional de compra com segundo item inválido confirmou rollback da entrada do primeiro item. Ruff dos arquivos novos e `git diff --check` passaram. Todas as migrations foram aplicadas somente no PostgreSQL temporário de testes. Transportes Evolution e OCR real foram substituídos por fakes; esses resultados não atestam entrega real de WhatsApp.

Faltam URL/versão/instância/credenciais da Evolution e teste com número controlado para verificar conexão, payload de mídia e entrega real. Não foram alterados bancos existentes nem realizados commit, push, deploy ou envio real. Não considerar HTTP 2xx da Evolution comprovação de entrega ao telefone.
