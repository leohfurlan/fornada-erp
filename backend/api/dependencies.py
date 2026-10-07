from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import JWTError, decode_token
from domain.usuarios.repository import UsuarioRepository
from infrastructure.database.models import SessaoAdministrativa, Usuario
from infrastructure.database.session import get_db

bearer_scheme = HTTPBearer(auto_error=True)


async def get_authenticated_actor(
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
        raise credentials_exception from None

    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_id(user_id, tenant_id)
    if not usuario or not usuario.ativo:
        raise credentials_exception

    return usuario


async def require_superuser(actor: Usuario = Depends(get_authenticated_actor)) -> Usuario:
    """Verifica privilégio persistido, nunca uma flag enviada pelo cliente."""
    if not actor.is_superuser:
        raise HTTPException(status_code=403, detail="Acesso exclusivo da administração.")
    return actor


async def get_current_user(
    request: Request,
    actor: Usuario = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
    admin_session: UUID | None = Header(default=None, alias="X-Admin-Session"),
) -> Usuario:
    """Mantém filtros de tenant usando uma sessão explícita de suporte."""
    if admin_session is None:
        return actor
    if not actor.is_superuser:
        raise HTTPException(status_code=403, detail="Acesso exclusivo da administração.")
    session = await db.get(SessaoAdministrativa, admin_session)
    if (
        not session
        or session.operador_id != actor.id
        or session.ended_at
        or session.deleted_at
        or session.expires_at <= datetime.now(UTC)
    ):
        raise HTTPException(
            status_code=403, detail="Acesso de suporte encerrado. Volte à administração."
        )
    # Operações de identidade não fazem parte do suporte ao negócio.
    if request.url.path.startswith("/api/v1/auth/") and request.url.path != "/api/v1/auth/me":
        raise HTTPException(
            status_code=403, detail="Encerre o suporte para alterar a identidade da conta."
        )
    target = await UsuarioRepository(db).buscar_por_id(session.usuario_id, session.tenant_id)
    if not target or not target.ativo or target.is_superuser:
        raise HTTPException(status_code=403, detail="Conta indisponível para suporte.")
    structlog.get_logger(__name__).info(
        "acesso_administrativo",
        tenant_id=str(target.tenant_id),
        user_id=str(actor.id),
        target_user_id=str(target.id),
        action=request.method,
        entity="sessao_administrativa",
        entity_id=str(session.id),
        path=request.url.path,
    )
    return target


def get_tenant_id(current_user: Usuario = Depends(get_current_user)) -> UUID:
    """Extrai o tenant_id do usuário autenticado."""
    return current_user.tenant_id
