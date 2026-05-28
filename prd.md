# PRD — ERP Inteligente para Confeitarias Artesanais

**Status:** Draft v1.0  
**Data:** Maio 2026  
**Responsável:** A definir  

---

## Nome do Produto

Candidatos em avaliação:

| Nome | Observação |
|------|------------|
| Bely ERP | Sonoro, feminino, direto |
| CakeFlow | Inglês, bom para posicionamento premium |
| Fornada | Conceito forte, memorizável |
| Mise | Curto, referência culinária (mise en place) |
| Confeita | Derivado direto do público |
| Batch | Técnico, interessante para fase 2+ |

> Recomendação inicial: **Fornada** ou **Mise** pela diferenciação. Decisão a validar com público-alvo.

---

## Visão do Produto

ERP simplificado e inteligente para confeiteiras, boleiras e pequenos negócios de produção artesanal. O foco não é contabilidade tradicional nem gestão corporativa.

**Proposta central:**

> "Você produz. O sistema organiza."

O sistema deve parecer um assistente operacional, não um software de gestão.

---

## Problema

### Dores recorrentes do público

- Precificação incorreta (vende sem saber o custo real)
- Falta de controle de estoque
- Desperdício de ingredientes
- Ausência de controle financeiro
- Dificuldade em calcular lucro real
- Receitas despadronizadas entre produções
- Compras desorganizadas
- Excesso de trabalho manual
- Baixa familiaridade com ERPs tradicionais

### Por que os sistemas atuais não funcionam

Os ERPs existentes exigem cadastro manual excessivo, conhecimento técnico, processos burocráticos e muito tempo operacional. O público-alvo quer simplicidade, rapidez e automação, não mais uma planilha ou sistema complexo para aprender.

---

## Objetivo do Produto

Criar uma plataforma extremamente simples que:

- Controle estoque automaticamente
- Calcule custo real de receitas
- Sugira preços de venda com margem saudável
- Registre compras via câmera (sem digitação)
- Reduza tempo operacional ao mínimo
- Funcione majoritariamente pelo celular
- Ajude o usuário a entender seu lucro real

---

## Público-Alvo

### Primário

- Confeiteiras artesanais
- Boleiras (produção sob encomenda)
- Doces personalizados
- Home bakers

### Secundário

- Cafeterias pequenas
- Docerias
- Microproduções alimentícias
- Produtores de salgados
- Pequenos buffets

### Perfil comportamental

O público primário tem baixa tolerância a complexidade, usa principalmente o celular, vende pelo Instagram e WhatsApp, e não tem familiaridade com termos contábeis ou financeiros. Quer resultado, não processo.

---

## Diferencial Competitivo

### Conceito: "ERP Invisível"

O sistema executa automaticamente tarefas que normalmente exigem cadastro manual. O usuário não percebe que está usando um ERP.

| Diferencial | Descrição |
|-------------|-----------|
| Entrada de compras via câmera | Foto do cupom ou QR Code da NFCe |
| Controle automático de estoque | Baixa ao registrar produção ou venda |
| Precificação inteligente | Considera todos os custos, incluindo mão de obra |
| Cálculo de tempo operacional | Tempo ativo, passivo e custo por hora |
| Mobile-first | Projetado para uso 100% no celular |
| Linguagem simples | Zero jargão contábil ou técnico |
| Dashboard emocional | Informações visuais e motivadoras |
| IA aplicada à operação | Categorização, sugestões e alertas automáticos |

---

## Funcionalidades do MVP

### 1. Cadastro de Receitas

**Objetivo:** Criar receitas padronizadas com custo automático calculado.

**Campos:**

- Nome da receita
- Categoria
- Rendimento (quantidade de unidades)
- Lista de ingredientes com quantidade e unidade de medida
- Etapas operacionais com tempo estimado por etapa
- Foto do produto

**Cálculos automáticos exibidos:**

| Indicador | Descrição |
|-----------|-----------|
| Custo dos ingredientes | Soma dos insumos com base no estoque |
| Custo operacional rateado | Energia, gás, água, taxas |
| Custo de mão de obra | Baseado no valor/hora configurado |
| Tempo total de produção | Soma das etapas |
| Tempo ativo vs. passivo | Diferenciação de tempo com e sem atenção |
| Custo por unidade | Custo total / rendimento |
| Lucro estimado | Baseado no preço de venda informado |
| Margem estimada | Em percentual |
| Preço mínimo de venda | Custo total sem margem |
| Preço recomendado | Com margem configurada pelo usuário |

