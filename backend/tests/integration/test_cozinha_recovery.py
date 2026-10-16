from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_authenticated_actor
from infrastructure.database.models import Tenant, Usuario
from main import app


@pytest.mark.asyncio
async def test_refresh_takeover_revokes_old_lease_and_rejects_late_ack(
    client: AsyncClient, db: AsyncSession
) -> None:
    assert db.bind is not None
    assert db.bind.url.database.startswith("fornada_central_test_")
    tenant = Tenant(nome="Cozinha recovery")
    db.add(tenant)
    await db.flush()
    user = Usuario(
        tenant_id=tenant.id,
        nome="Teste cozinha",
        email=f"{uuid4()}@example.invalid",
        senha_hash="unused",
    )
    db.add(user)
    await db.flush()
    app.dependency_overrides[get_authenticated_actor] = lambda: user

    created = await client.post("/api/v1/cozinha/stations", json={"name": "Bancada"})
    assert created.status_code == 201, created.text
    station_id = created.json()["station"]["id"]
    first = await client.post(
        f"/api/v1/cozinha/stations/{station_id}/lease",
        json={"expected_revision": 0, "takeover": False},
    )
    assert first.status_code == 200, first.text
    old_lease = first.json()["lease_id"]

    # Uma aba reaberta conhece a revisão persistida, mas precisa de takeover explícito.
    summary = await client.get("/api/v1/cozinha/stations")
    assert summary.json()["items"][0]["revision"] == first.json()["station"]["revision"]
    occupied = await client.post(
        f"/api/v1/cozinha/stations/{station_id}/lease",
        json={"expected_revision": summary.json()["items"][0]["revision"], "takeover": False},
    )
    assert occupied.status_code == 409

    takeover = await client.post(
        f"/api/v1/cozinha/stations/{station_id}/lease",
        json={"expected_revision": summary.json()["items"][0]["revision"], "takeover": True},
    )
    assert takeover.status_code == 200, takeover.text
    new_lease = takeover.json()["lease_id"]
    revision = takeover.json()["station"]["revision"]

    stale_heartbeat = await client.post(
        f"/api/v1/cozinha/stations/{station_id}/heartbeat", json={"lease_id": old_lease}
    )
    assert stale_heartbeat.status_code == 409
    current = await client.get(
        f"/api/v1/cozinha/stations/{station_id}",
        params={"lease_id": new_lease, "after_revision": revision - 1},
    )
    assert current.status_code == 200
    assert current.json()["station"]["revision"] == revision

    future_ack = await client.post(
        f"/api/v1/cozinha/stations/{station_id}/ack",
        json={"lease_id": new_lease, "revision": revision + 1},
    )
    assert future_ack.status_code == 409
    accepted_ack = await client.post(
        f"/api/v1/cozinha/stations/{station_id}/ack",
        json={"lease_id": new_lease, "revision": revision},
    )
    assert accepted_ack.status_code == 200, accepted_ack.text
    late_ack = await client.post(
        f"/api/v1/cozinha/stations/{station_id}/ack",
        json={"lease_id": new_lease, "revision": revision - 1},
    )
    assert late_ack.status_code == 409
