"""Códigos de uso único; transporte e armazenamento injetados por portas."""
import hashlib
import hmac
import secrets
from typing import Protocol
from uuid import uuid4

from domain.exceptions import AuthError, ValidationError


class OtpStore(Protocol):
    async def permitir_envio(self, telefone_hash: str, ip_hash: str) -> bool: ...
    async def guardar_desafio(self, identificador: str, telefone: str, digest: str) -> None: ...
    async def remover_desafio(self, identificador: str) -> None: ...
    async def verificar(self, identificador: str, digest: str) -> str | None: ...
    async def guardar_prova(self, prova: str, telefone: str) -> None: ...
    async def consumir_prova(self, prova: str) -> str | None: ...


class OtpSender(Protocol):
    async def enviar_codigo(self, telefone: str, codigo: str) -> None: ...


class OtpService:
    def __init__(self, store: OtpStore, sender: OtpSender, secret: str) -> None:
        self.store, self.sender, self.secret = store, sender, secret

    def digest(self, valor: str) -> str:
        """HMAC evita recuperar códigos curtos a partir de vazamento do cache."""
        return hmac.new(self.secret.encode(), valor.encode(), hashlib.sha256).hexdigest()

    async def solicitar(self, telefone: str, ip: str) -> str:
        """Limita envio por telefone/IP e salva desafio por cinco minutos."""
        if not await self.store.permitir_envio(self.digest(telefone), self.digest(ip)):
            raise ValidationError("Aguarde antes de solicitar outro código. Se persistir, tente mais tarde.")
        desafio = uuid4().hex
        codigo = f"{secrets.randbelow(1_000_000):06d}"
        await self.store.guardar_desafio(desafio, telefone, self.digest(f"{desafio}:{codigo}"))
        try:
            await self.sender.enviar_codigo(telefone, codigo)
        except Exception:
            await self.store.remover_desafio(desafio)
            raise
        return desafio

    async def verificar(self, desafio: str, codigo: str) -> str:
        """Consome desafio atomicamente e cria prova curta para login/cadastro."""
        telefone = await self.store.verificar(desafio, self.digest(f"{desafio}:{codigo}"))
        if not telefone:
            raise AuthError("Código inválido ou expirado. Solicite outro código se necessário.")
        prova = secrets.token_urlsafe(32)
        await self.store.guardar_prova(self.digest(prova), telefone)
        return prova

    async def consumir_prova(self, prova: str) -> str:
        """Prova de posse do telefone só pode criar ou vincular uma conta uma vez."""
        telefone = await self.store.consumir_prova(self.digest(prova))
        if not telefone:
            raise AuthError("Validação expirada. Verifique seu WhatsApp novamente.")
        return telefone
