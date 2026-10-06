import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from api.routers.whatsapp_auth import get_otp_service
from domain.exceptions import AuthError, ValidationError
from domain.usuarios.otp import OtpService
from infrastructure.cache.otp_store import RedisOtpStore
from main import app


class CapturarEnvio:
    codigo = ""
    falhar = False

    async def enviar_codigo(self, telefone: str, codigo: str) -> None:
        self.codigo = codigo
        if self.falhar:
            raise RuntimeError("Transporte indisponível")


@pytest_asyncio.fixture
async def otp():
    url = os.getenv("TEST_REDIS_URL")
    if not url:
        pytest.skip("Configure TEST_REDIS_URL para Redis isolado de teste")
    redis = Redis.from_url(url, decode_responses=True)
    sender = CapturarEnvio()
    service = OtpService(RedisOtpStore(redis), sender, "segredo-isolado-teste")
    yield service, sender, redis
    await redis.aclose()


@pytest.mark.asyncio
async def test_codigo_prova_uso_unico_e_concorrencia(otp):
    service, sender, redis = otp
    telefone = f"+55{uuid4().int % 10**11:011d}"
    desafio = await service.solicitar(telefone, uuid4().hex)
    assert 0 < await redis.ttl(f"otp:challenge:{desafio}") <= 300
    resultado = await asyncio.gather(service.verificar(desafio, sender.codigo), service.verificar(desafio, sender.codigo), return_exceptions=True)
    provas = [r for r in resultado if isinstance(r, str)]
    assert len(provas) == 1
    assert sum(isinstance(r, AuthError) for r in resultado) == 1
    assert await service.consumir_prova(provas[0]) == telefone
    with pytest.raises(AuthError):
        await service.consumir_prova(provas[0])


@pytest.mark.asyncio
async def test_limite_tentativas_expiracao_e_reenvio(otp):
    service, sender, redis = otp
    telefone = f"+55{uuid4().int % 10**11:011d}"
    desafio = await service.solicitar(telefone, uuid4().hex)
    with pytest.raises(ValidationError):
        await service.solicitar(telefone, uuid4().hex)
    errado = "000000" if sender.codigo != "000000" else "111111"
    for _ in range(5):
        with pytest.raises(AuthError):
            await service.verificar(desafio, errado)
    with pytest.raises(AuthError):
        await service.verificar(desafio, sender.codigo)
    desafio = await service.solicitar(f"+55{uuid4().int % 10**11:011d}", uuid4().hex)
    await redis.expire(f"otp:challenge:{desafio}", 0)
    with pytest.raises(AuthError):
        await service.verificar(desafio, sender.codigo)


@pytest.mark.asyncio
async def test_falha_envio_invalida_desafio(otp):
    service, sender, redis = otp
    sender.falhar = True
    capturado = ""
    original = service.store.guardar_desafio
    async def capturar(identificador, telefone, digest):
        nonlocal capturado
        capturado = identificador
        await original(identificador, telefone, digest)
    service.store.guardar_desafio = capturar
    with pytest.raises(RuntimeError):
        await service.solicitar(uuid4().hex, uuid4().hex)
    assert not await redis.exists(f"otp:challenge:{capturado}")


@pytest.mark.asyncio
async def test_onboarding_e_login_com_numero_verificado(client, otp):
    service, _, _ = otp
    async def override():
        yield service
    app.dependency_overrides[get_otp_service] = override
    telefone = f"+55{uuid4().int % 10**11:011d}"
    prova = "p" + uuid4().hex + uuid4().hex
    await service.store.guardar_prova(service.digest(prova), telefone)
    resposta = await client.post("/api/v1/auth/whatsapp/entrar", json={"prova": prova})
    assert resposta.status_code == 200
    onboarding = resposta.json()["onboarding_prova"]
    cadastro = await client.post("/api/v1/auth/whatsapp/cadastro", json={
        "prova": onboarding, "nome": "Confeiteira", "nome_negocio": "Loja piloto",
        "email": f"teste-{uuid4().hex}@example.com", "endereco": {
            "pais": "BR", "cep": "01001000", "logradouro": "Rua teste", "numero": "1",
            "bairro": "Centro", "cidade": "São Paulo", "estado": "SP",
        },
    })
    assert cadastro.status_code == 201, cadastro.text
    assert cadastro.json()["usuario"]["telefone"] == telefone
    # Número verificado identifica a mesma conta; sem duplicar tenant.
    prova2 = "p" + uuid4().hex + uuid4().hex
    await service.store.guardar_prova(service.digest(prova2), telefone)
    login = await client.post("/api/v1/auth/whatsapp/entrar", json={"prova": prova2})
    assert login.status_code == 200
    assert login.json()["tokens"]["usuario"]["id"] == cadastro.json()["usuario"]["id"]
    repetido = await client.post("/api/v1/auth/whatsapp/entrar", json={"prova": prova2})
    assert repetido.status_code == 401