**Regra de recálculo:**

O sistema recalcula automaticamente custo, margem e preço recomendado sempre que:
- Um ingrediente mudar de preço
- O tempo operacional for alterado
- O valor/hora da usuária for atualizado

---

#### 1.1 Controle de Tempo Operacional

Cada receita pode ter etapas com duração estimada.

**Exemplos de etapas:**
- Preparo da massa
- Recheio
- Montagem
- Decoração
- Embalagem
- Finalização

**Classificação de mão de obra:**

**Direta** — tempo gasto diretamente na fabricação do produto:
- Preparo, montagem, decoração, finalização

**Indireta** — tempo operacional não ligado à fabricação individual:
- Limpeza, organização, compras, atendimento, embalagem geral

---

#### 1.2 Configuração de Custo de Hora Trabalhada

A usuária configura:

- Valor da hora de trabalho (R$/h)
- Custo mensal operacional fixo (energia, gás, água, aluguel)
- Carga horária média mensal

O sistema usa esses dados para calcular o custo operacional rateado por receita e o valor financeiro real do tempo investido.

---

### 2. Controle de Estoque

**Objetivo:** Automatizar o controle de ingredientes sem digitação manual.

**Campos por ingrediente:**

- Nome
- Unidade de medida
- Estoque atual
- Estoque mínimo (gatilho de alerta)
- Custo médio (atualizado a cada compra)
- Histórico de movimentação

**Regra:** O estoque é baixado automaticamente após o registro de produção ou venda.

---

### 3. Entrada de Compras via Câmera

**Objetivo:** Eliminar a digitação manual de notas fiscais.

**Formas de entrada:**

1. Leitura de QR Code da NFCe
2. Upload de XML da nota fiscal
3. OCR de cupom fiscal fotografado

**Fluxo:**

```
Usuária fotografa cupom / escaneia QR Code
        ↓
Sistema lê os itens da nota
        ↓
Identifica e associa ingredientes cadastrados
        ↓
Sugere categorização para itens novos
        ↓
Atualiza estoque automaticamente
        ↓
Recalcula custo médio dos ingredientes
```

---

### 4. Precificação Inteligente

**Objetivo:** Garantir que o preço de venda cubra todos os custos reais e gere lucro.

**Componentes do custo considerados:**

- Ingredientes
- Embalagem
- Gás
- Energia
- Água
- Mão de obra direta
- Mão de obra indireta (rateada)
- Tempo operacional total
- Taxas iFood (quando aplicável)
- Taxas de cartão (quando aplicável)
- Margem desejada configurável

**Resultado exibido:**

| Indicador | Valor |
|-----------|-------|
| Custo real total | R$ — |
| Preço mínimo | R$ — |
| Preço recomendado | R$ — |
| Lucro estimado | R$ — |
| Margem | % |
| Custo por hora produzida | R$/h |
| Lucro por minuto de produção | R$/min |

---

### 5. Gestão de Pedidos

**Objetivo:** Registrar e acompanhar pedidos de forma simples.

**Campos:**

- Cliente
- Data de entrega
- Produto(s) solicitado(s)
- Valor combinado
- Observações
- Foto de referência (opcional)

**Status do pedido:**

```
Orçamento → Aprovado → Em Produção → Finalizado → Entregue
```

---

### 6. Dashboard Financeiro Simplificado

**Objetivo:** Mostrar o que importa sem jargão contábil.

**Indicadores exibidos:**

- Faturamento semanal
- Lucro estimado do período
- Produtos mais vendidos
- Produtos mais lucrativos
- Produtos menos rentáveis
- Receitas que consomem mais tempo
- Custo médio de mão de obra
- Horas trabalhadas na semana
- Gastos do mês
- Alertas de estoque crítico
- Pedidos pendentes com prazo próximo

---

### 7. Lista Inteligente de Compras

**Objetivo:** Antecipar falta de ingredientes antes que vire problema.

**Funcionalidades:**

- Previsão de consumo com base em pedidos futuros
- Sugestão automática de recompra ao atingir estoque mínimo
- Geração de lista de compras consolidada
- Alertas de estoque baixo com notificação

---

## Funcionalidades Futuras

### Fase 2

#### WhatsApp Business Integration

