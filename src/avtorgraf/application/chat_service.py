from __future__ import annotations

from typing import Any

from avtorgraf.config import Settings
from avtorgraf.domain.models import AssistantAnswer, ChatMessage, Reference, new_session_id
from avtorgraf.infrastructure.database import ConversationRepository
from avtorgraf.infrastructure.lightrag_client import LightRagClient


class ChatService:
    """
    Сервис для обработки вопросов пользователя.
    
    Объединяет логику работы с историей сессий, запросы к LightRAG 
    и формирование ответов с нормативными ссылками.
    """
    
    def __init__(
        self,
        settings: Settings,
        repository: ConversationRepository,
        lightrag: LightRagClient,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.lightrag = lightrag

    def ask(self, question: str, session_id: str | None, mode: str | None) -> AssistantAnswer:
        """
        Обрабатывает вопрос пользователя и возвращает ответ от LightRAG.
        
        Args:
            question: Вопрос пользователя
            session_id: ID сессии (создается новая, если не указан)
            mode: Режим поиска LightRAG (mix/hybrid/global/local/naive)
            
        Returns:
            Ответ ассистента с нормативными ссылками
            
        Raises:
            ValueError: Если вопрос пустой
        """
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Вопрос не может быть пустым")

        resolved_session_id = session_id or new_session_id()
        resolved_mode = mode or self.settings.default_query_mode
        self.repository.ensure_session(resolved_session_id, clean_question[:80])

        history_messages = self.repository.get_recent_messages(resolved_session_id)
        history = self._format_history(history_messages)

        data, elapsed_ms = self.lightrag.query(
            question=clean_question,
            mode=resolved_mode,
            user_prompt=self.settings.system_prompt,
            history=history,
        )
        
        answer = self._extract_answer(data)
        references = self._extract_references(data)

        self.repository.add_message(
            resolved_session_id, ChatMessage(role="user", content=clean_question)
        )
        self.repository.add_message(
            resolved_session_id, ChatMessage(role="assistant", content=answer)
        )

        return AssistantAnswer(
            session_id=resolved_session_id,
            answer=answer,
            references=references,
            elapsed_ms=elapsed_ms,
            raw=data,
        )

    def _format_history(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        """Форматирует историю сообщений для отправки в LightRAG."""
        return [
            {"role": message.role, "content": message.content}
            for message in messages
            if message.role in {"user", "assistant"}
        ]

    def _extract_answer(self, data: dict[str, Any]) -> str:
        """
        Извлекает текст ответа из ответа LightRAG.
        Пытается несколько стандартных ключей.
        """
        for key in ("response", "answer", "result", "content", "data"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "LightRAG вернул ответ в неизвестном формате. Проверьте поле raw в API."

    def _extract_references(self, data: dict[str, Any]) -> list[Reference]:
        """
        Извлекает нормативные ссылки из ответа LightRAG.
        Поддерживает несколько форматов ответа.
        """
        raw_refs = data.get("references") or data.get("refs") or data.get("sources") or []
        references: list[Reference] = []
        
        if isinstance(raw_refs, list):
            for item in raw_refs:
                ref = self._parse_reference_item(item)
                if ref:
                    references.append(ref)
        
        return references

    def _parse_reference_item(self, item: Any) -> Reference | None:
        """Парсит отдельный элемент ссылки из ответа LightRAG."""
        if isinstance(item, str):
            return Reference(title=item) if item.strip() else None
        
        if isinstance(item, dict):
            title = (
                item.get("title")
                or item.get("file_path")
                or item.get("document")
                or item.get("source")
                or "Источник"
            )
            return Reference(
                title=str(title),
                source=str(item.get("source", "")),
                snippet=str(item.get("snippet", item.get("content", ""))),
                metadata=item,
            )
        
        return None
