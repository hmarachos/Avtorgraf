from __future__ import annotations

import sqlite3
from pathlib import Path

from avtorgraf.domain.models import ChatMessage, now_utc_iso


class ConversationRepository:
    """
    Репозиторий для хранения сессий и сообщений в SQLite.
    
    Предоставляет методы для создания сессий, добавления сообщений
    и получения истории диалогов.
    """
    
    def __init__(self, database_path: str) -> None:
        """
        Инициализирует репозиторий и создает схему БД.
        
        Args:
            database_path: Путь к файлу SQLite базы данных
        """
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """Создает подключение к базе данных."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Создает таблицы и индексы, если их еще нет."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)"
            )

    def ensure_session(self, session_id: str, title: str = "") -> None:
        """
        Создает сессию, если она еще не существует.
        
        Args:
            session_id: Уникальный идентификатор сессии
            title: Заголовок сессии (по умолчанию пустой)
        """
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(id, title, created_at) VALUES (?, ?, ?)",
                (session_id, title, now_utc_iso()),
            )

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """
        Добавляет сообщение в сессию.
        
        Args:
            session_id: ID сессии
            message: Сообщение для сохранения
        """
        self.ensure_session(session_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages(session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, message.role, message.content, message.created_at),
            )

    def get_recent_messages(self, session_id: str, limit: int = 8) -> list[ChatMessage]:
        """
        Получает последние сообщения из сессии.
        
        Args:
            session_id: ID сессии
            limit: Максимальное количество сообщений
            
        Returns:
            Список сообщений в хронологическом порядке
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [
            ChatMessage(role=row["role"], content=row["content"], created_at=row["created_at"])
            for row in reversed(rows)
        ]

    def list_sessions(self, limit: int = 20) -> list[dict[str, str]]:
        """
        Возвращает список сессий, отсортированных по времени последнего обновления.
        
        Args:
            limit: Максимальное количество сессий
            
        Returns:
            Список словарей с информацией о сессиях
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.title, s.created_at,
                       COALESCE(MAX(m.created_at), s.created_at) AS updated_at
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
                GROUP BY s.id
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
