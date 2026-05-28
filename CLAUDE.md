# CLAUDE.md — Fornada

> Instruções permanentes para o Claude Code neste projeto.
> Leia este arquivo integralmente antes de qualquer ação.
> Para contexto de produto, regras de negócio e escopo do MVP, consulte PRD.md.

---

## 1. Identidade do Projeto

**Fornada** é um ERP simplificado e inteligente para confeiteiras artesanais.

- Público: home bakers, boleiras, confeiteiras de produção sob encomenda
- Proposta: "Você produz. O sistema organiza."
- Paradigma: mobile-first, linguagem simples, zero jargão técnico/contábil
- Modelo: SaaS multi-tenant com planos Starter, Pro e Studio

---

## 2. Stack Obrigatória

### Frontend

| Camada | Tecnologia |
|--------|------------|
| Framework | Next.js (App Router) |
| Linguagem | TypeScript (strict mode) |
| Estilização | Tailwind CSS |
| Componentes | shadcn/ui como base |
| Estado global | Zustand |
| Formulários | React Hook Form + Zod |
| Fetch | TanStack Query (React Query) |
| Testes | Vitest + Testing Library |

### Backend

| Camada | Tecnologia |
|--------|------------|
| Framework | FastAPI |
| Linguagem | Python 3.12+ |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validação | Pydantic v2 |
| Tarefas assíncronas | Celery + Redis |
| Cache | Redis |
| Testes | pytest + pytest-asyncio |
| Logging | structlog |
| Monitoramento | Sentry |

### Banco de Dados

- **Principal:** PostgreSQL (multi-tenant por `tenant_id` em todas as tabelas)
- **Cache e filas:** Redis

### IA e OCR

| Função | Tecnologia |
|--------|------------|
| OCR principal | Gemma 4 Vision via Google AI Studio API |
| Matching de ingredientes | Similaridade semântica + regras de normalização |

> **Decisão (Mai 2026):** Gemma 4 substituiu Google Vision API + Tesseract + OpenAI GPT-4o Vision.
> Motivo: qualidade equivalente, menos dependências externas, usuário já tem API key (`GOOGLE_AI_API_KEY`).
> Adapter em `infrastructure/ocr/gemma_adapter.py`. Mock automático quando sem API key.

---

## 3. Arquitetura

### Estrutura de Pastas (Backend)

```
fornada/
├── api/
│   ├── routers/          # endpoints FastAPI por domínio
│   └── dependencies.py   # injeção de dependências, auth
├── core/
│   ├── config.py         # settings via pydantic-settings
│   ├── security.py       # JWT, hash de senhas
│   └── logging.py        # configuração do structlog
├── domain/
│   ├── receitas/         # entidades, schemas, services, repo
│   ├── estoque/
│   ├── pedidos/
│   ├── financeiro/
│   └── usuarios/
├── infrastructure/
│   ├── database/         # models SQLAlchemy, session
│   ├── ocr/              # adapters Google Vision, Tesseract
│   ├── cache/            # Redis
│   └── celery/           # tasks assíncronas
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── alembic/
├── main.py
└── pyproject.toml
```

### Estrutura de Pastas (Frontend)

```
fornada-web/
├── app/
│   ├── (auth)/           # login, cadastro, recuperação de senha
│   ├── (dashboard)/      # área logada
│   │   ├── receitas/
│   │   ├── estoque/
│   │   ├── pedidos/
│   │   ├── compras/
│   │   └── financeiro/
│   └── layout.tsx
├── components/
│   ├── ui/               # shadcn/ui base
│   └── shared/           # componentes reutilizáveis do Fornada
├── lib/
│   ├── api.ts            # cliente HTTP configurado
│   └── utils.ts
├── hooks/                # custom hooks
├── stores/               # Zustand stores
├── types/                # tipos TypeScript globais
└── tests/
```

### Princípios Arquiteturais

- Arquitetura hexagonal (ports & adapters) no backend
- Domínio isolado de infraestrutura — services não importam diretamente ORM ou HTTP
- Multi-tenancy por `tenant_id` em todas as tabelas — toda query obrigatoriamente filtra por tenant
- Separação clara entre: motor de cálculo de custos, motor de precificação, módulo OCR, módulo IA

