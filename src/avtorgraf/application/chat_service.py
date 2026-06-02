from __future__ import annotations

from typing import Any

from avtorgraf.config import Settings
from avtorgraf.domain.models import AssistantAnswer, ChatMessage, Reference, new_session_id
from avtorgraf.infrastructure.database import ConversationRepository
from avtorgraf.infrastructure.lightrag_client import LightRagClient


class ChatService:
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
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Вопрос не может быть пустым")

        resolved_session_id = session_id or new_session_id()
        resolved_mode = mode or self.settings.default_query_mode
        self.repository.ensure_session(resolved_session_id, clean_question[:80])

        history_messages = self.repository.get_recent_messages(resolved_session_id)
        history = [
            {"role": message.role, "content": message.content}
            for message in history_messages
            if message.role in {"user", "assistant"}
        ]

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

    def _extract_answer(self, data: dict[str, Any]) -> str:
        for key in ("response", "answer", "result", "content", "data"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "LightRAG вернул ответ в неизвестном формате. Проверьте поле raw в API."

    def _extract_references(self, data: dict[str, Any]) -> list[Reference]:
        raw_refs = data.get("references") or data.get("refs") or data.get("sources") or []
        references: list[Reference] = []
        if isinstance(raw_refs, list):
            for item in raw_refs:
                if isinstance(item, str):
                    references.append(Reference(title=item))
                elif isinstance(item, dict):
                    title = (
                        item.get("title")
                        or item.get("file_path")
                        or item.get("document")
                        or item.get("source")
                        or "Источник"
                    )
                    references.append(
                        Reference(
                            title=str(title),
                            source=str(item.get("source", "")),
                            snippet=str(item.get("snippet", item.get("content", ""))),
                            metadata=item,
                        )
                    )
        return references
