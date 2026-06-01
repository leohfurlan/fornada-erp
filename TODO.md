# TODO — Fornada

> Estado do projeto em **30/05/2026** confrontado com [PRD.md](PRD.md) e [CLAUDE.md](CLAUDE.md).
> Marcações: ✅ feito · 🟡 parcial · ⬜ pendente

---

## Sprint 3 — Concluída ✅

### Mudança conceitual
- ✅ Dois fluxos comerciais paralelos: **Encomenda** (Pedido existente) e **Pronta entrega** (Venda multicanal nova)
- ✅ **Ordem de Produção (OP)** é a única responsável por mexer em ingredientes — Pedido foi simplificado
- ✅ **Estoque de Produto Acabado (PA)** intermedia produção e saída (Venda ou Pedido entregue)

### Estoque de Produto Acabado (base)
- ✅ Tabelas `estoque_produto_acabado` e `movimentacoes_estoque_pa` (migration `9dd6076eb726`)
- ✅ Domínio `domain/estoque_pa/` com `buscar_ou_criar` (idempotente), `incrementar`, `debitar`, `debitar_para_pedido` (atomic)
- ✅ Exceção `EstoquePAInsuficienteError` + handler 409 em pt-BR
- ✅ Rotas `GET/PATCH /estoque-pa`, `GET /estoque-pa/{receita_id}/movimentacoes`
- ✅ Origens rastreadas: `op:N`, `venda:N`, `pedido:N`, `venda_cancelada:N`, `ajuste`

### Refator Pedido
- ✅ State machine simplificada: `orcamento → aprovado → entregue | cancelado`
- ✅ `PedidosService` removeu `_reservar_estoque`, `_consumir_estoque`, `_estornar_reserva`, `_necessidade_por_ingrediente`
- ✅ Dependência: `EstoquePAService` (não mais `EstoqueRepository` de ingrediente)
- ✅ "Entregue" debita estoque PA (atomic — valida tudo antes); status legados `em_producao`/`finalizado` aceitos mas inalcançáveis

### Ordens de Produção (PCP)
- ✅ Tabela `ordens_producao` (migration `ff1a62e78ec2`) com `numero`, `receita_id`, `pedido_id` (opcional), `qtd_planejada`, `qtd_produzida` (nullable), `data_prevista`
- ✅ State machine: `planejada → em_producao → finalizada | cancelada`
- ✅ Side effects:
  - `→ em_producao`: reserva ingredientes (lógica antes do `PedidosService`, agora vive aqui)
  - `→ finalizada`: debita ingredientes pelo **planejado**, incrementa estoque PA pelo **produzido real** (apontamento)
  - `→ cancelada` (de `em_producao`): estorna reserva
- ✅ Rotas: CRUD + `PATCH /producao/ordens/{id}/status` com body `{status, qtd_produzida?}`
- ✅ Movimentação de ingrediente registrada com `origem='producao:{numero}'`

### Vendas (apontamento multicanal)
- ✅ Tabelas `vendas` e `venda_itens` (migration `5773d636139d`)
- ✅ Canais: `loja_fisica | whatsapp | ifood | instagram | outro`
- ✅ Cliente **opcional** (venda avulsa sem cadastro)
- ✅ Service atomic: valida saldo PA agregado por receita (mesma receita em 2 itens soma corretamente) antes de criar venda
- ✅ Cancelamento: estorna estoque PA (com origem `venda_cancelada:N`) + soft delete

