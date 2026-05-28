from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Tenant, Usuario


class UsuarioRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def criar_tenant(self, nome: str, plano: str = "starter") -> Tenant:
        tenant = Tenant(nome=nome, plano=plano)
        self._db.add(tenant)
        await self._db.flush()
        return tenant

    async def criar_usuario(
        self,
        tenant_id: UUID,
        email: str,
        senha_hash: str,
        nome: str,
    ) -> Usuario:
        usuario = Usuario(
            tenant_id=tenant_id,
            email=email,
            senha_hash=senha_hash,
            nome=nome,
        )
        self._db.add(usuario)
        await self._db.flush()
        return usuario

    async def buscar_por_email(self, email: str) -> Usuario | None:
        result = await self._db.execute(
            select(Usuario).where(Usuario.email == email, Usuario.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def buscar_por_id(self, usuario_id: UUID, tenant_id: UUID) -> Usuario | None:
        result = await self._db.execute(
            select(Usuario).where(
                Usuario.id == usuario_id,
                Usuario.tenant_id == tenant_id,
                Usuario.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
