"""Inicia a API ou o monitor com os arquivos locais de desenvolvimento iFood."""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "backend"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modo", choices=("api", "worker", "once"))
    args = parser.parse_args()
    for name in (".env.ifood.dev.local", ".env.ifood.local"):
        path = root / name
        if not path.is_file():
            parser.error(f"Arquivo local ausente: {name}")
        load_dotenv(path, override=True)

    from sqlalchemy.engine import make_url

    from core.config import settings

    if settings.environment != "development" or make_url(settings.database_url).host not in (
        "127.0.0.1",
        "localhost",
        "::1",
    ):
        parser.error("Este launcher exige desenvolvimento e banco em loopback")
    if args.modo == "api":
        import uvicorn

        uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="warning")
    else:
        from scripts.monitorar_ifood import run

        asyncio.run(run(args.modo == "once"))


if __name__ == "__main__":
    main()
