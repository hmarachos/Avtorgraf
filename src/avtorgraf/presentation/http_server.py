from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from avtorgraf.application.chat_service import ChatService
from avtorgraf.infrastructure.lightrag_client import LightRagClient, LightRagError


class ApiHandler(SimpleHTTPRequestHandler):
    """
    HTTP обработчик для API эндпоинтов и статических файлов.
    
    Обрабатывает запросы к /api/* и раздает статические файлы из static_dir.
    """
    
    chat_service: ChatService
    lightrag: LightRagClient
    static_dir: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=self.static_dir, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Отключает логирование запросов в stdout."""
        return

    def do_GET(self) -> None:
        """Обработчик GET запросов."""
        if self.path == "/api/health":
            self._handle_health()
            return
        if self.path == "/api/sessions":
            self._handle_sessions()
            return
        if self.path == "/api/documents":
            self._handle_documents()
            return
        if self.path == "/api/documents/pipeline_status":
            self._handle_pipeline_status()
            return
        if self.path.startswith("/api/documents/"):
            self._handle_document_content()
            return
        super().do_GET()

    def do_POST(self) -> None:
        """Обработчик POST запросов."""
        if self.path == "/api/chat":
            self._handle_chat()
            return
        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def _handle_health(self) -> None:
        """Проверяет статус здоровья приложения."""
        try:
            self._json({"app": "ok", "lightrag": self.lightrag.health()})
        except Exception as exc:
            self._json({"app": "ok", "lightrag": {"ok": False, "error": str(exc)}}, HTTPStatus.SERVICE_UNAVAILABLE)

    def _handle_sessions(self) -> None:
        """Возвращает список сессий."""
        try:
            sessions = self.chat_service.repository.list_sessions()
            self._json({"sessions": sessions})
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_documents(self) -> None:
        """Возвращает список загруженных документов."""
        try:
            self._json(self.lightrag.documents())
        except LightRagError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_pipeline_status(self) -> None:
        """Возвращает статус обработки документов в LightRAG."""
        try:
            self._json(self.lightrag.pipeline_status())
        except LightRagError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_document_content(self) -> None:
        """Возвращает содержимое конкретного документа."""
        try:
            # Извлекаем имя документа из пути /api/documents/{document_name}
            import urllib.parse
            document_name = urllib.parse.unquote(self.path.split("/api/documents/")[1])
            self._json(self.lightrag.get_document_content(document_name))
        except LightRagError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_chat(self) -> None:
        """Обрабатывает запрос на чат с ассистентом."""
        try:
            payload = self._read_json()
            stream = payload.get("stream", False)
            
            if stream:
                self._handle_chat_stream(payload)
            else:
                self._handle_chat_regular(payload)
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except LightRagError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_chat_regular(self, payload: dict[str, Any]) -> None:
        """Обработчик обычного (non-streaming) запроса."""
        result = self.chat_service.ask(
            question=str(payload.get("question", "")),
            session_id=payload.get("session_id"),
            mode=payload.get("mode"),
        )
        self._json(self._format_response(result))

    def _handle_chat_stream(self, payload: dict[str, Any]) -> None:
        """Обработчик streaming запроса - отправляет ответ в NDJSON формате."""
        try:
            question = str(payload.get("question", ""))
            session_id = payload.get("session_id")
            mode = payload.get("mode")
            
            # Получаем результат из LightRAG
            result = self.chat_service.ask(
                question=question,
                session_id=session_id,
                mode=mode,
            )
            
            # Отправляем NDJSON streaming ответ
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Отправляем ссылки на документы в первой строке (если есть)
            if result.references:
                references_line = json.dumps({
                    "references": [
                        {
                            "title": ref.title,
                            "source": ref.source,
                            "snippet": ref.snippet,
                        }
                        for ref in result.references
                    ]
                }, ensure_ascii=False)
                self.wfile.write(f"{references_line}\n".encode("utf-8"))
                self.wfile.flush()
            
            # Отправляем метаданные
            metadata_line = json.dumps({
                "type": "metadata",
                "session_id": result.session_id,
                "elapsed_ms": result.elapsed_ms,
            }, ensure_ascii=False)
            self.wfile.write(f"{metadata_line}\n".encode("utf-8"))
            self.wfile.flush()
            
            # Отправляем ответ по предложениям
            import time
            answer = result.answer
            
            # Разбиваем по предложениям
            sentences = answer.split(". ")
            for i, sentence in enumerate(sentences):
                if not sentence.strip():
                    continue
                
                # Восстанавливаем пунктуацию
                if i < len(sentences) - 1:
                    text = sentence + ". "
                else:
                    text = sentence
                
                # Отправляем строку NDJSON
                response_line = json.dumps({
                    "response": text
                }, ensure_ascii=False)
                self.wfile.write(f"{response_line}\n".encode("utf-8"))
                self.wfile.flush()
                
                # Небольшая задержка для эффекта стриминга (50ms)
                time.sleep(0.05)
            
            # Отправляем финальный сигнал
            done_line = json.dumps({
                "type": "done"
            }, ensure_ascii=False)
            self.wfile.write(f"{done_line}\n".encode("utf-8"))
            self.wfile.flush()
            
        except Exception as exc:
            error_event = json.dumps({
                "type": "error",
                "error": str(exc),
            }, ensure_ascii=False)
            self.wfile.write(f"data: {error_event}\n\n".encode("utf-8"))
            self.wfile.flush()

    def _format_response(self, result: Any) -> dict[str, Any]:
        """Форматирует ответ ассистента для отправки клиенту."""
        return {
            "session_id": result.session_id,
            "answer": result.answer,
            "references": [
                {
                    "title": ref.title,
                    "source": ref.source,
                    "snippet": ref.snippet,
                    "metadata": ref.metadata,
                }
                for ref in result.references
            ],
            "elapsed_ms": result.elapsed_ms,
        }

    def _read_json(self) -> dict[str, Any]:
        """Читает JSON из тела запроса."""
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw)

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        """Отправляет JSON ответ клиенту."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(
    host: str,
    port: int,
    static_dir: str,
    chat_service: ChatService,
    lightrag: LightRagClient,
) -> ThreadingHTTPServer:
    """
    Создает HTTP сервер с настроенными зависимостями.
    
    Args:
        host: Адрес для прослушивания
        port: Порт сервера
        static_dir: Директория со статическими файлами
        chat_service: Сервис обработки вопросов
        lightrag: Клиент LightRAG
        
    Returns:
        Настроенный ThreadingHTTPServer
    """
    Path(static_dir).mkdir(parents=True, exist_ok=True)

    class BoundHandler(ApiHandler):
        pass

    BoundHandler.chat_service = chat_service
    BoundHandler.lightrag = lightrag
    BoundHandler.static_dir = static_dir
    return ThreadingHTTPServer((host, port), BoundHandler)
