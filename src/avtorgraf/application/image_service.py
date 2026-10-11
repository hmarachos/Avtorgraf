from __future__ import annotations

import logging
from typing import Any

from avtorgraf.config import Settings
from avtorgraf.domain.models import AssistantAnswer, Reference, new_session_id
from avtorgraf.infrastructure.lightrag_client import LightRagClient
from avtorgraf.infrastructure.vision_client import VisionClient, VisionError

# Настройка логирования
logger = logging.getLogger("avtorgraf.image_service")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("📸 [IMAGE_SERVICE] %(message)s"))
    logger.addHandler(handler)


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

[Отвечай ТОЛЬКО по теме из "Фокус запроса".
Пример: если фокус "средства защиты рабочих" - опиши только: каски, перчатки, спецодежда, страховки, ограждения опасных зон, защитные барьеры.
Если фокус "котлован/откосы" - только про них.

Если в описании нарушений ничего нет по теме фокуса - напиши: "⚠️ По теме '[фокус]' нарушений не выявлено."

Каждое утверждение с ссылкой **[Документ, п. X]**]

---

## Методы устранения

[Только для нарушений по фокусу пользователя. Кратко. С ссылками.]

---

СТРОГО:
- Отвечай ТОЛЬКО по фокусу - НЕ пиши про котлованы, откосы, складирование если фокус про средства защиты
- Используй ТОЛЬКО найденный в LightRAG контекст
- Каждое утверждение с ссылкой на пункт документа
- Отвечай кратко - не более 3-5 предложений"""
    
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
        
        logger.info("=" * 50)
        logger.info(f"🚀 НАЧАЛО АНАЛИЗА (session={resolved_session_id})")
        logger.info(f"🎯 FOCUS_HINT: {focus_hint or '(нет)'}")
        
        # ===== ШАГ 1: Анализ фотографии =====
        logger.info("⏳ ШАГ 1: Анализ изображения...")
        step1_result, step1_ms = self.vision.analyze_image(image_data, image_format, focus_hint)
        total_elapsed_ms += step1_ms
        
        logger.info(f"✅ ШАГ 1 завершен за {step1_ms}мс")
        
        # Извлекаем описание нарушений из ответа и флаг найденных нарушений
        violations_description, found_violations = self._extract_violations(step1_result)
        
        logger.info(f"📋 violations_description: {violations_description[:200]}...")
        logger.info(f"🎯 found_violations: {found_violations}")
        
        # Если нарушений не найдено
        if not violations_description or not found_violations:
            answer_text = violations_description if violations_description else "На фотографии не выявлено нарушений по запросу пользователя."
            return AssistantAnswer(
                session_id=resolved_session_id,
                answer=answer_text,
                references=[],
                elapsed_ms=total_elapsed_ms,
                raw={
                    "step1": step1_result,
                    "found_violations": found_violations,
                },
            )
        
        # ===== ШАГ 2: Формирование поискового запроса =====
        # Передаем фокус в create_search_query для более точного запроса к LightRAG
        search_query, step2_ms = self.vision.create_search_query(
            violations_description, 
            focus_hint=focus_hint if focus_hint else ""
        )
        total_elapsed_ms += step2_ms
        
        logger.info(f"✅ ШАГ 2 завершен за {step2_ms}мс")
        logger.info(f"🔍 search_query: {search_query[:200]}...")
        
        # ===== ШАГ 3: Запрос к LightRAG =====
        # Формируем полный запрос с промптом для финального ответа
        focus_context = f" (фокус пользователя: {focus_hint.strip()})" if focus_hint and focus_hint.strip() else ""
        
        logger.info("⏳ ШАГ 3: Запрос к LightRAG...")
        full_query = f"""
Фокус запроса{focus_context}

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
        
        logger.info(f"✅ ШАГ 3 завершен за {step3_ms}мс")
        logger.info(f"📝 full_query: {full_query[:300]}...")
        
        # Извлекаем ответ и ссылки
        answer = self._extract_answer(lightrag_result)
        references = self._extract_references(lightrag_result)
        
        logger.info(f"🎉 АНАЛИЗ ЗАВЕРШЕН (всего {total_elapsed_ms}мс)")
        logger.info(f"📤 ОТВЕТ:\n{answer[:300]}...")
        
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
    
    def _extract_violations(self, data: dict[str, Any]) -> tuple[str, bool]:
        """
        Извлекает описание нарушений из ответа Vision модели.
        
        Returns:
            tuple[description: str, found_violations: bool]
        """
        logger.debug(f"_extract_violations: data keys = {list(data.keys())}")
        
        content = ""
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            logger.debug(f"_extract_violations: extracted content = {content[:200]}...")
        else:
            # Fallback: пробуем другие ключи
            for key in ("response", "answer", "result", "content"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    logger.debug(f"_extract_violations: fallback key '{key}' = {value[:100]}...")
                    content = value
                    break
        
        if not content:
            logger.debug("_extract_violations: no content found")
            return "", False
        
        # Определяем, найдены ли нарушения
        found_violations = True
        
        # Проверяем маркеры
        markers = {
            "НАЙДЕНО_НАРУШЕНИЙ: НЕТ": False,
            "НАЙДЕНО_НАРУШЕНИЙ: ДА": True,
            "НЕТ_НАРУШЕНИЙ": False,
        }
        
        for marker, has_violations in markers.items():
            if marker in content:
                logger.debug(f"_extract_violations: found marker '{marker}', violations = {has_violations}")
                found_violations = has_violations
                # Убираем маркер из контента
                content = content.replace(marker, "").strip()
                break
        
        # Если маркеры не найдены, проверяем ключевые слова в тексте
        if found_violations:  # Пока True
            negative_phrases = [
                "не видно", "не видно нарушений", "нарушений не выявлено",
                "не найден", "не найдены", "отсутствует", "отсутствуют",
                "⚠️ На фотографии"
            ]
            if any(phrase in content.lower() for phrase in negative_phrases):
                found_violations = False
        
        # Убираем строку с маркером если есть (альтернативный формат)
        lines = content.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in ["НАЙДЕНО_НАРУШЕНИЙ: НЕТ", "НАЙДЕНО_НАРУШЕНИЙ: ДА"]:
                continue
            if "НАЙДЕНО_НАРУШЕНИЙ:" in stripped:
                continue
            cleaned_lines.append(line)
        
        cleaned_content = "\n".join(cleaned_lines).strip()
        
        return cleaned_content, found_violations
    
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
