import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from infrastructure.database.session import Base, get_db
from main import app

# Permite override via env. Default = mesmo host do DATABASE_URL (dev)
# mas com banco /fornada_test isolado para não poluir dados de dev.
_default_db_url = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://fornada:fornada_dev@db:5432/fornada"
)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    _default_db_url.rsplit("/", 1)[0] + "/fornada_test",
)

# NullPool: cada sessão recebe uma conexão nova e fecha ao final. Evita
# erros do tipo "another operation in progress" causados por compartilhamento
# de conexões entre testes assíncronos.
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Session de teste com rollback automático ao fim do teste.

    O schema é gerenciado por Alembic (rode `alembic upgrade head` apontando
    pra fornada_test antes da primeira execução). Cada teste opera em uma
    transação isolada que é descartada no rollback.
    """
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