### Frontend — telas e componentes
- ✅ Types: `OrdemProducao`, `Venda`, `VendaItem`, `EstoquePA`, `MovimentacaoEstoquePA`, `StatusOP`, `CanalVenda`
- ✅ Hooks: `use-producao`, `use-vendas`, `use-estoque-pa`
- ✅ Componentes shared: `OpStatusBadge`, `CanalVendaBadge`, `TabEstoquePA`
- ✅ **Tela `/producao`** — PCP com agrupamento por data (Atrasado/Hoje/Amanhã/Próximos 7 dias/Futuro/Sem data) + chips de filtro de status
- ✅ **Tela `/producao/nova`** — form com preview de consumo de ingredientes calculado client-side
- ✅ **Tela `/producao/[id]`** — botões contextuais (Iniciar produção, Apontar produção, Cancelar) + modal de apontamento com qtd_produzida + link cruzado para Pedido se vinculado
- ✅ **Tela `/vendas`** — lista com chips de canal, badge multicolor por canal, total agregado do período
- ✅ **Tela `/vendas/nova`** — mobile-first: chips grandes de canal, itens com saldo PA visível por receita, preço sugerido do `preco_recomendado`, cliente opcional, total live
- ✅ **Tela `/vendas/[id]`** — detalhe com botão "Cancelar venda" que estorna estoque PA
- ✅ **Tela `/estoque`** refatorada com **tabs** (Ingredientes / Produtos prontos)
- ✅ **Tela `/estoque/pa/[receitaId]/historico`** — entradas/saídas com origem traduzida (op/venda/pedido)
- ✅ Edição inline da `qtd_minima` no card de produto pronto
- ✅ Pedido detalhe: status `em_producao`/`finalizado` removidos do `STATUS_LABEL` e filtros
- ✅ Menu inferior reorganizado: **4 ações principais** (Início, Vendas, Produção, Pedidos) + dropdown **Mais** (Receitas, Estoque, Configurações)

### Testes (Sprint 3)
- ✅ **102 testes passando** (77 da Sprint 2 + 25 novos)
- ✅ Cobertura crítica:
  - `producao/state_machine.py`: **100%**
  - `pedidos/state_machine.py`: **100%**
  - `vendas/service.py`: **87%** (meta 80%) ✓
  - `vendas/repository.py`: **88%**
  - `producao/service.py`: **66%** (paths críticos cobertos; integração end-to-end)
  - `receitas/calculos.py`: **100%** (mantida)
- ✅ Suítes novas:
  - `test_state_machine_producao.py` (unit)
  - `test_state_machine_pedidos.py` reescrito para fluxo simplificado
  - `test_producao_fluxo.py` — reservar → apontar com qtd≠planejada → ingredientes baixam, PA cresce; perda total (qtd=0) baixa ingredientes mas PA não cresce; cancelar em produção estorna reserva; bloqueio por estoque insuficiente
  - `test_vendas_fluxo.py` — debita PA; múltiplos itens da mesma receita agregam na validação; cancelar estorna; isolamento de tenant
  - `test_pedidos_fluxo.py` reescrito — entregar debita PA, sem saldo bloqueia atomicamente

---

## Sprint 2 — Concluída ✅

### Estoque — operações completas
- ✅ `PATCH /estoque/ingredientes/{id}` (editar nome, tipo, unidade, estoque mínimo)
- ✅ `DELETE /estoque/ingredientes/{id}` (soft delete) com bloqueio se ingrediente em uso
- ✅ `GET /estoque/ingredientes/{id}/movimentacoes` com paginação
- ✅ Tela `/estoque/[id]/editar` (mobile-first + zona de risco para excluir)
- ✅ Tela `/estoque/[id]/historico` (entradas/saídas com sinal +/−)
- ✅ Botões "Editar" e "Histórico" na tabela desktop e no card mobile

### Receitas — métricas de lucro + embalagem + duplicar
- ✅ Campo `preco_de_venda_real` (model + schema + form + migration)
- ✅ Custo de embalagem separado (ingredientes do tipo `embalagem` somam em `custo_embalagem`)
- ✅ Novas métricas no `CustoDetalhado`: `lucro_estimado`, `margem_real`, `custo_por_hora_produzida`, `lucro_por_minuto`, `tempo_passivo_minutos`
- ✅ `CustoCard` exibe seção "Resultado" condicional (verde se lucro positivo, vermelho se negativo)
- ✅ Funções puras `calcular_custo_por_hora_produzida()` e `calcular_lucro_por_minuto()` em [calculos.py](backend/domain/receitas/calculos.py)
- ✅ Duplicar receita: `POST /receitas/{id}/duplicar` + botão na tela de detalhe (redireciona para edição com sufixo "(cópia)" auto-incrementado)

