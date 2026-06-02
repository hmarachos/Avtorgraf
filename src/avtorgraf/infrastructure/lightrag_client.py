from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from avtorgraf.config import Settings


class LightRagError(RuntimeError):
    """Ошибка при взаимодействии с LightRAG API."""
    pass


class LightRagClient:
    """
    HTTP клиент для взаимодействия с LightRAG API.
    
    Поддерживает аутентификацию через API ключ или Bearer токен.
    """
    
    def __init__(self, settings: Settings) -> None:
        """
        Инициализирует клиент с настройками подключения.
        
        Args:
            settings: Настройки приложения с параметрами LightRAG
        """
        self.settings = settings
        self.base_url = settings.lightrag_base_url.rstrip("/")

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Формирует HTTP заголовки для запросов."""
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        if self.settings.lightrag_api_key:
            headers["X-API-Key"] = self.settings.lightrag_api_key
        if self.settings.lightrag_bearer_token:
            headers["Authorization"] = f"Bearer {self.settings.lightrag_bearer_token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """
        Выполняет HTTP запрос к LightRAG API.
        
        Args:
            method: HTTP метод (GET, POST и т.д.)
            path: Путь API эндпоинта
            body: Тело запроса (для POST)
            query: Query параметры
            
        Returns:
            Кортеж (ответ в виде словаря, время выполнения в мс)
            
        Raises:
            LightRagError: При ошибке HTTP или недоступности сервера
        """
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        data = json.dumps(body or {}).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request, timeout=self.settings.lightrag_timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise LightRagError(f"LightRAG HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise LightRagError(f"LightRAG недоступен: {exc.reason}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if not raw:
            return {}, elapsed_ms
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"response": raw}
        return parsed if isinstance(parsed, dict) else {"data": parsed}, elapsed_ms

    def query(
        self,
        question: str,
        mode: str,
        user_prompt: str,
        history: list[dict[str, str]],
    ) -> tuple[dict[str, Any], int]:
        """
        Отправляет вопрос в LightRAG и получает ответ.
        
        Args:
            question: Вопрос пользователя
            mode: Режим поиска (mix, hybrid, global, local, naive)
            user_prompt: Системный промпт для формирования ответа
            history: История диалога
            
        Returns:
            Кортеж (ответ с контекстом, время выполнения в мс)
        """
        payload = {
            "query": question,
            "mode": mode,
            "top_k": 40,
            "chunk_top_k": 20,
            "max_entity_tokens": 6000,
            "max_relation_tokens": 8000,
            "max_total_tokens": 30000,
            "only_need_context": False,
            "only_need_prompt": False,
            "stream": False,
            "history_turns": min(len(history) // 2, 4),
            "conversation_history": history,
            "user_prompt": user_prompt,
            "enable_rerank": True,
        }
        return self._request("POST", "/query", payload)

    def health(self) -> dict[str, Any]:
        """Проверяет доступность LightRAG сервера."""
        try:
            data, elapsed_ms = self._request("GET", "/health")
            return {"ok": True, "elapsed_ms": elapsed_ms, "details": data}
        except LightRagError as exc:
            return {"ok": False, "error": str(exc)}

    def documents(self) -> dict[str, Any]:
        """Получает список документов из базы знаний LightRAG."""
        data, _ = self._request("GET", "/documents")
        return data

    def pipeline_status(self) -> dict[str, Any]:
        """Получает статус обработки документов в LightRAG."""
        data, _ = self._request("GET", "/documents/pipeline_status")
        return data

    def get_document_content(self, document_name: str) -> dict[str, Any]:
        """
        Получает содержимое документа из LightRAG.
        
        Args:
            document_name: Имя документа для получения
            
        Returns:
            Словарь с содержимым документа
        """
        data, _ = self._request("GET", f"/documents/{urllib.parse.quote(document_name)}")
        return data
