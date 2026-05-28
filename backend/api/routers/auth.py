from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from domain.usuarios.repository import UsuarioRepository
from domain.usuarios.schemas import (
    LoginRequest,
    RefreshRequest,
    RegistroRequest,
    TokenResponse,
    UsuarioResponse,
)
from domain.usuarios.service import UsuarioService
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db
from api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def get_usuario_service(db: AsyncSession = Depends(get_db)) -> UsuarioService:
    return UsuarioService(UsuarioRepository(db))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def registrar(
    data: RegistroRequest,
    service: UsuarioService = Depends(get_usuario_service),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Cria conta de confeiteira (tenant + usuário administrador)."""
    result = await service.registrar(data)
    await db.commit()
    return result


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    service: UsuarioService = Depends(get_usuario_service),
) -> TokenResponse:
    """Autentica e retorna tokens de acesso."""
    return await service.login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    service: UsuarioService = Depends(get_usuario_service),
) -> TokenResponse:
    """Renova o access token usando o refresh token."""
    return await service.renovar_token(data.refresh_token)


@router.get("/me", response_model=UsuarioResponse)
async def me(current_user: Usuario = Depends(get_current_user)) -> UsuarioResponse:
    """Retorna dados do usuário autenticado."""
    return UsuarioResponse.model_validate(current_user)
