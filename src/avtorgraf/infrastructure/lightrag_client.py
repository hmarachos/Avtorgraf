from __future__ import annotations

import json
from pathlib import Path
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
        Получает содержимое документа.
        Сначала пытается найти и прочитать файл локально.
        Если локальный файл не найден или не может быть прочитан, запрашивает фрагменты через API LightRAG.
        """
        # Сначала пробуем найти файл локально
        documents_dir = getattr(self.settings, "documents_dir", "")
        if documents_dir:
            file_path = self._find_local_file(document_name, documents_dir)
            if file_path:
                try:
                    content = self._read_local_file(file_path)
                    return {
                        "content": content,
                        "source": f"local_filesystem ({file_path.name})"
                    }
                except Exception as exc:
                    # Логируем ошибку и пробуем получить из RAG
                    pass

        # Fallback: получаем фрагменты из LightRAG через /query/data
        try:
            return self._get_content_from_rag_chunks(document_name)
        except Exception as exc:
            raise LightRagError(f"Не удалось получить содержимое документа '{document_name}': {exc}")

    def _find_local_file(self, doc_name: str, directory: str) -> Path | None:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return None
            
        doc_name_lower = doc_name.lower()
        for file in path.glob("**/*"):
            if file.is_file():
                if doc_name_lower in file.name.lower():
                    return file
        return None

    def _read_local_file(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            return self._extract_text_from_docx(file_path)
        elif suffix == ".pdf":
            return self._extract_text_from_pdf(file_path)
        elif suffix in {".txt", ".md", ".json"}:
            return file_path.read_text(encoding="utf-8", errors="replace")
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {suffix}")

    def _extract_text_from_docx(self, file_path: Path) -> str:
        import zipfile
        import xml.etree.ElementTree as ET
        
        namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read("word/document.xml")
            root = ET.fromstring(xml_content)
            for paragraph in root.iter(f"{{{namespaces['w']}}}p"):
                texts = []
                for node in paragraph.iter(f"{{{namespaces['w']}}}t"):
                    if node.text:
                        texts.append(node.text)
                if texts:
                    paragraphs.append("".join(texts))
                    
        return "\n\n".join(paragraphs)

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        try:
            import pypdf
        except ImportError as exc:
            raise RuntimeError("Библиотека pypdf не установлена") from exc
            
        reader = pypdf.PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)

    def _get_content_from_rag_chunks(self, document_name: str) -> dict[str, Any]:
        payload = {
            "query": document_name,
            "mode": "naive",
            "chunk_top_k": 300,
        }
        
        data, _ = self._request("POST", "/query/data", payload)
        retrieved_data = data.get("data", {})
        chunks = retrieved_data.get("chunks", [])
        
        doc_name_lower = document_name.lower()
        matched_contents = []
        seen_contents = set()
        
        for chunk in chunks:
            file_path = chunk.get("file_path", "")
            content = chunk.get("content", "")
            
            if file_path and doc_name_lower in file_path.lower():
                if content and content not in seen_contents:
                    seen_contents.add(content)
                    matched_contents.append(content)
                    
        if not matched_contents:
            for chunk in chunks:
                content = chunk.get("content", "")
                if content and content not in seen_contents:
                    seen_contents.add(content)
                    matched_contents.append(content)
                    
        if not matched_contents:
            return {"content": "Документ не найден в RAG и локальной файловой системе."}
            
        content_text = "\n\n---\n\n".join(matched_contents)
        return {"content": content_text, "source": "rag_knowledge_graph"}
