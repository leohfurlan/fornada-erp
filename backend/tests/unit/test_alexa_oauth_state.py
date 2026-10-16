from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routers import alexa


@pytest.fixture
def oauth_app(monkeypatch):
    redirect = "https://pitangui.amazon.com/api/skill/link/TEST"
    monkeypatch.setattr(
        alexa,
        "settings",
        SimpleNamespace(
            alexa_enabled=True,
            alexa_oauth_client_id="test-client",
            alexa_redirect_uris=[redirect],
            frontend_url="https://fornada.example.com",
        ),
    )
    saved = []

    def add(context):
        context.id = uuid4()
        saved.append(context)

    db = SimpleNamespace(execute=AsyncMock(), add=add, commit=AsyncMock())
    app = FastAPI()
    app.include_router(alexa.router)
    app.dependency_overrides[alexa.get_db] = lambda: db
    return app, db, saved, redirect


@pytest.mark.parametrize("length", [512, 1096, 8192])
async def test_authorize_preserves_amazon_state(oauth_app, length):
    app, db, saved, redirect = oauth_app
    # Amazon sent 1096 characters in the pilot. Include URL-sensitive characters
    # to catch truncation or changes when the opaque state is later returned.
    state = ("opaque+state/%=&" * (length // 15 + 1))[:length]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get(
            "/integrations/alexa/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "test-client",
                "redirect_uri": redirect,
                "state": state,
            },
        )
    assert response.status_code == 303, response.text
    assert response.headers["cache-control"] == "no-store"
    assert saved[0].state == state
    assert saved[0].redirect_uri == redirect
    assert parse_qs(urlsplit(response.headers["location"]).query) == {
        "context": [str(saved[0].id)]
    }
    returned = alexa._redirect_with(redirect, {"code": "test-code", "state": saved[0].state})
    assert parse_qs(urlsplit(returned).query)["state"] == [state]
    db.commit.assert_awaited_once()


@pytest.mark.parametrize(
    ("state", "wrong_redirect"),
    [("", False), ("s" * 8193, False), ("s" * 1096, True)],
)
async def test_authorize_rejects_invalid_state_or_redirect(oauth_app, state, wrong_redirect):
    app, db, saved, redirect = oauth_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get(
            "/integrations/alexa/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "test-client",
                "redirect_uri": (
                    "https://untrusted.example/callback" if wrong_redirect else redirect
                ),
                "state": state,
            },
        )
    assert response.status_code == 400
    assert saved == []
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()
