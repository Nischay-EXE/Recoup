from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    razorpay_webhook_secret: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
