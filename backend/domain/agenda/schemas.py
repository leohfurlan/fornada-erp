import re
from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

TipoAgendaItem = Literal["receita", "pedido", "tarefa"]

# Tipos válidos de item de agenda (mesma fonte de verdade do service).
TIPOS_VALIDOS: frozenset[str] = frozenset({"receita", "pedido", "tarefa"})

_COR_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _validar_cor(cor: str | None) -> str | None:
    if cor is not None and not _COR_HEX_RE.match(cor):
        raise ValueError("Cor deve estar no formato hexadecimal, ex: #f97316")
    return cor


def _validar_horario(hora_inicio: time | None, hora_fim: time | None) -> None:
    # hora_fim só faz sentido junto de hora_inicio, e deve ser posterior.
    if hora_fim is not None and hora_inicio is None:
        raise ValueError("Defina a hora de início antes da hora de término")
    if hora_inicio is not None and hora_fim is not None and hora_fim <= hora_inicio:
        raise ValueError("A hora de término deve ser maior que a hora de início")


class CriarAgendaItemRequest(BaseModel):
    titulo: str
    tipo: TipoAgendaItem
    data: date
    hora_inicio: time | None = None
    hora_fim: time | None = None
    cor: str | None = None
    observacoes: str | None = None
    receita_id: UUID | None = None
    pedido_id: UUID | None = None
    ordem_producao_id: UUID | None = None

    @model_validator(mode="after")
    def _validar(self) -> "CriarAgendaItemRequest":
        _validar_cor(self.cor)
        _validar_horario(self.hora_inicio, self.hora_fim)
        return self


class AtualizarAgendaItemRequest(BaseModel):
    """PATCH semântico — todos os campos opcionais.

    Campos não enviados não são alterados (model_dump(exclude_unset=True)).
    """

    titulo: str | None = None
    tipo: TipoAgendaItem | None = None
    data: date | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    cor: str | None = None
    observacoes: str | None = None
    concluido: bool | None = None
    receita_id: UUID | None = None
    pedido_id: UUID | None = None
    ordem_producao_id: UUID | None = None

    @model_validator(mode="after")
    def _validar(self) -> "AtualizarAgendaItemRequest":
        _validar_cor(self.cor)
        _validar_horario(self.hora_inicio, self.hora_fim)
        return self


class MoverAgendaItemRequest(BaseModel):
    """Drag-and-drop: muda só data e (opcionalmente) horário."""

    data: date
    hora_inicio: time | None = None
    hora_fim: time | None = None

    @model_validator(mode="after")
    def _validar(self) -> "MoverAgendaItemRequest":
        _validar_horario(self.hora_inicio, self.hora_fim)
        return self


class ConcluirAgendaItemRequest(BaseModel):
    concluido: bool


class AgendaItemResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    titulo: str
    tipo: str
    data: date
    hora_inicio: time | None
    hora_fim: time | None
    cor: str | None
    concluido: bool
    observacoes: str | None
    receita_id: UUID | None
    pedido_id: UUID | None
    ordem_producao_id: UUID | None
    # Campos derivados de join — preenchidos pelo service.
    nome_receita: str | None
    nome_pedido: str | None
    numero_op: int | None
    duracao_minutos: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
