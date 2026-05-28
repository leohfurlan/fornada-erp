from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class RegistroRequest(BaseModel):
    nome_negocio: str
    nome: str
    email: EmailStr
    senha: str

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter pelo menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UsuarioResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    nome: str
    valor_hora: Decimal

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


class AtualizarUsuarioRequest(BaseModel):
    nome: str | None = None
    valor_hora: Decimal | None = None
