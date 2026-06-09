from __future__ import annotations

from typing import Any

from avtorgraf.config import Settings
from avtorgraf.domain.models import AssistantAnswer, Reference, new_session_id
from avtorgraf.infrastructure.lightrag_client import LightRagClient
from avtorgraf.infrastructure.vision_client import VisionClient, VisionError


class ImageAnalysisService:
    """
    Сервис для анализа фотографий строительных нарушений.
    
    Реализует 3-шаговый процесс:
    1. Анализ изображения через Vision модель
    2. Формирование поискового запроса для LightRAG
    3. Генерация ответа с нормативными ссылками
    """
    
    # Промпт для финального ответа с найденными нарушениями
    FINAL_PROMPT = """На основе описания нарушений на строительной площадке и найденных нормативных документов составь ответ.

СТРУКТУРА ОТВЕТА (строго соблюдай):

## Выявленные нарушения

[ОБЯЗАТЕЛЬНО начни с нарушений, связанных с ОСНОВНЫМ ЗАПРОСОМ ПОЛЬЗОВАТЕЛЯ. 
Если это котлован/откосы - опиши ИХ В ПЕРВУЮ ОЧЕРЕДЬ.
Опиши нарушения в 1-2 абзацах. Каждое утверждение подкрепи ссылкой на документ в формате **[Документ, п. X]**]

---

## Методы устранения

[Опиши методы устранения нарушений в 1-2 абзацах, ссылаясь на нормативные документы. 
СНАЧАЛА методы устранения для основного запроса, ПОТОМ остальное.
Каждое действие подкрепи ссылкой в формате **[Документ, п. X]**]

---

ВАЖНО:
- Используй ТОЛЬКО найденный в LightRAG контекст
- Каждое утверждение должно иметь ссылку на конкретный пункт документа
- Ссылки встраивай прямо в текст в формате **[СН 1.03.01-2019, п. 3.4]**
- ПРИОРИТЕТ темам из запроса пользователя (котлован, откосы и т.д.)
- Отвечай кратко и по делу
- Действуй в строгом соответствии с инструкцией об осуществлении авторского надзора в Республике Беларусь"""
    
    def __init__(
        self,
        settings: Settings,
        lightrag: LightRagClient,
        vision: VisionClient,
    ) -> None:
        self.settings = settings
        self.lightrag = lightrag
        self.vision = vision
    
    def analyze_photo(
        self,
        image_data: bytes,
        image_format: str,
        session_id: str | None = None,
        focus_hint: str = "",
    ) -> AssistantAnswer:
        """
        Анализирует фотографию строительной площадки.
        
        Args:
            image_data: Бинарные данные изображения
            image_format: Формат изображения (jpeg, png, webp)
            session_id: ID сессии (создается новая, если не указан)
            focus_hint: Текстовый запрос для фокусировки внимания модели
            
        Returns:
            Ответ с описанием нарушений и методами устранения
            
        Raises:
            VisionError: При ошибке анализа изображения
        """
        resolved_session_id = session_id or new_session_id()
        total_elapsed_ms = 0
        
        # ===== ШАГ 1: Анализ фотографии =====
        step1_result, step1_ms = self.vision.analyze_image(image_data, image_format, focus_hint)
        total_elapsed_ms += step1_ms
        
        # Извлекаем описание нарушений из ответа
        violations_description = self._extract_violations(step1_result)
        
        if not violations_description:
            return AssistantAnswer(
                session_id=resolved_session_id,
                answer="На фотографии не выявлено нарушений строительных норм.",
                references=[],
                elapsed_ms=total_elapsed_ms,
                raw={"step1": step1_result},
            )
        
        # ===== ШАГ 2: Формирование поискового запроса =====
        # Добавляем фокус в поисковый запрос если есть
        search_context = violations_description
        if focus_hint and focus_hint.strip():
            search_context = f"Запрос: {focus_hint.strip()}\n\nНарушения:\n{violations_description}"
        
        search_query, step2_ms = self.vision.create_search_query(search_context)
        total_elapsed_ms += step2_ms
        
        # ===== ШАГ 3: Запрос к LightRAG =====
        # Формируем полный запрос с промптом для финального ответа
        full_query = f"""
Описание нарушений:
{violations_description}

Поисковый запрос для базы знаний:
{search_query}
"""
        
        lightrag_result, step3_ms = self.lightrag.query(
            question=full_query,
            mode=self.settings.default_query_mode,
            user_prompt=self.FINAL_PROMPT,
            history=[],
        )
        total_elapsed_ms += step3_ms
        
        # Извлекаем ответ и ссылки
        answer = self._extract_answer(lightrag_result)
        references = self._extract_references(lightrag_result)
        
        return AssistantAnswer(
            session_id=resolved_session_id,
            answer=answer,
            references=references,
            elapsed_ms=total_elapsed_ms,
            raw={
                "step1_violations": violations_description,
                "step2_query": search_query,
                "step3_lightrag": lightrag_result,
            },
        )
    
    def _extract_violations(self, data: dict[str, Any]) -> str:
        """
        Извлекает описание нарушений из ответа Vision модели.
        """
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            return content.strip()
        
        # Fallback: пробуем другие ключи
        for key in ("response", "answer", "result", "content"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        
        return ""
    
    def _extract_answer(self, data: dict[str, Any]) -> str:
        """
        Извлекает текст ответа из ответа LightRAG.
        """
        for key in ("response", "answer", "result", "content", "data"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "LightRAG вернул ответ в неизвестном формате."
    
    def _extract_references(self, data: dict[str, Any]) -> list[Reference]:
        """
        Извлекает нормативные ссылки из ответа LightRAG.
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
