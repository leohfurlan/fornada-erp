"""Alexa account linking and verified request adapter for Modo cozinha."""

import base64
import hashlib
import json
import posixpath
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from api.dependencies import get_authenticated_actor
from core.config import settings
from core.rate_limit import limiter
from domain.cozinha.service import recipe_projection, resume_completion
from domain.cozinha.speech import projection_speech_parts
from domain.receitas.central_snapshot import search
from infrastructure.database.cozinha_models import (
    CozinhaAlexaOAuthContext,
    CozinhaAlexaOAuthGrant,
    CozinhaAlexaRequest,
    CozinhaAlexaVinculo,
    CozinhaEstacao,
)
from infrastructure.database.models import Usuario
from infrastructure.database.session import get_db

router = APIRouter(prefix="/integrations/alexa", tags=["Alexa - Modo cozinha"])
link_router = APIRouter(prefix="/cozinha/alexa", tags=["Vínculo Alexa"])
basic_auth = HTTPBasic(auto_error=False)
# Amazon's opaque OAuth state exceeds 1 KiB in real account-linking requests.
# Keep a bounded input while preserving the complete value for the callback.
MAX_OAUTH_STATE_LENGTH = 8192


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    context_id: UUID
    approve: bool


class DeviceConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pending_device_id: UUID


class StationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    station_id: UUID


