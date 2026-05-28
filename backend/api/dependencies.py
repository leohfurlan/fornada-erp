from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import JWTError, decode_token
from domain.usuarios.repository import UsuarioRepository
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Valida o JWT e retorna o usuário autenticado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exception

    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_id(user_id, tenant_id)
    if not usuario or not usuario.ativo:
        raise credentials_exception

    return usuario


def get_tenant_id(current_user: Usuario = Depends(get_current_user)) -> UUID:
    """Extrai o tenant_id do usuário autenticado."""
    return current_user.tenant_id
