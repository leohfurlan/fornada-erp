import structlog

from core.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from domain.exceptions import AuthError, ConflictError
from domain.usuarios.repository import UsuarioRepository
from domain.usuarios.schemas import LoginRequest, RegistroRequest, TokenResponse, UsuarioResponse
from infrastructure.database.models import Usuario

logger = structlog.get_logger(__name__)


class UsuarioService:
    def __init__(self, repo: UsuarioRepository) -> None:
        self._repo = repo

    async def registrar(self, data: RegistroRequest) -> TokenResponse:
        """Cria tenant + usuário administrador e retorna tokens JWT."""
        existente = await self._repo.buscar_por_email(data.email)
        if existente:
            raise ConflictError("Já existe uma conta com este e-mail")

        tenant = await self._repo.criar_tenant(nome=data.nome_negocio)
        usuario = await self._repo.criar_usuario(
            tenant_id=tenant.id,
            email=data.email,
            senha_hash=hash_password(data.senha),
            nome=data.nome,
        )

        logger.info(
            "usuario_registrado",
            tenant_id=str(tenant.id),
            user_id=str(usuario.id),
            action="register",
            entity="usuario",
            entity_id=str(usuario.id),
        )

        return self._gerar_tokens(usuario)

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Autentica e retorna tokens JWT."""
        usuario = await self._repo.buscar_por_email(data.email)
        if not usuario or not verify_password(data.senha, usuario.senha_hash):
            raise AuthError("E-mail ou senha incorretos")

        if not usuario.ativo:
            raise AuthError("Conta desativada. Entre em contato com o suporte.")

        logger.info(
            "usuario_login",
            tenant_id=str(usuario.tenant_id),
            user_id=str(usuario.id),
            action="login",
            entity="usuario",
            entity_id=str(usuario.id),
        )

        return self._gerar_tokens(usuario)

    async def renovar_token(self, refresh_token: str) -> TokenResponse:
        """Gera novos tokens a partir de um refresh token válido."""
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthError("Token inválido")
        except JWTError:
            raise AuthError("Token expirado ou inválido")

        from uuid import UUID

        usuario_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

        usuario = await self._repo.buscar_por_id(usuario_id, tenant_id)
        if not usuario or not usuario.ativo:
            raise AuthError("Usuário não encontrado")

        return self._gerar_tokens(usuario)

    def _gerar_tokens(self, usuario: Usuario) -> TokenResponse:
        access = create_access_token(usuario.id, usuario.tenant_id)
        refresh = create_refresh_token(usuario.id, usuario.tenant_id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            usuario=UsuarioResponse.model_validate(usuario),
        )
