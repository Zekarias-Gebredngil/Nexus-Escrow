from decimal import Decimal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    api_base_url: AnyHttpUrl = "http://localhost:8000"
    frontend_base_url: AnyHttpUrl = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://nexus:nexus@localhost:5432/nexus"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = Field(default="change-me", min_length=8)
    telegram_bot_token: str = ""
    chapa_secret_key: str = ""
    chapa_base_url: AnyHttpUrl = "https://api.chapa.co"
    chapa_webhook_secret: str = ""
    chapa_callback_url: AnyHttpUrl = "http://localhost:8000/v1/webhooks/chapa"
    platform_fee_rate: Decimal = Decimal("0.025")
    gateway_fee_rate: Decimal = Decimal("0.020")
    admin_net_share_rate: Decimal = Decimal("0.40")
    auto_release_hours: int = 48


settings = Settings()