---

## 4. Multi-tenancy — Regra Crítica

Toda tabela que contém dados de negócio **obrigatoriamente** possui a coluna `tenant_id UUID NOT NULL`.

Toda query de leitura ou escrita **obrigatoriamente** inclui filtro `WHERE tenant_id = :current_tenant_id`.

**Nunca** criar uma rota que acesse dados sem validar o tenant do usuário autenticado.

Se houver qualquer dúvida sobre isolamento entre tenants, pare e questione antes de implementar.

---

## 5. Convenções de Código

### Python / Backend

- Type hints obrigatórios em todas as funções e métodos
- Docstrings em services e funções de domínio
- Nunca retornar modelos SQLAlchemy diretamente nas rotas — sempre serializar via Pydantic schema
- Exceções de negócio via classes customizadas em `domain/exceptions.py`
- Logs sempre via `structlog` — nunca `print()` ou `logging` direto
- Variáveis de ambiente apenas via `core/config.py` (pydantic-settings) — nunca `os.environ` direto

### TypeScript / Frontend

- Strict mode ativo — nunca usar `any`
- Componentes sempre com tipagem explícita de props
- Nunca fazer fetch diretamente em componentes — usar hooks ou TanStack Query
- Textos da interface sempre em português do Brasil
- Valores monetários sempre formatados como `R$ 0,00` — usar `Intl.NumberFormat('pt-BR')`
- Unidades de medida e pesos sempre com vírgula decimal (padrão pt-BR)

### Nomenclatura

| Contexto | Padrão |
|----------|--------|
| Arquivos Python | `snake_case.py` |
| Classes Python | `PascalCase` |
| Funções e variáveis Python | `snake_case` |
| Arquivos TypeScript | `kebab-case.tsx` |
| Componentes React | `PascalCase` |
| Hooks | `useNomeDoHook` |
| Stores Zustand | `useNomeStore` |
| Tabelas banco | `snake_case` no plural |
| Colunas banco | `snake_case` |

---

## 6. Banco de Dados — Convenções

- Toda migration gerada via Alembic — nunca alterar schema manualmente
- Toda tabela obrigatoriamente possui: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()`
- Soft delete: coluna `deleted_at TIMESTAMPTZ NULL` — nunca deletar fisicamente dados de negócio
- Índices obrigatórios: `tenant_id`, colunas usadas em filtros frequentes
- Nunca usar `CASCADE DELETE` sem aprovação explícita

---

## 7. Autenticação e Segurança

- JWT com access token (15 min) e refresh token (7 dias) armazenado em cookie httpOnly
- Senhas com bcrypt (custo mínimo 12)
- Toda rota autenticada valida `tenant_id` do token contra o recurso solicitado
- Nunca expor IDs sequenciais — sempre UUID nas URLs e respostas da API
- Rate limiting nas rotas de auth e OCR

---

## 8. Motor de Cálculo — Regras de Negócio

O motor de cálculo de custos e precificação é o coração do produto. Trate-o com cuidado máximo.

### Componentes do Custo de uma Receita

```
Custo Total = Custo de Ingredientes
            + Custo de Embalagem
            + Custo Operacional Rateado (energia, gás, água)
            + Custo de Mão de Obra Direta
            + Custo de Mão de Obra Indireta (rateado)
