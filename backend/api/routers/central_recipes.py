"""Authenticated service-only recipe reads with live tenant/principal validation."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.central import Input, actor, authenticated
from domain.receitas.central_snapshot import fingerprint, search, snapshot
from infrastructure.database.session import get_db

router = APIRouter(
    prefix="/central/recipes", tags=["Central"], dependencies=[Depends(authenticated)]
)


class Search(Input):
    query: str = Field(min_length=1, max_length=200)
    offset: int = Field(default=0, ge=0, strict=True)
    limit: int = Field(default=10, ge=1, le=20, strict=True)

    @field_validator("query")
    @classmethod
    def meaningful(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("Nome inválido")
        return value.strip()


class Read(Input):
    recipe_id: UUID


class Operation(Input):
    operation_id: UUID
    command_id: UUID
    business_id: UUID
    capability_code: Literal["recipes.search", "recipes.read"]
    payload: dict
    authorization_receipt_ref: UUID | None = None
    approval_receipt_ref: UUID | None = None
    expected_resource_version: str | None = None
    idempotency_key: UUID
    conversation_id: UUID | None = None
    principal_ref: UUID
    scope: dict

    @model_validator(mode="after")
    def validate_payload(self):
        schema = Search if self.capability_code == "recipes.search" else Read
        self.payload = schema.model_validate(self.payload).model_dump(mode="json")
        return self


def result(request, user, data):
    return {
        "status": "confirmed",
        "business_id": str(request.business_id),
        "principal_ref": str(user.id),
        "scope": request.scope,
        "resource_version": data.get("version") or fingerprint(data),
        "evidence_ref": "fornada:recipe:" + str(request.operation_id),
        "data": data,
        "external_reference": data.get("recipe_id") or str(request.operation_id),
    }


@router.post("/search")
async def search_recipes(request: Operation, db: AsyncSession = Depends(get_db)):
    if request.capability_code != "recipes.search":
        raise HTTPException(422, "Capacidade inválida")
    payload = Search.model_validate(request.payload)
    user = await actor(
        db, request.business_id, principal=request.principal_ref, scope=request.scope
    )
    return result(request, user, await search(db, user.tenant_id, **payload.model_dump()))


@router.post("/read")
async def read_recipe(request: Operation, db: AsyncSession = Depends(get_db)):
    if request.capability_code != "recipes.read":
        raise HTTPException(422, "Capacidade inválida")
    payload = Read.model_validate(request.payload)
    user = await actor(
        db, request.business_id, principal=request.principal_ref, scope=request.scope
    )
    try:
        data = await snapshot(db, user.tenant_id, payload.recipe_id)
    except ValueError:
        raise HTTPException(
            422, "Cadastro operacional inválido; revise a receita no Fornada"
        ) from None
    if data is None:
        raise HTTPException(404, "Receita não encontrada")
    if request.expected_resource_version and request.expected_resource_version != data["version"]:
        raise HTTPException(409, "Receita alterada")
    return result(request, user, data)
