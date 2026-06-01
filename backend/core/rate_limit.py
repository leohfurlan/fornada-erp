"""Limiter compartilhado entre main.py e routers que aplicam @limiter.limit(...)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Instância única do projeto — importada em main.py (handler) e nos routers
# que precisam decorar rotas com @limiter.limit("X/minute") etc.
limiter = Limiter(key_func=get_remote_address)
