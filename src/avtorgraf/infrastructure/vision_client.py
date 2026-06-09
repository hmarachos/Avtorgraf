from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any

from avtorgraf.config import Settings


class VisionError(RuntimeError):
    """Ошибка при анализе изображения."""
    pass


class VisionClient:
    """
    Клиент для анализа изображений через OpenRouter API.
    
    Поддерживает multimodal модели (Gemini, GPT-4 Vision, Claude и др.)
    """
    
    ANALYSIS_PROMPT = """## КРИТИЧЕСКИ ВАЖНО: СПЕЦИАЛЬНЫЙ ЗАПРОС ПОЛЬЗОВАТЕЛЯ

Пользователь просит проанализировать фото со специфическим фокусом:
**{focus_query}**

ТВОЯ ПЕРВООЧЕРЕДНАЯ ЗАДАЧА:
1. ВНИМАТЕЛЬНО ИЗУЧИ фотографию на предмет элементов, связанных с запросом
2. ЕСЛИ на фото виден котлован, его откосы, стенки - ОПИШИ ИХ В ПЕРВУЮ ОЧЕРЕДЬ:
   - Угол заложения откосов котлована (визуальная оценка: крутой/пологий)
   - Тип грунта на откосах (песок, глина, суглинок - если виден)
   - Наличие/отсутствие крепления стенок котлована
   - Признаки обрушения грунта на откосах
   - Состояние бровки котлована
   - Расстояние от бровки котлована до складируемых материалов/техники
   - Наличие ограждений по периметру котлована
   - Организация водоотлива из котлована
3. ЕСЛИ запрошенных элементов НЕТ на фото - НАЧНИ ОТВЕТ со слов: "⚠️ На предоставленной фотографии не видно [запрошенных элементов]"
4. ТОЛЬКО ПОСЛЕ анализа запрошенного можешь упомянуть другие нарушения

---

Ты — специалист по авторскому надзору в строительстве в Республике Беларусь.

Найди следующие категории нарушений (ЕСЛИ они видны):

**Земляные работы и котлованы:**
- Угол откосов не соответствует типу грунта
- Отсутствие крепления стенок котлована при глубине более 1.25 м
- Складирование грунта/материалов ближе 0.5 м от бровки котлована
- Отсутствие ограждения котлована
- Признаки обрушения откосов

**Технология производства работ:**
- Неправильное выполнение процессов
- Отступления от проекта

**Требования безопасности:**
- Отсутствие средств защиты
- Опасные зоны без ограждений
- Работы на высоте без страховки

**Дефекты конструкций:**
- Трещины, сколы в бетоне
- Коррозия арматуры

**Складирование материалов:**
- Неправильное хранение
- Отсутствие поддонов

---

ФОРМАТ ОТВЕТА:

### АНАЛИЗ ПО ЗАПРОСУ: {focus_query}

[Здесь детально опиши то, что просил пользователь. Если на фото это не видно - так и напиши]

---

### ДОПОЛНИТЕЛЬНЫЕ НАРУШЕНИЯ (если есть)

### Нарушение №[номер]: [название]
**Категория:** [земляные работы/технология/безопасность/дефект/складирование]
**Описание:** [что видно]
**Местоположение:** [где на фото]
**Критичность:** [критическое/значительное/незначительное]
"""

    REFORMAT_PROMPT = """На основе описания нарушений создай краткий поисковый запрос для базы знаний нормативных документов Республики Беларусь.

ВАЖНО:
- Если в описании упоминаются КОТЛОВАН, ОТКОСЫ, ТРАНШЕИ - включи эти термины в запрос В ПЕРВУЮ ОЧЕРЕДЬ
- Для земляных работ используй термины: "котлован", "откосы", "крепление стенок", "угол заложения", "земляные работы"
- Запрос должен быть конкретным и специфичным

Формат: только текст запроса, без объяснений. Не более 2-3 предложений.

ПРИМЕРЫ:
- Если про котлован: "требования к углу заложения откосов котлована, крепление стенок котлована, расстояние от бровки до складирования материалов"
- Если про бетон: "требования к бетонным работам, дефекты бетона, контроль качества бетонирования"
"""
    
    def __init__(self, settings: Settings) -> None:
        """
        Инициализирует клиент с настройками.
        
        Args:
            settings: Настройки приложения с параметрами OpenRouter
        """
        self.settings = settings
        self.base_url = settings.openrouter_base_url.rstrip("/")
        
    def _headers(self) -> dict[str, str]:
        """Формирует HTTP заголовки для запросов."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "HTTP-Referer": "https://avtorgraf.local",
            "X-Title": "Avtorgraf Vision Analysis",
            # Настройки для обхода ограничений guardrails
            "X-Disable-Data-Collection": "true",
        }
    
    def analyze_image(self, image_data: bytes, image_format: str = "jpeg", focus_hint: str = "") -> tuple[dict[str, Any], int]:
        """
        Анализирует изображение и возвращает описание нарушений (ШАГ 1).
        
        Args:
            image_data: Бинарные данные изображения
            image_format: Формат изображения (jpeg, png, webp)
            focus_hint: Текстовый запрос пользователя для фокусировки внимания
            
        Returns:
            Кортеж (результат анализа, время выполнения в мс)
            
        Raises:
            VisionError: При ошибке анализа
        """
        # Кодируем изображение в base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        mime_type = f"image/{image_format}"
        
        # Формируем промпт с учетом фокуса пользователя
        if focus_hint and focus_hint.strip():
            # УЛЬТРА-КОРОТКИЙ промпт для фокусированного анализа
            analysis_prompt = f"""ВОПРОС: {focus_hint.strip()}

