"""Redis compartilhado para limites, tentativas e consumo atômico do OTP."""
from redis.asyncio import Redis

_ENVIO = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
local phone = tonumber(redis.call('GET', KEYS[2]) or '0')
local ip = tonumber(redis.call('GET', KEYS[3]) or '0')
if phone >= 5 or ip >= 20 then return 0 end
redis.call('SET', KEYS[1], '1', 'EX', 60)
if redis.call('INCR', KEYS[2]) == 1 then redis.call('EXPIRE', KEYS[2], 3600) end
if redis.call('INCR', KEYS[3]) == 1 then redis.call('EXPIRE', KEYS[3], 3600) end
return 1
"""
_VERIFICAR = """
local hash = redis.call('HGET', KEYS[1], 'digest')
if not hash then return false end
local tentativas = redis.call('HINCRBY', KEYS[1], 'tentativas', 1)
if tentativas > 5 then redis.call('DEL', KEYS[1]); return false end
if hash ~= ARGV[1] then
  if tentativas >= 5 then redis.call('DEL', KEYS[1]) end
  return false
end
local telefone = redis.call('HGET', KEYS[1], 'telefone')
redis.call('DEL', KEYS[1])
return telefone
"""


class RedisOtpStore:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def permitir_envio(self, telefone_hash: str, ip_hash: str) -> bool:
        return bool(await self.redis.eval(_ENVIO, 3,
            f"otp:cooldown:{telefone_hash}", f"otp:phone:{telefone_hash}", f"otp:ip:{ip_hash}"))

    async def guardar_desafio(self, identificador: str, telefone: str, digest: str) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(f"otp:challenge:{identificador}", mapping={"telefone": telefone, "digest": digest, "tentativas": "0"})
            pipe.expire(f"otp:challenge:{identificador}", 300)
            await pipe.execute()

    async def remover_desafio(self, identificador: str) -> None:
        await self.redis.delete(f"otp:challenge:{identificador}")

    async def verificar(self, identificador: str, digest: str) -> str | None:
        valor = await self.redis.eval(_VERIFICAR, 1, f"otp:challenge:{identificador}", digest)
        return valor or None

    async def guardar_prova(self, prova: str, telefone: str) -> None:
        await self.redis.set(f"otp:proof:{prova}", telefone, ex=600)

    async def consumir_prova(self, prova: str) -> str | None:
        return await self.redis.getdel(f"otp:proof:{prova}")
