from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PROXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # upstream
    ollama_url: str = "http://127.0.0.1:11434"
    default_model: str = "qwen2.5-coder:7b"
    upstream_timeout: float = 600.0

    # server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # state
    keys_file: str = "data/keys.json"
    log_file: str = "data/requests.jsonl"

    # behaviour
    postprocess: bool = True
    inject_enabled: bool = True
    log_sse_frames: bool = False
    admin_token: str = "change-me"

    warning_text: str = (
        "Внимание: вы подключены к недоверенному API-прокси. "
        "Ваши промпты и ответы проходят через чужую инфраструктуру "
        "и могут быть изменены. Не используйте 'дешёвые' API-ключи "
        "от непроверенных продавцов."
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
