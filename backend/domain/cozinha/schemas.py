from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StationCreate(Input):
    name: str = Field(default="Minha cozinha", min_length=1, max_length=80)


class LeaseRequest(Input):
    takeover: bool = False
    expected_revision: int = Field(ge=0)


class HeartbeatRequest(Input):
    lease_id: UUID


class CommandPayload(Input):
    block_id: str | None = Field(default=None, max_length=100)
    completed: bool | None = None
    query: str | None = Field(default=None, max_length=200)
    offset: int = Field(default=0, ge=0)
    selection_id: UUID | None = None
    ordinal: int | None = Field(default=None, ge=1, le=5)
    recipe_id: UUID | None = None
    section: Literal["ingredients", "preparation", "steps", "assembly"] | None = None


class KitchenCommand(Input):
    command_id: UUID
    expected_revision: int = Field(ge=0)
    lease_id: UUID
    type: Literal[
        "set_step_completed",
        "reset_steps",
        "search_recipe",
        "select_recipe",
        "open_recipe",
        "show_section",
        "next",
        "previous",
        "repeat",
        "continue_speech",
        "resume",
    ]
    payload: CommandPayload


class AcknowledgeRequest(Input):
    lease_id: UUID
    revision: int = Field(ge=0)
