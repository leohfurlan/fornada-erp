"""Login por posse de telefone, sem vincular contas pelo e-mail informado."""
import secrets
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from core.config import settings
from core.rate_limit import limiter
from core.security import hash_password
from domain.exceptions import AuthError, ConflictError
from domain.usuarios.otp import OtpService
from domain.usuarios.repository import UsuarioRepository
from domain.usuarios.schemas import TokenResponse, UsuarioResponse
from domain.usuarios.service import UsuarioService
from domain.usuarios.telefone import normalizar_telefone
from domain.usuarios.whatsapp_schemas import (
    CadastroWhatsappRequest, DesafioResponse, LoginWhatsappResponse,
    ProvaRequest, SolicitarCodigo, VerificacaoResponse, VerificarCodigo,
)
from infrastructure.cache.otp_store import RedisOtpStore
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db
from infrastructure.whatsapp.evolution import EvolutionSender

router = APIRouter(prefix="/auth/whatsapp", tags=["Autenticação WhatsApp"])


async def get_otp_service() -> AsyncGenerator[OtpService, None]:
    """Falha fechada até transporte e cache estarem configurados."""
    if not settings.whatsapp_auth_enabled or not all((settings.evolution_api_url, settings.evolution_api_key, settings.evolution_instance)):
        raise HTTPException(503, "Acesso por WhatsApp ainda não está disponível. Use o acesso por e-mail.")
    redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3)
    try:
        yield OtpService(RedisOtpStore(redis), EvolutionSender(settings.evolution_api_url, settings.evolution_api_key, settings.evolution_instance), settings.secret_key)
    except (RedisError, httpx.HTTPError):
        raise HTTPException(503, "Não foi possível concluir o envio ou a validação. Tente novamente em alguns instantes.") from None
    finally:
        await redis.aclose()


@router.get("/disponibilidade")
async def disponibilidade() -> dict[str, bool]:
    """Expõe somente disponibilidade configurada, sem credenciais."""
    return {"ativo": settings.whatsapp_auth_enabled and bool(settings.evolution_api_url and settings.evolution_api_key and settings.evolution_instance)}


@router.post("/solicitar", response_model=DesafioResponse)
@limiter.limit("5/minute")
async def solicitar(request: Request, data: SolicitarCodigo, otp: OtpService = Depends(get_otp_service)) -> DesafioResponse:
    telefone = normalizar_telefone(data.telefone, data.regiao)
    desafio = await otp.solicitar(telefone, request.client.host if request.client else "unknown")
    return DesafioResponse(desafio=desafio)


@router.post("/verificar", response_model=VerificacaoResponse)
@limiter.limit("20/minute")
async def verificar(request: Request, data: VerificarCodigo, otp: OtpService = Depends(get_otp_service)) -> VerificacaoResponse:
    return VerificacaoResponse(prova=await otp.verificar(data.desafio, data.codigo))


@router.post("/entrar", response_model=LoginWhatsappResponse)
@limiter.limit("10/minute")
async def entrar(request: Request, data: ProvaRequest, otp: OtpService = Depends(get_otp_service), db: AsyncSession = Depends(get_db)) -> LoginWhatsappResponse:
    telefone = await otp.consumir_prova(data.prova)
    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_telefone(telefone)
    if usuario:
        if not usuario.ativo:
            raise AuthError("Conta desativada. Entre em contato com o suporte.")
        return LoginWhatsappResponse(tokens=UsuarioService(repo)._gerar_tokens(usuario))
    prova = secrets.token_urlsafe(32)
    await otp.store.guardar_prova(otp.digest(prova), telefone)
    return LoginWhatsappResponse(onboarding_prova=prova)


@router.post("/cadastro", response_model=TokenResponse, status_code=201)
@limiter.limit("5/hour")
async def cadastrar(request: Request, data: CadastroWhatsappRequest, otp: OtpService = Depends(get_otp_service), db: AsyncSession = Depends(get_db)) -> TokenResponse:
    repo = UsuarioRepository(db)
    if await repo.buscar_por_email(str(data.email)):
        raise ConflictError("Este e-mail já tem uma conta. Entre por e-mail e vincule o WhatsApp nas configurações.")
    telefone = await otp.consumir_prova(data.prova)
    if await repo.buscar_por_telefone(telefone):
        raise ConflictError("Este WhatsApp já está vinculado. Solicite um novo código para entrar.")
    try:
        tenant = await repo.criar_tenant(data.nome_negocio)
        tenant.endereco = data.endereco.model_dump()
        usuario = await repo.criar_usuario(tenant.id, str(data.email), hash_password(secrets.token_urlsafe(48)), data.nome)
        usuario.telefone = telefone
        await db.flush()
        tokens = UsuarioService(repo)._gerar_tokens(usuario)
        await db.commit()
        return tokens
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Conta já cadastrada. Solicite um novo código para entrar ou use o acesso por e-mail.") from None


@router.post("/vincular", response_model=UsuarioResponse)
async def vincular(data: ProvaRequest, usuario: Usuario = Depends(get_current_user), otp: OtpService = Depends(get_otp_service), db: AsyncSession = Depends(get_db)) -> UsuarioResponse:
    """Conta atual autenticada e telefone verificado: nenhuma associação por e-mail."""
    telefone = await otp.consumir_prova(data.prova)
    if usuario.telefone and usuario.telefone != telefone:
        raise ConflictError("Esta conta já tem um WhatsApp. A troca de número precisa de recuperação assistida.")
    vinculado = await UsuarioRepository(db).buscar_por_telefone(telefone)
    if vinculado and vinculado.id != usuario.id:
        raise ConflictError("Este WhatsApp já está vinculado a outra conta.")
    usuario.telefone = telefone
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Este WhatsApp já está vinculado a outra conta.") from None
    return UsuarioResponse.model_validate(usuario)
