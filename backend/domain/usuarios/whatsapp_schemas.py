from pydantic import BaseModel, ConfigDict, EmailStr, Field
from domain.usuarios.schemas import TokenResponse


class SolicitarCodigo(BaseModel):
    telefone: str = Field(min_length=5, max_length=40)
    regiao: str = Field(min_length=2, max_length=2)


class DesafioResponse(BaseModel):
    desafio: str
    reenviar_em: int = 60
    expira_em: int = 300


class VerificarCodigo(BaseModel):
    desafio: str = Field(pattern=r"^[a-f0-9]{32}$")
    codigo: str = Field(pattern=r"^[0-9]{6}$")


class VerificacaoResponse(BaseModel):
    prova: str


class ProvaRequest(BaseModel):
    prova: str = Field(min_length=40, max_length=100)


class LoginWhatsappResponse(BaseModel):
    tokens: TokenResponse | None = None
    onboarding_prova: str | None = None


class EnderecoInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    pais: str = Field(min_length=2, max_length=2)
    cep: str = Field(min_length=3, max_length=20)
    logradouro: str = Field(min_length=1, max_length=200)
    numero: str = Field(min_length=1, max_length=30)
    complemento: str = Field(default="", max_length=100)
    bairro: str = Field(min_length=1, max_length=100)
    cidade: str = Field(min_length=1, max_length=100)
    estado: str = Field(min_length=1, max_length=100)


class CadastroWhatsappRequest(ProvaRequest):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    nome: str = Field(min_length=1, max_length=200)
    nome_negocio: str = Field(min_length=1, max_length=200)
    email: EmailStr
    endereco: EnderecoInput
