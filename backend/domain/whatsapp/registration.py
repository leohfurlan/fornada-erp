"""Cadastro guiado a partir do remetente validado pelo webhook autenticado."""

import secrets
from datetime import UTC, datetime, timedelta

from pydantic import EmailStr, TypeAdapter
from pydantic import ValidationError as SchemaError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from domain.usuarios.repository import UsuarioRepository
from domain.usuarios.whatsapp_schemas import EnderecoInput
from domain.whatsapp.messages import ONBOARDING, IncomingMessage
from infrastructure.database.whatsapp_models import WhatsAppCadastro

FIELDS = [
    ("nome", "Qual é seu nome?"),
    ("nome_negocio", "Qual é o nome da sua confeitaria?"),
    ("email", "Qual é seu e-mail?"),
    ("pais", "Qual é o país do endereço? Use duas letras: BR, PT, US..."),
    ("cep", "Qual é o CEP ou código postal?"),
    ("logradouro", "Qual é a rua ou avenida?"),
    ("numero", "Qual é o número do endereço? Use S/N se não houver."),
    ("bairro", "Qual é o bairro?"),
    ("cidade", "Qual é a cidade?"),
    ("estado", "Qual é o estado ou região?"),
]


async def register_chat(db: AsyncSession, incoming: IncomingMessage) -> str:
    text = incoming.text.strip()
    command = text.upper()
    cadastro = await db.scalar(
        select(WhatsAppCadastro)
        .where(
            WhatsAppCadastro.telefone == incoming.phone,
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    if not cadastro:
        cadastro = WhatsAppCadastro(telefone=incoming.phone, dados={}, expira_em=now)
        db.add(cadastro)
    if command in {"CANCELAR", "RECOMEÇAR"}:
        cadastro.dados = {}
        return "Cadastro cancelado. Envie CADASTRAR para começar novamente."
    state = dict(cadastro.dados) if cadastro.expira_em > now else {}
    if not state or command == "CADASTRAR":
        cadastro.dados = {"step": 0}
        cadastro.expira_em = now + timedelta(minutes=30)
        return (
            "Boas-vindas! Vamos criar sua conta pelo WhatsApp.\n"
            "Se já tem conta, vincule seu número em Configurações > WhatsApp no aplicativo.\n"
            "Nunca envie senha por aqui. CANCELAR encerra o cadastro.\n" + FIELDS[0][1]
        )
    index = state["step"]
    if index < len(FIELDS):
        field = FIELDS[index][0]
        if not text or len(text) > 200 or incoming.image:
            return "Responda com texto de até 200 caracteres. " + FIELDS[index][1]
        if field == "email":
            try:
                text = str(TypeAdapter(EmailStr).validate_python(text)).lower()
            except SchemaError:
                return "Informe um e-mail válido."
        if field == "pais" and (len(text) != 2 or not text.isalpha()):
            return "Informe o país usando duas letras, por exemplo BR."
        state[field] = text.upper() if field == "pais" else text
        state["step"] = index + 1
        if index + 1 < len(FIELDS):
            cadastro.dados = state
            return FIELDS[index + 1][1]
        try:
            EnderecoInput.model_validate(
                {
                    key: state[key]
                    for key in ("pais", "cep", "logradouro", "numero", "bairro", "cidade", "estado")
                }
            )
        except SchemaError:
            cadastro.dados = {}
            return "Endereço inválido. Envie CADASTRAR para corrigir os dados."
        cadastro.dados = state
        return (
            f"Confira: {state['nome']} / {state['nome_negocio']} / {state['email']}.\n"
            f"Endereço: {state['logradouro']}, {state['numero']}, {state['bairro']}, "
            f"{state['cidade']}, {state['estado']}, {state['cep']}, {state['pais']}.\n"
            "Seu número será vinculado à conta para acesso e compras. "
            "CONFIRMAR CADASTRO para aceitar e criar; CANCELAR para sair."
        )
    if command != "CONFIRMAR CADASTRO":
        return "Envie CONFIRMAR CADASTRO para criar sua conta, ou CANCELAR."
    repo = UsuarioRepository(db)
    if await repo.buscar_por_email(state["email"]):
        cadastro.dados = {}
        return (
            "Não foi possível criar a conta com esses dados. "
            "Se já possui conta, entre no aplicativo e vincule seu WhatsApp nas Configurações."
        )
    tenant = await repo.criar_tenant(state["nome_negocio"])
    tenant.endereco = EnderecoInput.model_validate(
        {
            key: state[key]
            for key in ("pais", "cep", "logradouro", "numero", "bairro", "cidade", "estado")
        }
    ).model_dump()
    user = await repo.criar_usuario(
        tenant.id, state["email"], hash_password(secrets.token_urlsafe(32)), state["nome"]
    )
    user.telefone = "+" + incoming.phone
    cadastro.dados = {}
    return (
        "Sua conta foi criada! Para acessar o aplicativo, entre pelo código WhatsApp.\n"
        + ONBOARDING
    )
