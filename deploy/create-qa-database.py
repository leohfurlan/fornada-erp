"""Cria banco descartável apenas no PostgreSQL de QA local."""
import asyncio
import asyncpg


async def main() -> None:
    connection = await asyncpg.connect(host="127.0.0.1", port=55432, user="postgres", password="fornada_test_only", database="postgres")
    try:
        if not await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", "fornada_test_v2"):
            await connection.execute("CREATE DATABASE fornada_test_v2")
    finally:
        await connection.close()


asyncio.run(main())
