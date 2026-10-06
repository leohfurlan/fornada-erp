from pydantic import model_validator
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

    # WhatsApp — Evolution API v2 (serviço externo)
    evolution_enabled: bool = False
    evolution_webhook_secret: str = ""
    frontend_url: str = "http://localhost:3000"

    # Monitoramento
    sentry_dsn: str = ""

    # Ambiente
    environment: str = "development"
    debug: bool = False
    cors_origins: list[str] = []

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        """Impede inicialização de produção com configuração insegura."""
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


settings = Settings()
