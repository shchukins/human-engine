from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    database_url: str = Field(alias="DATABASE_URL")
    strava_verify_token: str = Field(alias="STRAVA_VERIFY_TOKEN")
    strava_client_id: str = Field(alias="STRAVA_CLIENT_ID")
    strava_client_secret: str = Field(alias="STRAVA_CLIENT_SECRET")
    strava_redirect_uri: str = Field(alias="STRAVA_REDIRECT_URI")

    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")
    telegram_notify_on_webhook_success: bool = Field(
        default=False,
        alias="TELEGRAM_NOTIFY_ON_WEBHOOK_SUCCESS",
    )
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(
        default="qwen2.5:7b",
        alias="OLLAMA_MODEL",
    )
    ollama_fallback_model: str = Field(
        default="qwen3.5:4b",
        alias="OLLAMA_FALLBACK_MODEL",
    )
    ollama_timeout_seconds: int = Field(
        default=120,
        alias="OLLAMA_TIMEOUT_SECONDS",
    )

settings = Settings()