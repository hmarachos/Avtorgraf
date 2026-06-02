from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def now_utc_iso() -> str:
    """Возвращает текущее время в UTC в формате ISO 8601."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_session_id() -> str:
    """Генерирует уникальный идентификатор сессии."""
    return uuid4().hex


@dataclass(frozen=True)
class ChatMessage:
    """Сообщение в чате между пользователем и ассистентом."""
    
    role: str  # "user" или "assistant"
    content: str
    created_at: str = field(default_factory=now_utc_iso)


@dataclass(frozen=True)
class Reference:
    """Нормативная ссылка из базы знаний LightRAG."""
    
    title: str
    source: str = ""
    snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantAnswer:
    """Ответ ассистента на вопрос пользователя."""
    
    session_id: str
    answer: str
    references: list[Reference]
    elapsed_ms: int
    raw: dict[str, Any] = field(default_factory=dict)
