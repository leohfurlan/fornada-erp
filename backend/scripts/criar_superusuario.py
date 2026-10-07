"""Cria uma conta administrativa separada, sem promover contas existentes."""

import argparse
import asyncio
import getpass
import sys

import structlog
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from infrastructure.database.models import Tenant, Usuario
from infrastructure.database.session import AsyncSessionLocal


async def criar_superusuario(db: AsyncSession, email: str, nome: str, senha: str) -> Usuario:
    """Cria identidade privilegiada em tenant próprio; duplicidade é um erro."""
    email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    if len(senha) < 16 or len(senha.encode("utf-8")) > 72:
        raise ValueError("Use uma senha de pelo menos 16 caracteres e até 72 bytes.")
    existing = (
        await db.execute(select(Usuario.id).where(func.lower(Usuario.email) == email))
    ).scalar_one_or_none()
    if existing:
        raise ValueError("E-mail já cadastrado. Use uma conta administrativa separada.")
    tenant = Tenant(nome="Administração Fornada")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id,
        email=email,
        nome=nome,
        senha_hash=hash_password(senha),
        is_superuser=True,
    )
    db.add(user)
    await db.flush()
    return user


async def executar(email: str, nome: str, senha: str) -> None:
    async with AsyncSessionLocal() as db:
        user = await criar_superusuario(db, email, nome, senha)
        await db.commit()
        structlog.get_logger(__name__).info(
            "superusuario_criado",
            tenant_id=str(user.tenant_id),
            user_id=str(user.id),
            action="create",
            entity="usuario",
            entity_id=str(user.id),
        )
        sys.stdout.write(f"Conta criada: {user.email}\nID: {user.id}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--nome", default="Administrador Fornada")
    args = parser.parse_args()
    senha = getpass.getpass("Senha administrativa (mínimo 16 caracteres): ")
    if senha != getpass.getpass("Confirme a senha: "):
        parser.error("As senhas não coincidem.")
    try:
        asyncio.run(executar(args.email, args.nome, senha))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