Изучи фотографию и ответь на этот вопрос. 

Если на фото есть котлован - опиши:
- Угол откосов
- Тип грунта
- Крепление стенок
- Расстояние от бровки до материалов
- Признаки обрушения

Если запрошенного объекта НЕТ на фото - сразу напиши об этом.

Формат: сначала ответ на вопрос, потом другие нарушения."""
        else:
            # Общий промпт для анализа всего
            focus_query = "общий анализ всех нарушений"
            analysis_prompt = self.ANALYSIS_PROMPT.format(focus_query=focus_query)
        
        payload = {
            "model": self.settings.vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты опытный инженер-строитель и специалист по авторскому надзору в Республике Беларусь. Ты анализируешь фотографии строительных площадок и выявляешь нарушения. Ты ВСЕГДА отвечаешь ТОЧНО на заданный вопрос.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": analysis_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                            },
                        },
                    ],
                },
            ],
            "max_tokens": 4000,
            "temperature": 0.2,  # Очень низкая температура для точного следования инструкциям
            # Параметры для обхода ограничений
            "provider": {
                "allow_fallbacks": True,
            },
        }
        
        return self._request(payload)
    
    def create_search_query(self, violations_description: str) -> tuple[str, int]:
        """
        Создает поисковый запрос для LightRAG на основе описания нарушений (ШАГ 2).
        
        Args:
            violations_description: Описание выявленных нарушений
            
        Returns:
            Кортеж (поисковый запрос, время выполнения в мс)
        """
        payload = {
            "model": self.settings.vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": self.REFORMAT_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"Описание нарушений:\n\n{violations_description}",
                },
            ],
            "max_tokens": 200,
            "temperature": 0.5,
        }
        
        data, elapsed_ms = self._request(payload)
        
        # Извлекаем текст ответа
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            return content.strip(), elapsed_ms
        
        return violations_description[:500], elapsed_ms
    
    def _request(self, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """
        Выполняет HTTP запрос к OpenRouter API.
        
        Args:
            payload: Тело запроса
            
        Returns:
            Кортеж (ответ в виде словаря, время выполнения в мс)
            
        Raises:
            VisionError: При ошибке HTTP или недоступности сервера
        """
        url = f"{self.base_url}/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(),
            method="POST",
        )
        
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise VisionError(f"OpenRouter HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise VisionError(f"OpenRouter недоступен: {exc.reason}") from exc
        
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        
        if not raw:
            return {}, elapsed_ms
        
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}, elapsed_ms
        
        return parsed if isinstance(parsed, dict) else {"data": parsed}, elapsed_ms