def client_origin() -> str:
    parsed = urlsplit(settings.frontend_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _enabled() -> None:
    if not settings.alexa_enabled:
        raise HTTPException(503, detail="A integração Alexa ainda não foi configurada.")


def _oauth_error(error: str, description: str, code: int = 400) -> HTTPException:
    headers = {"WWW-Authenticate": 'Basic realm="alexa-oauth"'} if code == 401 else None
    return HTTPException(
        code,
        detail={"error": error, "error_description": description},
        headers=headers,
    )


def _new_token() -> str:
    return secrets.token_urlsafe(48)


def _scope(value: str | None) -> str:
    allowed = {"cozinha:read", "cozinha:control"}
    scopes = set((value or "").split())
    if not scopes or not scopes <= allowed:
        raise _oauth_error("invalid_scope", "Escopo de acesso não aceito.")
    return " ".join(sorted(scopes))


@router.get("/oauth/authorize")
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str = "cozinha:read cozinha:control",
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    _enabled()
    if response_type != "code" or client_id != settings.alexa_oauth_client_id:
        raise _oauth_error("invalid_request", "Pedido de autorização inválido.")
    if (
        redirect_uri not in settings.alexa_redirect_uris
        or not state
        or len(state) > MAX_OAUTH_STATE_LENGTH
    ):
        raise _oauth_error("invalid_request", "Redirecionamento ou estado inválido.")
    if code_challenge is not None:
        if (
            code_challenge_method != "S256"
            or len(code_challenge) != 43
            or any(
                char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
                for char in code_challenge
            )
        ):
            raise _oauth_error("invalid_request", "PKCE deve usar o método S256.")
    elif code_challenge_method is not None:
        raise _oauth_error("invalid_request", "Desafio PKCE incompleto.")
    scopes = _scope(scope)
    context = CozinhaAlexaOAuthContext(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scope=scopes,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    await db.execute(
        delete(CozinhaAlexaOAuthContext).where(
            CozinhaAlexaOAuthContext.expires_at < datetime.now(UTC) - timedelta(days=1)
        )
    )
    await db.execute(
        delete(CozinhaAlexaOAuthGrant).where(
            CozinhaAlexaOAuthGrant.expires_at < datetime.now(UTC) - timedelta(days=30)
        )
    )
    db.add(context)
    await db.commit()
    consent_url = (
        f"{settings.frontend_url.rstrip('/')}/integracoes/alexa/autorizar?context={context.id}"
    )
    return RedirectResponse(
        consent_url, status_code=status.HTTP_303_SEE_OTHER, headers={"Cache-Control": "no-store"}
    )


@router.post("/oauth/consent")
@limiter.limit("10/minute")
async def consent(
    request: Request,
    response: Response,
    data: ConsentRequest,
    actor: Usuario = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
    origin: str | None = Header(default=None),
    admin_session: str | None = Header(default=None, alias="X-Admin-Session"),
) -> dict[str, str]:
    _enabled()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    if admin_session is not None:
        raise HTTPException(403, detail="Encerre o suporte antes de vincular a Alexa.")
    if origin != client_origin() or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, detail="Origem inválida para consentimento.")
    context = await db.scalar(
        select(CozinhaAlexaOAuthContext)
        .where(CozinhaAlexaOAuthContext.id == data.context_id)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if not context or context.consumed_at or context.expires_at <= now:
        raise HTTPException(410, detail="Este pedido de vínculo venceu. Recomece pela Alexa.")
    context.consumed_at = now
    if not data.approve:
        await db.commit()
        return {
            "redirect_url": _redirect_with(
                context.redirect_uri, {"error": "access_denied", "state": context.state}
            )
        }
    raw_code = _new_token()
    db.add(
        CozinhaAlexaOAuthGrant(
            tenant_id=actor.tenant_id,
            usuario_id=actor.id,
            family_id=uuid4(),
            client_id=context.client_id,
            token_hash=_digest(raw_code),
            grant_type="code",
            scope=context.scope,
            redirect_uri=context.redirect_uri,
            code_challenge=context.code_challenge,
            code_challenge_method=context.code_challenge_method,
            expires_at=now + timedelta(minutes=5),
        )
    )
    await db.commit()
    return {
        "redirect_url": _redirect_with(
            context.redirect_uri, {"code": raw_code, "state": context.state}
        )
    }


def _redirect_with(uri: str, values: dict[str, str]) -> str:
    parsed = urlsplit(uri)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.extend(values.items())
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


async def _basic_client(
    credentials: HTTPBasicCredentials | None,
) -> None:
    if (
        credentials is None
        or not secrets.compare_digest(credentials.username, settings.alexa_oauth_client_id)
        or not secrets.compare_digest(
            credentials.password, settings.alexa_oauth_client_secret.get_secret_value()
        )
    ):
        raise _oauth_error("invalid_client", "Cliente não autenticado.", 401)


@router.post("/oauth/token")
@limiter.limit("30/minute")
async def token(
    request: Request,
    response: Response,
    grant_type: str = Form(...),
    code: str | None = Form(default=None),
    redirect_uri: str | None = Form(default=None),
    code_verifier: str | None = Form(default=None),
    refresh_token: str | None = Form(default=None),
    credentials: HTTPBasicCredentials | None = Depends(basic_auth),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    _enabled()
    await _basic_client(credentials)
    now = datetime.now(UTC)
    if grant_type == "authorization_code":
        if not code or not redirect_uri:
            raise _oauth_error("invalid_request", "Código e redirecionamento são obrigatórios.")
        grant = await db.scalar(
            select(CozinhaAlexaOAuthGrant)
            .where(
                CozinhaAlexaOAuthGrant.token_hash == _digest(code),
                CozinhaAlexaOAuthGrant.grant_type == "code",
            )
            .with_for_update()
        )
        if (
            not grant
            or grant.consumed_at
            or grant.revoked_at
            or grant.expires_at <= now
            or grant.client_id != settings.alexa_oauth_client_id
            or grant.redirect_uri != redirect_uri
        ):
            raise _oauth_error("invalid_grant", "Código inválido ou vencido.")
        if grant.code_challenge:
            if (
                code_verifier is None
                or not 43 <= len(code_verifier) <= 128
                or any(
                    char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
                    for char in code_verifier
                )
            ):
                raise _oauth_error("invalid_grant", "Verificador PKCE inválido.")
            verifier_hash = (
                base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
                .rstrip(b"=")
                .decode()
            )
            if not secrets.compare_digest(verifier_hash, grant.code_challenge):
                raise _oauth_error("invalid_grant", "Verificação PKCE inválida.")
        elif code_verifier:
            raise _oauth_error("invalid_grant", "Este código não aceita verificador PKCE.")
        grant.consumed_at = now
        family = grant.family_id
        subject = (grant.tenant_id, grant.usuario_id, grant.scope)
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise _oauth_error("invalid_request", "Refresh token obrigatório.")
        grant = await db.scalar(
            select(CozinhaAlexaOAuthGrant)
            .where(
                CozinhaAlexaOAuthGrant.token_hash == _digest(refresh_token),
                CozinhaAlexaOAuthGrant.grant_type == "refresh",
            )
            .with_for_update()
        )
        if not grant or grant.client_id != settings.alexa_oauth_client_id:
            raise _oauth_error("invalid_grant", "Refresh token inválido.")
        if grant.revoked_at or grant.consumed_at:
            await db.execute(
                CozinhaAlexaOAuthGrant.__table__.update()
                .where(CozinhaAlexaOAuthGrant.family_id == grant.family_id)
                .values(revoked_at=now)
            )
            await db.commit()
            raise _oauth_error("invalid_grant", "Reutilização do refresh token detectada.")
        if grant.expires_at <= now:
            raise _oauth_error("invalid_grant", "Refresh token vencido.")
        grant.consumed_at = now
        family = grant.family_id
        subject = (grant.tenant_id, grant.usuario_id, grant.scope)
    else:
        raise _oauth_error("unsupported_grant_type", "Tipo de autorização não aceito.")

    access, refresh_value = _new_token(), _new_token()
    subject_user = await db.scalar(
        select(Usuario).where(
            Usuario.id == subject[1],
            Usuario.tenant_id == subject[0],
            Usuario.ativo.is_(True),
        )
    )
    if not subject_user:
        raise _oauth_error("invalid_grant", "A conta Fornada não está disponível.")
    await db.execute(
        pg_insert(CozinhaAlexaVinculo)
        .values(
            tenant_id=subject[0],
            usuario_id=subject[1],
            amazon_user_hash=None,
        )
        .on_conflict_do_nothing(constraint="uq_cozinha_alexa_usuario")
    )
    for raw, kind, lifetime in (
        (access, "access", timedelta(minutes=15)),
        (refresh_value, "refresh", timedelta(days=7)),
    ):
        db.add(
            CozinhaAlexaOAuthGrant(
                tenant_id=subject[0],
                usuario_id=subject[1],
                family_id=family,
                client_id=settings.alexa_oauth_client_id,
                token_hash=_digest(raw),
                grant_type=kind,
                scope=subject[2],
                expires_at=now + lifetime,
            )
        )
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": 900,
        "refresh_token": refresh_value,
        "scope": subject[2],
    }


class _SafeAlexaVerifier:
    """ASK SDK verifier with certificate retrieval pinned to the allowed Amazon URL."""

    def __init__(self) -> None:
        from ask_sdk_webservice_support.verifier import RequestVerifier

        class SafeRequestVerifier(RequestVerifier):
            def _validate_certificate_url(self, cert_url: str) -> None:
                parsed = urlsplit(cert_url)
                decoded_path = unquote(httpx.URL(cert_url).path)
                normalized = posixpath.normpath(decoded_path)
                if (
                    parsed.scheme.lower() != "https"
                    or parsed.hostname != "s3.amazonaws.com"
                    or parsed.port not in (None, 443)
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.query
                    or parsed.fragment
                    or not normalized.startswith("/echo.api/")
                    or normalized == "/echo.api"
                ):
                    raise ValueError("URL de certificado Alexa inválida")

            def _load_cert_chain(self, cert_url: str) -> bytes:
                if cert_url in self._cert_cache:
                    return self._cert_cache[cert_url]
                with httpx.Client(timeout=3.0, follow_redirects=False) as client:
                    result = client.get(cert_url)
                if result.status_code != 200 or len(result.content) > 65536:
                    raise ValueError("Cadeia de certificado Alexa indisponível")
                self._cert_cache[cert_url] = result.content
                return result.content

        self.verifier = SafeRequestVerifier()

    def verify(self, headers: dict[str, str], raw: str, envelope: dict) -> None:
        self.verifier.verify(headers, raw, envelope)


_verifier: _SafeAlexaVerifier | None = None


def _verified_request(headers: dict[str, str], raw: str, envelope: dict) -> None:
    global _verifier
    if _verifier is None:
        _verifier = _SafeAlexaVerifier()
    _verifier.verify(headers, raw, envelope)


def _ask_response(
    speech: str,
    *,
    end: bool = True,
    link: bool = False,
    reprompt: str = "Diga o nome da receita que deseja buscar.",
) -> dict:
    result = {
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": speech},
            "shouldEndSession": end,
        },
    }
    if link:
        result["response"]["card"] = {"type": "LinkAccount"}
    if not end:
        result["response"]["reprompt"] = {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt,
            }
        }
    return result


