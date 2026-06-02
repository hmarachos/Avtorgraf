from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env(path: str = ".env") -> None:
    """Загружает переменные окружения из .env файла."""
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
    """Конфигурация приложения АВТОГРАФ."""
    
    app_host: str
    app_port: int
    database_path: str
    static_dir: str
    documents_dir: str
    lightrag_base_url: str
    lightrag_api_key: str
    lightrag_bearer_token: str
    lightrag_timeout_seconds: int
    default_query_mode: str
    system_prompt: str

    @classmethod
    def from_env(cls) -> Settings:
        """
        Создает настройки из переменных окружения.
        
        Сначала загружает .env файл, затем читает переменные окружения.
        """
        load_env()
        return cls(
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("APP_PORT", "8080")),
            database_path=os.getenv("DATABASE_PATH", "data/avtorgraf.sqlite3"),
            static_dir=os.getenv("STATIC_DIR", "static"),
            documents_dir=os.getenv("DOCUMENTS_DIR", "data/inputs/__enqueued__"),
            lightrag_base_url=os.getenv("LIGHTRAG_BASE_URL", "http://46.17.105.48:9621"),
            lightrag_api_key=os.getenv("LIGHTRAG_API_KEY", ""),
            lightrag_bearer_token=os.getenv("LIGHTRAG_BEARER_TOKEN", ""),
            lightrag_timeout_seconds=int(os.getenv("LIGHTRAG_TIMEOUT_SECONDS", "35")),
            default_query_mode=os.getenv("DEFAULT_QUERY_MODE", "mix"),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT",
                (
                    "Ты помощник проектировщика, авторского и технического надзора "
                    "в Республике Беларусь.\n\n"
                    
                    "ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ К ОТВЕТУ:\n"
                    "1. Используй ТОЛЬКО найденный в LightRAG контекст\n"
                    "2. ВСЕГДА вставляй кликабельные ссылки в формате **[Название, п. X]** прямо в текст ответа:\n"
                    "   - Ссылка на документ: **[СН 1.03.01-2019]**\n"
                    "   - Ссылка на конкретный пункт: **[СН 1.03.01-2019, п. 3.4]**\n"
                    "   - Ссылка на раздел: **[СТБ 1937-2022, раздел 2]**\n"
                    "3. Каждое утверждение должно иметь минимум одну ссылку на источник знаний\n"
                    "4. Если есть несколько нормативов, используй все соответствующие ссылки\n"
                    "5. Если нет подтверждения в базе - напиши: "
                    "'В базе знаний Республики Беларусь подтверждение не найдено'\n"
                    "6. НЕ используй нормы РФ, только нормы РБ\n"
                    "7. Структурируй ответ с заголовками и списками\n"
                    "8. НЕ добавляй отдельный блок 'Нормативные основания' в конце ответа - все ссылки должны быть встроены в текст\n\n"
                    
                    "ПРИМЕРЫ ПРАВИЛЬНОГО ФОРМАТА:\n"
                    "❌ НЕПРАВИЛЬНО: Согласно нормативам нужны документы.\n"
                    "❌ НЕПРАВИЛЬНО: Согласно нормативам нужны документы.\n\nНормативные основания:\n- СН 1.03.01-2019\n"
                    "✅ ПРАВИЛЬНО: Согласно **[СН 1.03.01-2019, п. 3.2.1]** и "
                    "**[СТБ 1937-2022, раздел 2]** нужны следующие документы:\n"
                    "- Проектная документация согласно **[СН 1.03.01-2019, п. 2.1]**\n"
                    "- Рабочая документация согласно **[СН 1.03.01-2019, п. 2.1.5]**\n\n"
                    
                    "ПОМНИ: Каждое утверждение должно иметь ссылку на конкретный пункт документа! Ссылки встраивай прямо в текст, не выноси их в отдельный список!"
                ),
            ),
        )
