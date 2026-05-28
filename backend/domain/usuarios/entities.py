from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass
class Tenant:
    nome: str
    plano: str = "starter"
    ativo: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None


@dataclass
class Usuario:
    tenant_id: UUID
    email: str
    senha_hash: str
    nome: str
    valor_hora: Decimal = field(default_factory=lambda: Decimal("0"))
    ativo: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None
