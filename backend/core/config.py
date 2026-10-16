from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Banco de dados
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Segurança
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    whatsapp_auth_enabled: bool = False
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance: str = ""

    # IA e OCR
    google_ai_api_key: str = ""
    gemma_ocr_model: str = "gemma-4-26b-a4b-it"
    gemma_ocr_temperature: float = 0.1
    gemma_ocr_thinking_level: Literal["minimal"] = "minimal"
    ocr_provider: Literal["gemma", "openai", "hybrid"] = "gemma"
    ocr_vision_provider: Literal["gemma", "openai"] = "gemma"
    openai_api_key: str = ""
    openai_ocr_model: str = ""

    # WhatsApp — Evolution API v2 (serviço externo)
    evolution_enabled: bool = False
    evolution_webhook_secret: str = ""
    frontend_url: str = "http://localhost:3000"

    # Alexa requires explicit opt-in plus a complete skill and OAuth configuration.
    alexa_feature_enabled: bool = Field(default=False, validation_alias="ALEXA_ENABLED")
    alexa_skill_application_id: str = ""
    alexa_oauth_client_id: str = ""
    alexa_oauth_client_secret: SecretStr = SecretStr("")
    alexa_redirect_uris: list[str] = []

    # Monitoramento
    sentry_dsn: str = ""

    # Monitor iFood: loja de teste, inclusive hospedada na VPS; sem comandos de pedidos.
    ifood_enabled: bool = False
    ifood_mode: Literal["test"] = "test"
    ifood_client_id: UUID | None = None
    ifood_client_secret: SecretStr = SecretStr("")
    ifood_tenant_id: UUID | None = None
    ifood_test_merchant_id: UUID | None = None
    ifood_test_merchant_name: str = ""
    ifood_poll_interval_seconds: int = 30
    ifood_notifications_enabled: bool = False
    ifood_notifications_since: AwareDatetime | None = None
    ifood_whatsapp_enabled: bool = False
    ifood_whatsapp_phone: SecretStr = SecretStr("")

    # Ambiente
    environment: str = "development"
    debug: bool = False
    cors_origins: list[str] = []

    # A central opera por API; não compartilha sessões de usuários.
    central_enabled: bool = False
    central_service_token: SecretStr = SecretStr("")
    central_business_tenants: dict[UUID, UUID] = {}
    central_local_ocr_enabled: bool = False
    central_public_ocr_enabled: bool = False
    central_ocr_model: Literal["gemma-4-31b-it", "gemma-4-26b-a4b-it"] = "gemma-4-26b-a4b-it"

    @field_validator("ifood_client_id", "ifood_tenant_id", "ifood_test_merchant_id",
                     "ifood_notifications_since", mode="before")
    @classmethod
    def blank_ifood_id(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        """Impede inicialização de produção com configuração insegura."""
        if self.central_enabled and (
            len(self.central_service_token.get_secret_value()) < 32
            or not self.central_business_tenants
        ):
            raise ValueError("Configure credencial dedicada e vínculos de negócios da central")
        if self.ifood_poll_interval_seconds < 30:
            raise ValueError("O intervalo de consulta iFood deve ser de pelo menos 30 segundos")
        if self.ifood_notifications_enabled and (
            not self.ifood_enabled or self.ifood_notifications_since is None
        ):
            raise ValueError("Ative o monitor e configure o início dos alertas iFood")
        if self.ifood_whatsapp_enabled:
            import re
            if not self.ifood_notifications_enabled or not re.fullmatch(
                r"[1-9][0-9]{7,14}", self.ifood_whatsapp_phone.get_secret_value().lstrip("+")
            ):
                raise ValueError("Configure os alertas e o destinatário WhatsApp iFood")
            if not all((self.evolution_api_url, self.evolution_api_key, self.evolution_instance)):
                raise ValueError("Configure o transporte WhatsApp para os alertas iFood")
            if self.is_production and (
                not self.evolution_api_url.startswith("https://")
                or not self.frontend_url.startswith("https://")
            ):
                raise ValueError("Os alertas iFood exigem transporte e frontend HTTPS")
        if self.ifood_enabled:
            if not all((self.ifood_client_id, self.ifood_client_secret.get_secret_value().strip(),
                        self.ifood_tenant_id, self.ifood_test_merchant_id)):
                raise ValueError("Configure credenciais, tenant e merchant de teste para o iFood")
            if not self.ifood_test_merchant_name.startswith("Teste - "):
                raise ValueError("Configure o nome confirmado da loja de teste iFood")
        if self.whatsapp_auth_enabled:
            from urllib.parse import urlsplit
            parsed = urlsplit(self.evolution_api_url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or not self.evolution_api_key.strip() or not self.evolution_instance.strip():
                raise ValueError("Configure URL, API key e instância para o login por WhatsApp")
        if self.evolution_enabled:
            if not self.whatsapp_auth_enabled:
                raise ValueError("Ative WHATSAPP_AUTH_ENABLED para acesso às contas criadas na conversa")
            if not all((self.evolution_api_url, self.evolution_api_key, self.evolution_instance)):
                raise ValueError("Configure URL, API key e instância da Evolution API")
            if len(self.evolution_webhook_secret) < 32:
                raise ValueError("EVOLUTION_WEBHOOK_SECRET deve ter pelo menos 32 caracteres")
            if self.is_production and (
                not self.evolution_api_url.startswith("https://")
                or not self.frontend_url.startswith("https://")
            ):
                raise ValueError("Evolution e frontend devem usar HTTPS em produção")
        if self.alexa_feature_enabled:
            if not all(
                (
                    self.alexa_skill_application_id.strip(),
                    self.alexa_oauth_client_id.strip(),
                    len(self.alexa_oauth_client_secret.get_secret_value()) >= 24,
                    self.alexa_redirect_uris,
                )
            ):
                raise ValueError("ALEXA_ENABLED exige skill, cliente OAuth, segredo e redirects")
            if not self.frontend_url.startswith("https://") or any(
                not uri.startswith("https://") for uri in self.alexa_redirect_uris
            ):
                raise ValueError("A integração Alexa exige frontend e redirects HTTPS")
        if self.is_production:
            if self.whatsapp_auth_enabled and not self.evolution_api_url.startswith("https://"):
                raise ValueError("EVOLUTION_API_URL deve usar HTTPS em produção")
            if self.debug:
                raise ValueError("DEBUG deve ser false em produção")
            if len(self.secret_key) < 32 or self.secret_key == "gere-uma-chave-secreta-forte-aqui":
                raise ValueError(
                    "SECRET_KEY deve ser uma chave aleatória com pelo menos 32 caracteres"
                )
            if any(
                origin == "*" or not origin.startswith("https://") for origin in self.cors_origins
            ):
                raise ValueError("CORS_ORIGINS deve conter apenas origens HTTPS explícitas")
        return self

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def alexa_enabled(self) -> bool:
        return bool(
            self.alexa_feature_enabled
            and self.alexa_skill_application_id.strip()
            and self.alexa_oauth_client_id.strip()
            and len(self.alexa_oauth_client_secret.get_secret_value()) >= 24
            and self.alexa_redirect_uris
        )


settings = Settings()
