import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_TOKEN: str
    ADMIN_ID: int = 52946005
    WEBHOOK_PATH: str = "/webhook"
    SECRET_TOKEN: str
    DATABASE_URL: str = "sqlite:///./data.db"
    DAILY_PROMPT_TIME: str = "14:00"
    PROMPT_TIMEOUT_MINUTES: int = 15

    class Config:
        env_file = ".env"

settings = Settings()