### Pedidos — domínio inteiro (eixo da sprint)
- ✅ Tabelas `clientes`, `pedidos`, `pedido_itens` + migration
- ✅ Domínio `domain/pedidos/` (schemas, repository, service, state_machine)
- ✅ Máquina de estados: `orcamento → aprovado → em_producao → finalizado → entregue`, com `cancelado` saindo de qualquer não-terminal
- ✅ Side effects no estoque:
  - `→ em_producao`: incrementa `quantidade_reservada`, valida disponibilidade (raise `EstoqueInsuficienteError` se faltar)
  - `→ finalizado`: debita `estoque_atual`, zera reserva, registra `MovimentacaoEstoque(tipo='saida', origem='pedido:N')`
  - `→ cancelado` (de em_producao): estorna reserva
- ✅ Rotas: CRUD de clientes e pedidos + `PATCH /pedidos/{id}/status`
- ✅ Tela `/pedidos` (lista com chips de status, filtro por busca, badge de prazo ≤48h / atrasado)
- ✅ Tela `/pedidos/novo` (form com itens dinâmicos, cliente inline novo, preço sugerido do `preco_recomendado` da receita)
- ✅ Tela `/pedidos/[id]` (detalhe com botões de transição contextual baseados em `proximas_transicoes` vindo do backend)
- ✅ Componente `PedidoStatusBadge` colorido por status
- ✅ Entrada "Pedidos" no menu inferior mobile

### Segurança / Observabilidade
- ✅ Rate limiting com `slowapi`:
  - `/auth/register`: 5/hora
  - `/auth/login`: 10/minuto
  - `/auth/refresh`: 20/minuto
- ✅ Handler 429 em pt-BR ("Muitas tentativas...")
- ✅ Limiter compartilhado em [core/rate_limit.py](backend/core/rate_limit.py)

### Testes (CLAUDE.md §10)
- ✅ 80 testes passando (`pytest --cov`)
- ✅ Cobertura:
  - `domain/receitas/calculos.py`: **100%** (meta 95%) ✓
  - `domain/pedidos/state_machine.py`: **100%** ✓
  - `domain/estoque/service.py`: **94%** (meta 80%) ✓
  - `domain/estoque/repository.py`: **100%** ✓
  - `domain/pedidos/service.py`: 66% (core flows cobertos; 80% fica para Sprint 3)
- ✅ Suíte de integração para fluxo Pedidos: reservar → finalizar → cancelar com estorno → estoque insuficiente → isolamento de tenant
- ✅ `conftest.py` ajustado para usar `NullPool` (evita "another operation in progress" entre testes async) e DB de teste isolado (`fornada_test`)

---

## Sprint 1 — Concluída ✅

