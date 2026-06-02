from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from avtorgraf.application.chat_service import ChatService
from avtorgraf.infrastructure.lightrag_client import LightRagClient, LightRagError


class ApiHandler(SimpleHTTPRequestHandler):
    chat_service: ChatService
    lightrag: LightRagClient
    static_dir: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=self.static_dir, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._json({"app": "ok", "lightrag": self.lightrag.health()})
            return
        if self.path == "/api/sessions":
            self._json({"sessions": self.chat_service.repository.list_sessions()})
            return
        if self.path == "/api/documents":
            try:
                self._json(self.lightrag.documents())
            except LightRagError as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return
        if self.path == "/api/documents/pipeline_status":
            try:
                self._json(self.lightrag.pipeline_status())
            except LightRagError as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/chat":
            self._handle_chat()
            return
        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def _handle_chat(self) -> None:
        try:
            payload = self._read_json()
            result = self.chat_service.ask(
                question=str(payload.get("question", "")),
                session_id=payload.get("session_id"),
                mode=payload.get("mode"),
            )
            self._json(
                {
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
            )
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except LightRagError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw)

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
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
    Path(static_dir).mkdir(parents=True, exist_ok=True)

    class BoundHandler(ApiHandler):
        pass

    BoundHandler.chat_service = chat_service
    BoundHandler.lightrag = lightrag
    BoundHandler.static_dir = static_dir
    return ThreadingHTTPServer((host, port), BoundHandler)
