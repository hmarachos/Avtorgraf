from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_session_id() -> str:
    return uuid4().hex


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    created_at: str = field(default_factory=now_utc_iso)


@dataclass(frozen=True)
class Reference:
    title: str
    source: str = ""
    snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantAnswer:
    session_id: str
    answer: str
    references: list[Reference]
    elapsed_ms: int
    raw: dict[str, Any] = field(default_factory=dict)
