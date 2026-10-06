# Fornada

ERP para confeiteiras artesanais: receitas e precificação, ingredientes e estoque,
pedidos, ordens de produção, produto acabado, vendas, compras e agenda.

Frontend Next.js/TypeScript; API FastAPI/Python; PostgreSQL; Redis e Celery.

## Desenvolvimento

Copie `.env.example` para `.env`, preencha as configurações e execute:

```powershell
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Frontend: http://localhost:3000. API: http://localhost:8000/docs.

## Produção

Consulte [o procedimento de publicação](deploy/README.md) e
[o diagnóstico de prontidão](docs/status-2026-10-06.md).
O Compose de desenvolvimento não é o ambiente de publicação.