### Infraestrutura
- ✅ Docker Compose (PostgreSQL 16, Redis 7, backend, frontend, Celery worker)
- ✅ [.env.example](.env.example) com todas variáveis necessárias
- ✅ [fornada.ps1](fornada.ps1) — wrapper PowerShell para o Makefile
- ✅ CORS via regex aceitando localhost + qualquer IP de rede privada (acesso pelo celular)
- ✅ 3 migrations Alembic aplicadas
- ✅ Git repo + push inicial para [github.com/leohfurlan/fornada-erp](https://github.com/leohfurlan/fornada-erp)
- ✅ [.gitignore](.gitignore) protegendo `.env`, `node_modules`, `__pycache__`, `postgres_data`

### Backend — Arquitetura
- ✅ Estrutura hexagonal por domínio (`api/`, `core/`, `domain/`, `infrastructure/`)
- ✅ FastAPI + SQLAlchemy 2.0 async + asyncpg
- ✅ Pydantic v2 com schemas separados de models
- ✅ Logging via `structlog` (sem `print()` ou `os.environ` direto)
- ✅ Multi-tenancy por `tenant_id` em todas tabelas e queries
- ✅ Soft delete (`deleted_at`) em todas as tabelas de negócio

### Backend — Domínios
- ✅ **Auth**: register, login, refresh, me — JWT access 15min + refresh 7d, bcrypt cost 12
- ✅ **Receitas**: CRUD completo (POST/GET/PATCH/DELETE) com custo recalculado a cada GET
- ✅ **Estoque**: CRUD de ingredientes + entrada de compra com recálculo de custo médio
- ✅ **Configurações**: etapas padrão (CRUD) + custos operacionais + valor/hora
- ✅ **Motor de cálculo** ([calculos.py](backend/domain/receitas/calculos.py)) — **38 testes, 95%+ cobertura**

### Backend — OCR / IA
- ✅ Adapter Gemma 4 via Google AI Studio ([gemma_adapter.py](backend/infrastructure/ocr/gemma_adapter.py))
- ✅ Mock automático quando `GOOGLE_AI_API_KEY` ausente
- ✅ Task Celery para processamento assíncrono

### Frontend
- ✅ Next.js 14 App Router + TypeScript strict + Tailwind
- ✅ Mobile-first (testado em viewport 390px)
- ✅ Auth Zustand + axios interceptor com refresh automático
- ✅ TanStack Query para todo fetch (devtools ocultos em mobile)
- ✅ shadcn/ui base + componentes shared
- ✅ Formatação pt-BR consistente (`formatMoney`, `formatQuantidade`, `formatDataHora`, `formatPercent`, `formatMinutos`)
- ✅ `DecimalInput` aceitando vírgula como separador decimal
- ✅ `UnidadeSelect` agrupado por categoria (peso/volume/contagem)

### Frontend — Telas
- ✅ Login + Cadastro
- ✅ Dashboard home com cards de atalho
- ✅ Receitas: lista, criar, ver detalhe, **editar**, deletar — com modo de preparo (texto livre, quebras preservadas) e `updated_at`
- ✅ Estoque: tabela desktop ordenável + cards expansíveis mobile + filtros (tipo/status) + busca
- ✅ Configurações: hub + Geral (custos+valor/hora) + Etapas padrão (CRUD) + Ajuda (tutorial MOD/MOI/custos)

---

## MVP — Pendente

### Funcionalidades core (PRD §Funcionalidades do MVP)

#### Cadastro de Receitas (PRD §1)
- ⬜ Upload de **foto do produto**
- 🟡 Indicador de **tempo ativo vs passivo** — hoje só temos `direta/indireta`. PRD §1 lista "Tempo ativo vs. passivo | Diferenciação de tempo com e sem atenção" como indicador exibido
- ⬜ Métrica **lucro estimado** (precisa de campo `preço_de_venda_real` separado de `preco_recomendado`)
- ⬜ Métrica **custo por hora produzida** (R$/h)
- ⬜ Métrica **lucro por minuto de produção** (R$/min)
- ⬜ Custo de **embalagem específica por receita** (hoje só genérico via custo operacional)

#### Controle de Estoque (PRD §2)
- ⬜ Tela de **histórico de movimentação** por ingrediente (tabela `movimentacoes_estoque` já existe, falta UI e endpoint)
- ⬜ Implementação real de **quantidade reservada** (depende de Pedidos)
- ⬜ Tela de edição (PATCH) e exclusão de ingrediente — hoje só criação

#### Entrada de Compras via Câmera (PRD §3) ⬜ **NADA NA UI AINDA**
- ⬜ Endpoint que recebe imagem/QR e dispara task Celery
- ⬜ Tela mobile com câmera nativa (`<input type="file" capture="environment">`)
- ⬜ Leitura de **QR Code da NFCe**
- ⬜ Upload de **XML da NFe**
- ⬜ Matching fuzzy de itens extraídos × ingredientes cadastrados
- ⬜ Tela de **confirmação/edição** dos itens antes de salvar
- ⬜ Sugestão de categorização para itens novos
- ⬜ Atualização automática de estoque + custo médio após confirmação

#### Precificação Inteligente (PRD §4)
- ⬜ Componente de custo de **taxas iFood** (configurável)
- ⬜ Componente de custo de **taxa de cartão** (configurável)
- ⬜ Resultado final exibido conforme PRD: lucro estimado, lucro/min, custo/hora produzida

#### Gestão de Pedidos (PRD §5) ⬜ **DOMÍNIO INTEIRO NÃO IMPLEMENTADO**
- ⬜ Tabela `pedidos`, `pedido_itens`, `clientes`
- ⬜ Domínio `domain/pedidos/`
- ⬜ Status workflow: Orçamento → Aprovado → Em Produção → Finalizado → Entregue
- ⬜ Quando pedido entra em "Em Produção", incrementa `quantidade_reservada` dos ingredientes
- ⬜ Quando "Finalizado", baixa do `estoque_atual`
- ⬜ UI: lista de pedidos, novo pedido, detalhe com mudança de status
- ⬜ Foto de referência (upload)

#### Dashboard Financeiro (PRD §6) ⬜ **TELA INICIAL HOJE É STUB**
- ⬜ Faturamento semanal
- ⬜ Lucro estimado do período
- ⬜ Top 5 produtos mais vendidos
- ⬜ Top 5 produtos mais lucrativos
- ⬜ Bottom 5 produtos menos rentáveis
- ⬜ Receitas que consomem mais tempo
- ⬜ Custo médio de mão de obra
- ⬜ Horas trabalhadas na semana
- ⬜ Gastos do mês
- 🟡 Alertas de estoque crítico — existe na tela `/estoque`, falta agregar no dashboard
- ⬜ Pedidos pendentes com prazo próximo

#### Lista Inteligente de Compras (PRD §7) ⬜ **NÃO IMPLEMENTADO**
- ⬜ Previsão de consumo com base em pedidos futuros
- ⬜ Sugestão automática de recompra quando atinge estoque mínimo
- ⬜ Geração de lista consolidada (exportável)
- ⬜ Notificação push/email de estoque baixo

### Qualidade — Testes (CLAUDE.md §10)

| Módulo | Meta | Atual |
|---|---|---|
| Motor de cálculo | 95% | ✅ ~98% (38 testes) |
| Services de domínio | 80% | ⬜ 0% (auth, receitas, estoque, configurações sem testes) |
| Rotas de API | 70% | ⬜ 0% (apenas smoke tests manuais via curl) |
| OCR adapters | 60% | ⬜ 0% (sem testes do `gemma_adapter`) |
| Frontend | — | 🟡 só `utils.test.ts`; componentes e hooks sem testes |

### Qualidade — Segurança e Observabilidade

- ⬜ **Rate limiting** nas rotas de auth e OCR (`slowapi` instalado mas não aplicado — CLAUDE.md §7 exige)
- ⬜ **Sentry** ativo — configurado mas só liga com `SENTRY_DSN` preenchido
- ⬜ Validação de **tamanho de upload** (fotos de receita, imagens de cupom)
- ⬜ Política de **CORS produção** (hoje aceita qualquer IP de rede local — bom para dev, perigoso em prod)
- ⬜ Audit log estruturado das ações sensíveis (CLAUDE.md §13: campos `tenant_id`, `user_id`, `action`, `entity`, `entity_id` em todos os services — alguns ainda não logam)

### Qualidade — Performance e UX

- ⬜ **Recálculo de custo via Celery** (hoje síncrono no request) — PRD §1.1 implica reprocessamento em massa quando ingrediente muda de preço
- ⬜ **Offline-first** (CLAUDE.md §14): service workers + IndexedDB + sync queue para cadastro de receita e entrada de compra
- ⬜ Imagens otimizadas (Next/Image + CDN ou storage local)
- ⬜ Lazy loading das rotas pesadas (formulário de receita carrega `useIngredientes` e `useEtapasPadrao` em série)

### Monetização (PRD §Modelo Comercial)

- ⬜ Integração Stripe (variáveis no `.env.example` já preparadas)
- ⬜ Tabela `assinaturas` e middleware de verificação de plano ativo
- ⬜ Tela de planos (Starter R$29 / Pro R$59 / Studio R$99)
- ⬜ Trial de 14 dias sem cartão
- ⬜ Limitação por plano (Starter: 20 receitas; Pro: ilimitado; Studio: múltiplos usuários)
- ⬜ Webhook de eventos de assinatura (Stripe → backend)

---

## Fase 2 — Pós-MVP (PRD §Funcionalidades Futuras)

### WhatsApp Business Integration
- ⬜ Webhook recebendo mensagens do WhatsApp
- ⬜ Geração automática de orçamento formatado
- ⬜ Lembrete de entrega via WhatsApp
- ⬜ Cobrança automática via link de pagamento

### IA de Precificação Visual
- ⬜ Endpoint que recebe foto de produto e usa Gemma 4 para sugerir:
  - Categoria
  - Faixa de preço de mercado
  - Complexidade estimada
  - Margem média de similares
  - Tempo estimado de produção

### Sugestão de Produção
- ⬜ Modelo de previsão de demanda por sazonalidade
- ⬜ Sugestão de quantidade ideal por produto baseado em histórico
- ⬜ Sugestão de produção antecipada

---

## Fase 3 — Avançado (PRD §Funcionalidades Futuras)

### Módulo Fiscal
- ⬜ Emissão de NFS-e (nota de serviço)
- ⬜ Emissão de NFC-e (cupom fiscal eletrônico)
- ⬜ Integração simplificada para MEI/ME

### Integrações
- ⬜ iFood (catálogo + pedidos)
- ⬜ WhatsApp Business API oficial
- ⬜ Instagram (catálogo de produtos)

---

## Backlog técnico (débitos identificados durante a Sprint 1)

- 🐛 `formatDecimal` ainda exportada mas só `tests/utils.test.ts` usa — considerar remover após auditoria
- 🐛 Dashboard atual (`/`) é só atalhos — virar dashboard financeiro de verdade quando dados existirem
- 🐛 Hot reload do Next.js às vezes mantém cache `.next` stale → mitigado com `.\fornada.ps1 reset-frontend`
- 📝 Faltam **README.md** e **CONTRIBUTING.md** no repositório público
- 📝 Documentação OpenAPI já é gerada pelo FastAPI em `/docs` mas falta agrupar tags com descrições
- 🔧 Adicionar GitHub Actions: rodar `pytest` + `pnpm tsc --noEmit` em PRs (sugestão pendente desde o push)
- 🔧 `factory-boy` instalado mas sem factories criadas — usar quando começar testes de integração
- 🎨 Página `/configuracoes/etapas` não permite editar etapa existente (só criar e deletar)
- 🎨 Listagem de receitas não tem filtro/busca (terá relevância quando >20 receitas)

---

## Como atualizar este arquivo

Ao concluir uma tarefa, troque ⬜ por ✅ (ou 🟡 se ficou parcial). Quando criar funcionalidade nova fora deste plano, adicione na seção apropriada com a marcação inicial. Mantenha o foco: **MVP fecha primeiro, depois Fase 2**.