```

### Custo por Unidade

```
Custo por Unidade = Custo Total / Rendimento da Receita
```

### Preço Mínimo de Venda

```
Preço Mínimo = Custo por Unidade
```

### Preço Recomendado

```
Preço Recomendado = Custo por Unidade / (1 - Margem Desejada)
```

### Custo de Mão de Obra

```
Custo MO por Receita = (Tempo Ativo em Horas) × (Valor/Hora configurado pela usuária)
```

### Custo Operacional Rateado

```
Custo Op/hora = Custo Mensal Operacional / Horas Mensais Trabalhadas
Custo Op por Receita = Custo Op/hora × Tempo Total da Receita em Horas
```

### Recálculo Automático

O motor recalcula automaticamente toda vez que:
- Custo de qualquer ingrediente mudar (nova compra)
- Tempo operacional de uma etapa for editado
- Valor/hora da usuária for atualizado
- Custo mensal operacional for atualizado

---

## 9. OCR e Entrada de Compras

### Fluxo

1. Usuária fotografa cupom ou escaneia QR Code da NFCe
2. Backend recebe imagem/QR Code via endpoint dedicado
3. Celery task processa OCR de forma assíncrona
4. Sistema extrai itens, quantidades e preços
5. Matching com ingredientes cadastrados (fuzzy + normalização de unidades)
6. Sugestão de categorização para itens não reconhecidos
7. Usuária confirma ou corrige antes de salvar
8. Estoque atualizado e custo médio recalculado

### Regra de Custo Médio

```
Custo Médio Novo = (Estoque Atual × Custo Médio Atual + Quantidade Nova × Preço Novo)
                  / (Estoque Atual + Quantidade Nova)
```

---

## 10. Protocolo de Testes

### Antes de qualquer commit

```bash
# Backend
cd backend
pytest --tb=short -q

# Frontend
cd frontend
pnpm test --run
pnpm tsc --noEmit
```

Não fazer commit com testes falhando. Se um teste pré-existente falhar por mudança de comportamento intencional, atualizar o teste e documentar o motivo.

### Cobertura mínima por módulo

| Módulo | Cobertura mínima |
|--------|-----------------|
| Motor de cálculo de custos | 95% |
| Motor de precificação | 95% |
| Services de domínio | 80% |
| Rotas de API | 70% |
| OCR adapters | 60% (mocks aceitáveis) |

---

## 11. Protocolo de Revisão de Código

Sempre que solicitada revisão, ou antes de concluir uma implementação, checar:

- O isolamento de tenant está garantido em todas as queries?
- O motor de cálculo foi afetado? Se sim, os testes cobrem os novos cenários?
- Há type hints em tudo?
- Há algum `print()` ou `os.environ` no código novo?
- A interface usa linguagem simples, sem jargão técnico ou contábil?
- Valores monetários estão formatados corretamente em pt-BR?

---

## 12. Variáveis de Ambiente

Nunca hardcodar segredos. Toda configuração sensível via `.env` com `pydantic-settings`.

Arquivo `.env.example` deve estar sempre atualizado com todas as variáveis necessárias (sem valores reais).

Variáveis obrigatórias para o projeto funcionar:

```
DATABASE_URL=
REDIS_URL=
SECRET_KEY=
GOOGLE_VISION_API_KEY=
OPENAI_API_KEY=
SENTRY_DSN=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

---

## 13. Logging e Observabilidade

- Logs estruturados via `structlog` em todos os services e tasks
- Campos obrigatórios nos logs: `tenant_id`, `user_id`, `action`, `entity`, `entity_id`
- Erros de OCR logam também: `source` (google_vision | tesseract | openai), `confidence`, `raw_text`
- Erros de cálculo logam: `receita_id`, `ingredientes`, `parametros_utilizados`
- Sentry configurado para capturar exceções não tratadas em produção

---

## 14. Filosofia do Produto — Nunca Esquecer

O Fornada é usado por pessoas que não são técnicas e estão no celular entre uma produção e outra.

- Toda mensagem de erro deve ser em português, clara e acionável
- Nenhum campo de formulário pode ter label técnico sem explicação
- O sistema deve confirmar ações destrutivas (ex: remover ingrediente de receita)
- Fluxos críticos (cadastro de receita, entrada de compra) devem funcionar offline com sincronização posterior — planejar para isso desde a arquitetura
- Performance mobile é requisito, não detalhe — testar sempre em viewport de 390px

---

## 15. Comandos Úteis

```bash
# Backend — iniciar dev
uvicorn main:app --reload --port 8000

# Backend — rodar migrations
alembic upgrade head

# Backend — gerar migration
alembic revision --autogenerate -m "descricao"

# Backend — testes
pytest -v

# Backend — testes com cobertura
pytest --cov=. --cov-report=term-missing

# Frontend — iniciar dev
pnpm dev

# Frontend — build
pnpm build

# Frontend — testes
pnpm test

# Docker — subir ambiente completo
docker compose up -d
```