def _ordinal(value: object) -> int | None:
    if isinstance(value, int):
        return value
    text = str(value or "").strip().casefold()
    words = {
        "um": 1,
        "uma": 1,
        "primeiro": 1,
        "primeira": 1,
        "dois": 2,
        "duas": 2,
        "segundo": 2,
        "segunda": 2,
        "três": 3,
        "tres": 3,
        "terceiro": 3,
        "terceira": 3,
        "quatro": 4,
        "quarto": 4,
        "quarta": 4,
        "cinco": 5,
        "quinto": 5,
        "quinta": 5,
    }
    try:
        return int(text)
    except ValueError:
        return words.get(text)


def _slot(envelope: dict, slot_name: str) -> object | None:
    request_data = envelope.get("request", {})
    slots = request_data.get("intent", {}).get("slots", {})
    return (slots.get(slot_name) or {}).get("value")


def _section_blocks(station: CozinhaEstacao) -> list[dict]:
    if not station.projection:
        return []
    return [
        block
        for block in station.projection.get("blocks", [])
        if block.get("section") == station.secao
    ]


def _current_speech_parts(station: CozinhaEstacao) -> list[str]:
    if not station.projection:
        return []
    return projection_speech_parts(station.projection, station.secao, station.bloco_indice)


def _position_prompt(station: CozinhaEstacao) -> str:
    if not station.projection:
        return "A estação está pronta. Diga buscar receita e o nome do que você quer preparar."
    section = {
        "ingredients": "ingredientes",
        "preparation": "preparo",
        "assembly": "montagem",
    }.get(station.secao, "receita")
    blocks = _section_blocks(station)
    stage = (
        f", etapa {min(station.bloco_indice + 1, len(blocks))} de {len(blocks)}"
        if station.secao != "ingredients" and blocks
        else ""
    )
    parts = _current_speech_parts(station)
    part = min(station.parte_fala_indice + 1, len(parts)) if parts else 0
    return (
        f"{station.projection['name']} continua em {section}{stage}, parte {part} de {len(parts)}. "
        "Diga repetir para ouvir novamente ou continuar leitura."
    )


