from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    database_path: str
    static_dir: str
    lightrag_base_url: str
    lightrag_api_key: str
    lightrag_bearer_token: str
    lightrag_timeout_seconds: int
    default_query_mode: str
    system_prompt: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        return cls(
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("APP_PORT", "8080")),
            database_path=os.getenv("DATABASE_PATH", "data/avtorgraf.sqlite3"),
            static_dir=os.getenv("STATIC_DIR", "static"),
            lightrag_base_url=os.getenv("LIGHTRAG_BASE_URL", "http://46.17.105.48:9621"),
            lightrag_api_key=os.getenv("LIGHTRAG_API_KEY", ""),
            lightrag_bearer_token=os.getenv("LIGHTRAG_BEARER_TOKEN", ""),
            lightrag_timeout_seconds=int(os.getenv("LIGHTRAG_TIMEOUT_SECONDS", "35")),
            default_query_mode=os.getenv("DEFAULT_QUERY_MODE", "mix"),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT",
                (
                    "Отвечай как помощник проектировщика, авторского и технического надзора "
                    "в Республике Беларусь. Используй только найденный в LightRAG контекст. "
                    "Если в базе нет подтверждения, прямо скажи, что нормативное основание "
                    "не найдено. Обязательно указывай пункты СН, СТБ, инструкций или кодексов РБ, "
                    "когда они присутствуют в контексте. Не подменяй нормы РБ нормами РФ."
                ),
            ),
        )