- Criação de pedidos direto pelo WhatsApp
- Envio automático de orçamento formatado
- Lembrete automático de entrega
- Cobrança automática via link de pagamento

#### IA de Precificação Visual

Usuária tira foto de um bolo. Sistema sugere:

- Categoria do produto
- Faixa de preço de mercado
- Complexidade estimada
- Margem média de produtos similares
- Tempo estimado de produção

#### Sugestão de Produção

- Quantidade ideal por produto
- Previsão de demanda por sazonalidade
- Sugestão de produção antecipada

---

### Fase 3

#### Módulo Fiscal

- Emissão de NFS-e (nota de serviço)
- Emissão de NFC-e (cupom fiscal eletrônico)
- Integração fiscal simplificada para MEI e ME

#### Delivery e Integrações

- Integração com iFood
- Integração com WhatsApp Business API
- Integração com Instagram (catálogo de produtos)

---

## Requisitos Técnicos

### Frontend

| Item | Decisão |
|------|---------|
| Prioridade | Mobile-first (absoluta) |
| Framework | React + Next.js |
| Estilização | Tailwind CSS |
| Paradigma | SPA com navegação fluida, sem carregamentos de página |

### Backend

| Item | Decisão |
|------|---------|
| Framework | FastAPI (Python) |
| Alternativa | Django Ninja |
| Autenticação | JWT + sessão segura |
| Banco de dados | PostgreSQL |
| Cache / filas | Redis + Celery (processamento de OCR assíncrono) |

### IA e OCR

| Componente | Tecnologia |
|------------|------------|
| OCR principal | Google Vision API |
| OCR fallback | Tesseract (open source) |
| OCR avançado | OpenAI Vision (GPT-4o) |
| NLP / categorização | Modelo próprio fine-tuned ou prompt engineering |
| Matching de ingredientes | Similaridade semântica + regras |

### Arquitetura

Arquitetura hexagonal (ports & adapters), separando claramente:

- Domínio (receitas, estoque, pedidos, financeiro)
- Motor de cálculo de custos
- Motor de precificação
- Módulo de OCR e leitura de NFCe
- Módulo de IA e sugestões
- Integrações externas (WhatsApp, iFood, fiscal)
- Automações e tarefas assíncronas

---

## Modelo Comercial

### Planos SaaS (mensalidade)

| Plano | Preço | Público-alvo |
|-------|-------|-------------|
| Starter | R$ 29/mês | Home baker iniciante, até 20 receitas |
| Pro | R$ 59/mês | Confeiteira ativa, produção regular |
| Studio | R$ 99/mês | Pequena confeitaria, múltiplos usuários |

> Sugestão: oferecer trial de 14 dias sem cartão para reduzir fricção de aquisição.

### Canal Principal de Aquisição

Instagram + WhatsApp, com conteúdo mostrando:

- Antes/depois da gestão com o sistema
- Precificação errada e quanto dinheiro isso custa
- Desperdício oculto de ingredientes
- Automação real (vídeo da câmera lendo cupom)
- Lucro invisível perdido em mão de obra não cobrada

---

## Métricas de Sucesso (KPIs)

| KPI | Meta inicial |
|-----|-------------|
| Tempo médio de cadastro de compra | Menor que 60 segundos |
| Receitas cadastradas por usuária | Maior que 5 no primeiro mês |
| Retenção mensal (MRR retention) | Maior que 85% |
| Usuários ativos semanalmente | Maior que 60% da base |
| Pedidos registrados por usuária/mês | Maior que 10 |
| NPS | Maior que 50 |

---

## Premissas e Restrições

- O produto deve funcionar 100% pelo celular sem perda de funcionalidade
- A linguagem da interface nunca deve usar termos contábeis sem explicação
- O cadastro inicial (onboarding) deve ser concluído em menos de 10 minutos
- O sistema não deve exigir conhecimento prévio de gestão para ser usado
- Integrações fiscais (NFS-e, NFC-e) ficam fora do MVP

---

## Próximos Passos

- [ ] Definir nome do produto
- [ ] Validar proposta com 5 a 10 confeiteiras reais (discovery)
- [ ] Criar protótipo navegável das telas principais
- [ ] Definir stack definitiva e repositório
- [ ] Criar CLAUDE.md do projeto para desenvolvimento com Claude Code
- [ ] Iniciar Sprint 1: autenticação, cadastro de receitas e estoque básico