def _speak_current_part(station: CozinhaEstacao, *, prefix: str = "") -> str:
    parts = _current_speech_parts(station)
    if not parts:
        labels = {
            "ingredients": "ingredientes",
            "preparation": "modo de preparo",
            "assembly": "montagem",
        }
        return f"Esta receita não tem {labels.get(station.secao, 'conteúdo')} cadastrados."
    index = station.parte_fala_indice
    if index < 0 or index >= len(parts):
        return "Você chegou ao fim desta leitura. Diga próxima etapa para avançar."
    section = {
        "ingredients": "Ingredientes",
        "preparation": "Preparo",
        "assembly": "Montagem",
    }.get(station.secao, "Receita")
    block_info = ""
    blocks = _section_blocks(station)
    if station.secao != "ingredients" and blocks:
        block_index = min(max(station.bloco_indice, 0), len(blocks) - 1)
        block_info = f", etapa {block_index + 1} de {len(blocks)}"
    return f"{prefix}{section}{block_info}, parte {index + 1} de {len(parts)}. {parts[index]}"


@router.post("/requests")
async def alexa_request(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> dict:
    _enabled()
    response.headers["Cache-Control"] = "no-store"
    raw_bytes = await request.body()
    if len(raw_bytes) > 65536:
        raise HTTPException(400, detail="Pedido Alexa inválido.")
    try:
        raw = raw_bytes.decode("utf-8")
        envelope = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(400, detail="Pedido Alexa inválido.") from None
    if not isinstance(envelope, dict):
        raise HTTPException(400, detail="Pedido Alexa inválido.")
    try:
        timestamp = datetime.fromisoformat(envelope["request"]["timestamp"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None or abs((datetime.now(UTC) - timestamp).total_seconds()) > 150:
            raise ValueError("timestamp fora da janela")
        await run_in_threadpool(_verified_request, dict(request.headers), raw, envelope)
    except Exception:
        raise HTTPException(400, detail="Assinatura ou horário do pedido Alexa inválido.") from None

    system = envelope.get("context", {}).get("System", {})
    user_data = system.get("user", {})
    access_token = user_data.get("accessToken")
    ask_request = envelope.get("request", {})
    request_id = ask_request.get("requestId")
    application_id = system.get("application", {}).get("applicationId")
    amazon_user_id = user_data.get("userId")
    device_id = system.get("device", {}).get("deviceId")
    if (
        application_id != settings.alexa_skill_application_id
        or not isinstance(request_id, str)
        or not 1 <= len(request_id) <= 300
        or not isinstance(amazon_user_id, str)
        or not isinstance(device_id, str)
        or len(amazon_user_id) > 1000
        or len(device_id) > 1000
    ):
        raise HTTPException(400, detail="Pedido Alexa inválido.")
    if not access_token:
        return _ask_response(
            "Vincule sua conta Fornada pelo aplicativo Alexa para continuar.", link=True
        )

    now = datetime.now(UTC)
    token_grant = await db.scalar(
        select(CozinhaAlexaOAuthGrant).where(
            CozinhaAlexaOAuthGrant.token_hash == _digest(access_token),
            CozinhaAlexaOAuthGrant.client_id == settings.alexa_oauth_client_id,
            CozinhaAlexaOAuthGrant.grant_type == "access",
            CozinhaAlexaOAuthGrant.revoked_at.is_(None),
            CozinhaAlexaOAuthGrant.expires_at > now,
        )
    )
    if not token_grant or not amazon_user_id or not device_id:
        return _ask_response(
            "O vínculo expirou. Vincule novamente sua conta Fornada pelo aplicativo Alexa.",
            link=True,
        )
    if "cozinha:control" not in token_grant.scope.split():
        return _ask_response(
            "Este vínculo não tem permissão para controlar o Modo cozinha. "
            "Vincule novamente e aceite o acesso solicitado.",
            link=True,
        )
    actor = await db.get(Usuario, token_grant.usuario_id)
    if not actor or not actor.ativo or actor.tenant_id != token_grant.tenant_id:
        return _ask_response(
            "A conta Fornada está indisponível. Confira o acesso e vincule novamente.", link=True
        )

    user_hash = _digest(f"{application_id}:{amazon_user_id}")
    device_hash = _digest(device_id)
    await db.execute(
        pg_insert(CozinhaAlexaVinculo)
        .values(
            tenant_id=actor.tenant_id,
            usuario_id=actor.id,
            amazon_user_hash=user_hash,
        )
        .on_conflict_do_nothing(constraint="uq_cozinha_alexa_usuario")
    )
    binding = await db.scalar(
        select(CozinhaAlexaVinculo)
        .where(
            CozinhaAlexaVinculo.tenant_id == actor.tenant_id,
            CozinhaAlexaVinculo.usuario_id == actor.id,
        )
        .with_for_update()
    )
    if binding and binding.amazon_user_hash is None:
        binding.amazon_user_hash = user_hash
    if binding and binding.amazon_user_hash != user_hash:
        return _ask_response(
            "Esta conta Fornada já está vinculada a outra conta Alexa. "
            "Desvincule-a no modo cozinha primeiro."
        )
    if binding is None:
        raise HTTPException(503, detail="Não foi possível preparar o vínculo Alexa.")
    approved = binding.approved_device_hash == device_hash
    if not approved:
        candidate_expired = (
            binding.pending_device_seen_at is None
            or binding.pending_device_seen_at <= now - timedelta(minutes=5)
        )
        if binding.pending_device_hash != device_hash or candidate_expired:
            binding.pending_device_hash = device_hash
            binding.pending_device_id = uuid4()
            binding.pending_device_seen_at = now
        await db.commit()
        return _ask_response(
            "Para proteger suas receitas, confirme esta Echo na tela Modo cozinha "
            "do Fornada e tente novamente."
        )

    if not binding.estacao_id:
        return _ask_response("Abra Modo cozinha no Fornada e escolha a estação que ficará na tela.")
    station = await db.scalar(
        select(CozinhaEstacao)
        .where(
            CozinhaEstacao.id == binding.estacao_id,
            CozinhaEstacao.tenant_id == actor.tenant_id,
            CozinhaEstacao.usuario_id == actor.id,
            CozinhaEstacao.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if (
        not station
        or station.status != "active"
        or not station.lease_expira_em
        or station.lease_expira_em <= now
    ):
        return _ask_response("Ative o Modo cozinha no Chrome antes de pedir uma receita.")

    recipe_changed = False
    if station.receita_id and station.projection:
        try:
            current_projection = await recipe_projection(db, actor.tenant_id, station.receita_id)
        except ValueError:
            current_projection = None
        if (
            current_projection is None
            or current_projection["recipe_version"] != station.receita_versao
        ):
            station.receita_id = None
            station.receita_versao = None
            station.projection = None
            station.secao = "ingredients"
            station.bloco_indice = 0
            station.parte_fala_indice = 0
            station.aviso = (
                "A receita foi removida ou precisa de revisão. Escolha outra receita."
                if current_projection is None
                else "Esta receita foi alterada. Abra a versão atual antes de continuar."
            )
            station.revisao += 1
            recipe_changed = True

    payload_hash = _digest(
        json.dumps(envelope, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )
    prior = await db.scalar(
        select(CozinhaAlexaRequest).where(
            CozinhaAlexaRequest.application_id == application_id,
            CozinhaAlexaRequest.amazon_user_hash == user_hash,
            CozinhaAlexaRequest.request_id == request_id,
        )
    )
    if prior and not recipe_changed:
        if prior.tenant_id != actor.tenant_id or prior.usuario_id != actor.id:
            return _ask_response(
                "Este comando já foi processado. Tente novamente com uma nova frase."
            )
        if prior.payload_hash != payload_hash:
            return _ask_response(
                "Este comando já foi recebido. Tente novamente com uma nova frase."
            )
        return prior.response
    if prior and recipe_changed:
        if prior.tenant_id != actor.tenant_id or prior.usuario_id != actor.id:
            return _ask_response(
                "Este comando já foi processado. Tente novamente com uma nova frase."
            )
        await db.commit()
        return _ask_response(
            "A receita foi alterada e a leitura foi interrompida. Abra a versão atual no Fornada."
        )

    speech = "Não entendi o pedido. Diga, por exemplo, buscar receita de brownie."
    kind = ask_request.get("type")
    intent = ask_request.get("intent", {}).get("name")
    recent_count = (
        await db.scalar(
            select(func.count())
            .select_from(CozinhaAlexaRequest)
            .where(
                CozinhaAlexaRequest.tenant_id == actor.tenant_id,
                CozinhaAlexaRequest.usuario_id == actor.id,
                CozinhaAlexaRequest.created_at >= now - timedelta(minutes=1),
            )
        )
        or 0
    )
    if recipe_changed and not (
        ask_request.get("type") == "IntentRequest"
        and ask_request.get("intent", {}).get("name") == "SearchRecipeIntent"
    ):
        speech = (
            "A receita foi alterada e a leitura foi interrompida. Abra a versão atual no Fornada."
        )
    elif recent_count >= 60:
        speech = "Há muitos pedidos seguidos. Aguarde um instante e tente novamente."
    elif kind == "LaunchRequest":
        if station.projection:
            speech = (
                f"Modo cozinha pronto. {_position_prompt(station)} "
                "Diga buscar receita para escolher outra."
            )
        else:
            speech = "Modo cozinha pronto. Diga buscar receita e o nome do que você quer preparar."
    elif kind == "IntentRequest" and intent == "ResumeKitchenIntent":
        speech = (
            _speak_current_part(station, prefix="Retomando. ")
            if station.projection
            else _position_prompt(station)
        )
    elif kind == "IntentRequest" and intent == "SearchRecipeIntent":
        query = str(_slot(envelope, "recipe_name") or "").strip()
        if not query:
            speech = "Qual receita você quer buscar?"
        else:
            result = await search(db, actor.tenant_id, query[:200], 0, 5)
            if not result["items"]:
                station.selecao_id = None
                station.resultados_busca = None
                station.revisao += 1
                speech = f"Não encontrei receita para {query}. Tente outro nome."
            elif len(result["items"]) > 1:
                station.selecao_id = uuid4()
                selection = {
                    "selection_id": str(station.selecao_id),
                    "query": query[:200],
                    "offset": 0,
                    "expires_at": (now + timedelta(minutes=5)).isoformat(),
                    **result,
                    "items": [{"ordinal": i, **item} for i, item in enumerate(result["items"], 1)],
                }
                station.resultados_busca = selection
                station.revisao += 1
                choices = "; ".join(
                    f"{item['ordinal']}: {item['name']}" for item in selection["items"]
                )
                speech = (
                    f"Encontrei mais de uma receita: {choices}. Diga o número da que deseja abrir."
                )
            else:
                item = result["items"][0]
                speech = await _open_recipe(
                    db, actor, station, UUID(item["recipe_id"]), item["name"]
                )
    elif kind == "IntentRequest" and intent in (
        "ShowIngredientsIntent",
        "ShowPreparationIntent",
        "ShowAssemblyIntent",
    ):
        section = {
            "ShowIngredientsIntent": "ingredients",
            "ShowPreparationIntent": "preparation",
            "ShowAssemblyIntent": "assembly",
        }[intent]
        if not station.projection:
            speech = "Abra uma receita no Modo cozinha antes de pedir a leitura."
        else:
            has_section = (
                section == "ingredients"
                and bool(station.projection.get("ingredients"))
                or any(
                    block.get("section") == section
                    for block in station.projection.get("blocks", [])
                )
            )
            if not has_section:
                speech = (
                    _speak_current_part(station)
                    if station.secao == section
                    else {
                        "ingredients": "Esta receita não tem ingredientes cadastrados.",
                        "preparation": "Esta receita não tem modo de preparo cadastrado.",
                        "assembly": "Esta receita não tem montagem cadastrada.",
                    }[section]
                )
            else:
                station.secao = section
                station.bloco_indice = 0
                station.parte_fala_indice = 0
                station.revisao += 1
                speech = _speak_current_part(station)
    elif kind == "IntentRequest" and intent in (
        "NextStepIntent",
        "PreviousStepIntent",
    ):
        if not station.projection:
            speech = "Abra uma receita no Modo cozinha antes de navegar pelas etapas."
        else:
            blocks = _section_blocks(station)
            direction = 1 if intent == "NextStepIntent" else -1
            next_index = station.bloco_indice + direction
            if next_index < 0:
                speech = "Esta é a primeira etapa desta seção."
            elif next_index >= len(blocks):
                speech = "Esta é a última etapa desta seção. Você pode escolher outra seção."
            else:
                station.bloco_indice = next_index
                station.parte_fala_indice = 0
                station.revisao += 1
                speech = _speak_current_part(station)
    elif kind == "IntentRequest" and intent == "RepeatContentIntent":
        speech = (
            _speak_current_part(station)
            if station.projection
            else "Abra uma receita no Modo cozinha antes de pedir a leitura."
        )
    elif kind == "IntentRequest" and intent == "ContinueReadingIntent":
        if not station.projection:
            speech = "Abra uma receita no Modo cozinha antes de continuar a leitura."
        else:
            parts = _current_speech_parts(station)
            if station.parte_fala_indice + 1 >= len(parts):
                speech = "Fim desta parte da receita. Diga próxima etapa ou escolha outra seção."
            else:
                station.parte_fala_indice += 1
                station.revisao += 1
                speech = _speak_current_part(station)
    elif kind == "IntentRequest" and intent == "SelectRecipeIntent":
        saved = station.resultados_busca or {}
        ordinal = _ordinal(_slot(envelope, "ordinal"))
        expires = datetime.fromisoformat(saved["expires_at"]) if saved.get("expires_at") else now
        item = next(
            (entry for entry in saved.get("items", []) if entry.get("ordinal") == ordinal), None
        )
        if expires <= now or not item:
            speech = "Essa seleção venceu ou não está na lista. Busque a receita novamente."
        else:
            speech = await _open_recipe(db, actor, station, UUID(item["recipe_id"]), item["name"])
    elif kind == "IntentRequest" and intent == "MoreRecipesIntent":
        saved = station.resultados_busca or {}
        expires = datetime.fromisoformat(saved["expires_at"]) if saved.get("expires_at") else now
        offset = saved.get("next_offset")
        if expires <= now or not saved.get("query"):
            speech = "A busca venceu. Busque a receita novamente."
        elif offset is None:
            speech = "Não há mais receitas nesta busca."
        else:
            result = await search(db, actor.tenant_id, saved["query"], offset, 5)
            station.selecao_id = uuid4()
            selection = {
                "selection_id": str(station.selecao_id),
                "query": saved["query"],
                "offset": offset,
                "expires_at": (now + timedelta(minutes=5)).isoformat(),
                **result,
                "items": [
                    {"ordinal": index, **entry}
                    for index, entry in enumerate(result["items"], start=1)
                ],
            }
            station.resultados_busca = selection
            station.revisao += 1
            if selection["items"]:
                choices = "; ".join(
                    f"{entry['ordinal']}: {entry['name']}" for entry in selection["items"]
                )
                speech = f"Mais receitas: {choices}. Diga o número da que deseja abrir."
            else:
                speech = "Não encontrei mais receitas."
    elif kind == "IntentRequest" and intent in ("AMAZON.HelpIntent", "AMAZON.FallbackIntent"):
        speech = (
            "Você pode dizer buscar receita de brownie, ler ingredientes, mostrar preparo, "
            "próxima etapa, voltar etapa, repetir ou continuar leitura."
        )
    elif kind == "IntentRequest" and intent == "AMAZON.CancelIntent":
        if station.resultados_busca:
            station.selecao_id = None
            station.resultados_busca = None
            station.revisao += 1
        speech = "Seleção cancelada. A receita atual continua aberta na estação."
    elif kind == "IntentRequest" and intent == "AMAZON.StopIntent":
        speech = "Tudo bem. A estação continua aberta no Fornada."
    elif kind == "SessionEndedRequest":
        await db.rollback()
        return {"version": "1.0", "response": {"shouldEndSession": True}}

    conversational_intents = {
        "ResumeKitchenIntent",
        "SearchRecipeIntent",
        "SelectRecipeIntent",
        "MoreRecipesIntent",
        "ShowIngredientsIntent",
        "ShowPreparationIntent",
        "ShowAssemblyIntent",
        "NextStepIntent",
        "PreviousStepIntent",
        "RepeatContentIntent",
        "ContinueReadingIntent",
        "AMAZON.HelpIntent",
        "AMAZON.FallbackIntent",
    }
    keep_session = kind == "IntentRequest" and intent in conversational_intents
    if station.resultados_busca and station.resultados_busca.get("items"):
        reprompt = "Diga o número da receita ou diga mais receitas."
    elif station.projection:
        reprompt = (
            "Diga ler ingredientes, mostrar preparo, próxima etapa, voltar etapa, "
            "repetir ou continuar leitura."
        )
    else:
        reprompt = "Diga buscar receita e o nome do que você quer preparar."
    result = _ask_response(speech, end=not keep_session, reprompt=reprompt)
    db.add(
        CozinhaAlexaRequest(
            tenant_id=actor.tenant_id,
            usuario_id=actor.id,
            application_id=application_id,
            amazon_user_hash=user_hash,
            request_id=request_id,
            payload_hash=payload_hash,
            response=result,
        )
    )
    await db.execute(
        delete(CozinhaAlexaRequest).where(
            CozinhaAlexaRequest.created_at < now - timedelta(hours=24),
        )
    )
    await db.commit()
    return result


async def _open_recipe(
    db: AsyncSession, actor: Usuario, station: CozinhaEstacao, recipe_id: UUID, recipe_name: str
) -> str:
    try:
        projection = await recipe_projection(db, actor.tenant_id, recipe_id)
    except ValueError:
        projection = None
    if projection is None:
        return "Não consegui abrir essa receita. Confira se ela ainda está cadastrada no Fornada."
    station.receita_id = recipe_id
    station.receita_versao = projection["recipe_version"]
    station.projection = resume_completion(station.projection, projection)
    station.secao = "ingredients"
    station.bloco_indice = 0
    station.parte_fala_indice = 0
    station.aviso = None
    station.selecao_id = None
    station.resultados_busca = None
    station.revisao += 1
    return f"Receita {recipe_name} enviada para a estação. Acompanhe no Chrome."


@link_router.get("/link")
async def get_link(
    response: Response,
    actor: Usuario = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    binding = await db.scalar(
        select(CozinhaAlexaVinculo).where(
            CozinhaAlexaVinculo.tenant_id == actor.tenant_id,
            CozinhaAlexaVinculo.usuario_id == actor.id,
        )
    )
    pending = []
    if (
        binding
        and binding.pending_device_id
        and binding.pending_device_seen_at
        and binding.pending_device_seen_at > datetime.now(UTC) - timedelta(minutes=5)
    ):
        pending.append(
            {
                "id": str(binding.pending_device_id),
                "first_seen_at": binding.pending_device_seen_at.isoformat(),
            }
        )
    response.headers["Cache-Control"] = "no-store"
    return {
        "linked": binding is not None,
        "station_id": str(binding.estacao_id) if binding and binding.estacao_id else None,
        "pending_devices": pending,
        "approved_device_id": str(binding.approved_device_id)
        if binding and binding.approved_device_id
        else None,
    }


@link_router.put("/link/device")
async def confirm_device(
    data: DeviceConfirmation,
    response: Response,
    actor: Usuario = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    pending_id = data.pending_device_id
    binding = await db.scalar(
        select(CozinhaAlexaVinculo)
        .where(
            CozinhaAlexaVinculo.tenant_id == actor.tenant_id,
            CozinhaAlexaVinculo.usuario_id == actor.id,
        )
        .with_for_update()
    )
    if (
        not binding
        or binding.pending_device_id != pending_id
        or not binding.pending_device_seen_at
        or binding.pending_device_seen_at <= datetime.now(UTC) - timedelta(minutes=5)
    ):
        raise HTTPException(410, detail="Este pedido da Echo venceu. Peça novamente pela Alexa.")
    binding.approved_device_id = pending_id
    binding.approved_device_hash = binding.pending_device_hash
    binding.pending_device_id = None
    binding.pending_device_hash = None
    binding.pending_device_seen_at = None
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"approved_device_id": str(binding.approved_device_id)}


@link_router.put("/link/station")
async def select_station(
    data: StationSelection,
    response: Response,
    actor: Usuario = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    station_id = data.station_id
    binding = await db.scalar(
        select(CozinhaAlexaVinculo)
        .where(
            CozinhaAlexaVinculo.tenant_id == actor.tenant_id,
            CozinhaAlexaVinculo.usuario_id == actor.id,
        )
        .with_for_update()
    )
    if not binding:
        raise HTTPException(404, detail="Vínculo Alexa não encontrado.")
    station = await db.scalar(
        select(CozinhaEstacao).where(
            CozinhaEstacao.id == station_id,
            CozinhaEstacao.tenant_id == actor.tenant_id,
            CozinhaEstacao.usuario_id == actor.id,
            CozinhaEstacao.deleted_at.is_(None),
        )
    )
    if not station:
        raise HTTPException(404, detail="Estação não encontrada.")
    binding.estacao_id = station.id
    station.selecao_id = None
    station.resultados_busca = None
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"station_id": str(station.id)}


@link_router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
async def unlink(
    response: Response,
    actor: Usuario = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> None:
    binding = await db.scalar(
        select(CozinhaAlexaVinculo)
        .where(
            CozinhaAlexaVinculo.tenant_id == actor.tenant_id,
            CozinhaAlexaVinculo.usuario_id == actor.id,
        )
        .with_for_update()
    )
    if binding:
        await db.execute(
            CozinhaAlexaOAuthGrant.__table__.update()
            .where(
                CozinhaAlexaOAuthGrant.tenant_id == actor.tenant_id,
                CozinhaAlexaOAuthGrant.usuario_id == actor.id,
                CozinhaAlexaOAuthGrant.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await db.delete(binding)
        await db.commit()
    response.headers["Cache-Control"] = "no-store"
