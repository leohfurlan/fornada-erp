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

    # IA e OCR
    google_ai_api_key: str = ""

    # Monitoramento
    sentry_dsn: str = ""

    # Ambiente
    environment: str = "development"
    debug: bool = False

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
