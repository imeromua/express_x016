from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram
    bot_token: str
    group_id: int

    # Admins
    admin_ids: List[int] = []

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    # Database
    postgres_dsn: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # VirusTotal
    virustotal_api_key: str = ""

    # Broadcast
    broadcast_delay: float = 0.05

    # Onboarding
    registration_timeout_minutes: int = 30

    # Timezone
    timezone: str = "Europe/Kyiv"


@lru_cache
def get_settings() -> Settings:
    return Settings()
