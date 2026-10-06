import pytest
from pydantic import ValidationError

from core.config import Settings


def production_settings(**overrides: object) -> Settings:
    values = dict(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        secret_key="x" * 48,
        environment="production",
        debug=False,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": "short"},
        {"debug": True},
        {"cors_origins": ["*"]},
        {"cors_origins": ["http://localhost:3000"]},
    ],
)
def test_rejects_unsafe_production(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        production_settings(**overrides)


def test_accepts_same_origin_production() -> None:
    assert production_settings().is_production


def test_accepts_explicit_https_origin() -> None:
    assert production_settings(cors_origins=["https://erp.example.com"]).cors_origins
