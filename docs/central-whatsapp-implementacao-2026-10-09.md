# Integração Fornada / whatsapp-admin — implementação local

Data: 09/10/2026. Configuração real permanece desativada; sem commit, push, deploy, migration em produção ou envio real de WhatsApp.

## Resultado

Implementado o serviço privado da Fornada para compras revisadas e aprovadas pela usuária na central. O piloto funciona com OCR desligado: imagem recebida abre revisão humana, o operador preenche itens, envia resumo, a confeiteira aprova a versão e só então o ERP registra compra/estoque. Não há SSO nem novas capacidades de agenda/pedidos/produção.

Trabalho preparado em `.scratch/central-integration`, com snapshot dos arquivos atuais, e incorporado por manifest de 21 arquivos à Fornada após verificar que os arquivos originais continuavam iguais ao snapshot. Alterações pré-existentes de iFood, frontend, deploy e WhatsApp foram preservadas. A central recebeu alterações pontuais no adapter, messaging e testes; o restante do projeto foi preservado.

## Mudanças centrais

- `backend/api/routers/central.py`: resolve, extract, draft, catalog, review, decision, approval, execute e reconcile; autenticação dedicada, grant negócio→tenant e identidade atual.
- `backend/infrastructure/database/central_models.py` e migration `73a5fcee0651`: propostas, versões, hashes, aprovação e resultado da compra.
- Migration de merge `a85c10b7d302`: preserva ambas as revisões central/iFood e produz uma única head.
- `domain/compras/extraction.py`, `infrastructure/ocr/hybrid.py` e adições compatíveis ao reconhecimento/schema: dependências mínimas do OCR local, sem trocar adapters públicos nem fluxos legados.
- Configuração, rotas, Alembic, exemplos `.env` e Compose integrados com iFood; serviço desligado por padrão.
- Dockerfiles com Tesseract/idioma português; `requirements.prod.lock` fixa versões das dependências Python da imagem validada. Pacotes do sistema/base Docker ainda seguem os repositórios e tags configurados; isso não promete reprodução binária integral.
- Central `backend/app/fornada_adapter.py`: erros classificados por status sem expor corpo privado e sem retry de mutação.
- Central `backend/app/messaging.py`: conversas novas herdam o início da ativação, evitando perder a primeira mensagem quando o consumo da inbox atrasa. Regressão com relógio controlado.
- Verificador de continuidade da central estabiliza timestamp nas redeliveries do mesmo evento; evita falsa falha dependente da passagem de segundo.

## Correções além do patch original

Trocar telefone cadastrado invalida a aprovação anterior. `/resolve` nega recursos inexistentes e verifica a propriedade de propostas/compras. Aprovação é exclusiva de `stock.receive`; payloads são limitados à referência declarada da capacidade. Revogação de usuário/tenant/grant e alteração da prévia bloqueiam execução. Limite da imagem alinhado em 20 MiB com a central, mantendo conferência do formato e limite de pixels.

Regra de permissão preservada: usuário comum ativo do tenant concedido pode operar compras, conforme API atual. Superuser não representa a confeiteira. Usuários com papéis comerciais diferenciados exigiriam evolução do modelo.

## Validação

- Fornada: suíte completa com **318 passed, 4 skipped** após integração e correções. Regressores focados de compras/WhatsApp/iFood: 44 aprovados.
- Central: **213 passed** na repetição completa, incluindo recuperação cifrada com rclone local. Após o último ajuste de classificação de identidade negada (HTTP 403), **10 testes direcionados de adapter/transporte passaram**; a suite completa não foi repetida depois desse ajuste pontual.
- Fornada no checkout final: **18 testes focados aprovados**, após adaptar a proteção de banco dos testes para aceitar também o banco padrão `fornada_test`, sem exigir uma porta específica.
- Ruff direcionado aos arquivos novos/alterados da integração e verificação de whitespace aprovados.
- Build local da imagem de produção; importação da API sem rede e `tesseract --list-langs` com `por`. Compose validado sem iniciar serviços.
- Ensaio reproduzível `backend/scripts/validar_central_http.py`: duas APIs reais em processos separados, bancos aleatórios próprios, migrations reais e workers da central. Apenas Evolution e falha de rede são simulados.
- Ensaio cobre revisão manual sem OCR, salvar sem enviar, aprovação e referência real, revogação antes da execução, duas requisições concorrentes e tomada humana. Simula resposta perdida depois do commit: central fica incerta e recupera a compra via reconciliação sem outro execute.
- Resultado comercial do ensaio: três compras, três movimentos e estoque final de 6 kg, equivalentes a três entradas de 2 kg; nenhum lançamento na revogação/tomada humana.
- Migration: upgrade a partir da head iFood, downgrade de volta a iFood e novo upgrade, preservando usuário e registros sintéticos de monitor/alerta iFood. Cada ensaio também parte de bancos vazios.

Evidência HTTP final: [JSON sintético](central-whatsapp-http-evidencia-2026-10-09.json). A execução final usou os checkouts incorporados dos dois projetos, já com a classificação HTTP 403 ajustada. A suite da central emitiu um aviso de depreciação do TestClient/Starlette, sem falha.

Os testes da central usam schemas/bancos temporários no PostgreSQL local dedicado, incluindo rclone crypt com storage local. Os testes não enviam dados ao Drive. Uma primeira regressão parcial falhou por ausência de `CENTRAL_TEST_RCLONE_BINARY`; a configuração do runtime foi corrigida para executar os ensaios de recuperação reais. A primeira suíte completa revelou duas falhas descritas acima e motivou as correções; não foi tratada como aprovação.

## Limites e próxima etapa

Homologar Evolution/Baileys e publicar os dois serviços continua pendente de autorização operacional. Confirmar UUID do negócio, tenant, usuária, telefone, segredo dedicado, versão/payload da Evolution, roteamento e único responsável pela conversa. Backup/restauração da implantação precisa ser verificado no ambiente real antes de migration.

OCR automático tem cobertura restrita de layouts e não identifica loja de modo suficiente para garantir preparação automática. Catálogo inicial tem limite de produtos/lojas; usar ERP para registros ausentes. Aprovação usa código/versão; “ok” não aprova. Propostas expiradas e operação incerta precisam de tratamento consultivo, sem retry automático.

O [contrato e runbook](central-whatsapp-contrato-v1.md) registra configuração, erros, confiança no remetente, ponto transacional de revogação, reprodução dos testes e desativação sem apagar dados.
