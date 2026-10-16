import pytest
from pydantic import ValidationError

from core.config import Settings


def _settings(**values: object) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://user:password@localhost/fornada_test",
        secret_key="local-static-analysis-only",
        **values,
    )


def test_alexa_is_disabled_by_default() -> None:
    assert _settings().alexa_enabled is False


def test_alexa_opt_in_requires_complete_https_configuration() -> None:
    with pytest.raises(ValidationError, match="ALEXA_ENABLED exige"):
        _settings(ALEXA_ENABLED=True)


def test_alexa_opt_in_activates_only_with_all_credentials_and_redirects() -> None:
    settings = _settings(
        ALEXA_ENABLED=True,
        alexa_skill_application_id="amzn1.ask.skill.test",
        alexa_oauth_client_id="test-client",
        alexa_oauth_client_secret="test-secret-with-at-least-24-chars",
        alexa_redirect_uris=["https://pitangui.amazon.com/api/skill/link/M123"],
        frontend_url="https://fornada.example.com",
    )

    assert settings.alexa_enabled is True


def test_alexa_opt_in_rejects_insecure_redirects() -> None:
    with pytest.raises(ValidationError, match="frontend e redirects HTTPS"):
        _settings(
            ALEXA_ENABLED=True,
            alexa_skill_application_id="amzn1.ask.skill.test",
            alexa_oauth_client_id="test-client",
            alexa_oauth_client_secret="test-secret-with-at-least-24-chars",
            alexa_redirect_uris=["http://localhost/callback"],
            frontend_url="https://fornada.example.com",
        )
