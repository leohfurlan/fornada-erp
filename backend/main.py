from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from api.routers import (
    agenda,
    auth,
    configuracoes,
    estoque,
    estoque_pa,
    pedidos,
    producao,
    receitas,
    vendas,
)
from core.config import settings
from core.logging import configure_logging
from core.rate_limit import limiter
from domain.exceptions import (
    AuthError,
    ConflictError,
    EstoqueInsuficienteError,
    EstoquePAInsuficienteError,
    FornadaError,
    NotFoundError,
    ValidationError,
)
from infrastructure.cache.redis import close_redis

configure_logging()

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await close_redis()


app = FastAPI(
    title="Fornada API",
    description="ERP para confeiteiras artesanais",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Muitas tentativas. Tente novamente em alguns instantes."
        },
    )

app.add_middleware(
    CORSMiddleware,
    # Aceita localhost + qualquer IP de rede privada (LAN/Wi-Fi) na porta 3000.
    # Permite acessar pelo celular conectado na mesma rede sem precisar
    # editar config a cada mudança de IP.
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
        r"):3000"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(receitas.router, prefix="/api/v1")
app.include_router(estoque.router, prefix="/api/v1")
app.include_router(configuracoes.router, prefix="/api/v1")
app.include_router(pedidos.router, prefix="/api/v1")
app.include_router(estoque_pa.router, prefix="/api/v1")
app.include_router(producao.router, prefix="/api/v1")
app.include_router(vendas.router, prefix="/api/v1")
app.include_router(agenda.router, prefix="/api/v1")


# Tratamento de erros de domínio — mensagens em português, sem jargão técnico
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.message})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message})


@app.exception_handler(AuthError)
async def auth_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": exc.message}
    )


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.message}
    )


@app.exception_handler(EstoqueInsuficienteError)
async def estoque_insuficiente_handler(
    request: Request, exc: EstoqueInsuficienteError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message}
    )


@app.exception_handler(EstoquePAInsuficienteError)
async def estoque_pa_insuficiente_handler(
    request: Request, exc: EstoquePAInsuficienteError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message}
    )


@app.exception_handler(FornadaError)
async def domain_error_handler(request: Request, exc: FornadaError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.message}
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
