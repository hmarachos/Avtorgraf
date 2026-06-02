from __future__ import annotations

from avtorgraf.application.chat_service import ChatService
from avtorgraf.config import Settings
from avtorgraf.infrastructure.database import ConversationRepository
from avtorgraf.infrastructure.lightrag_client import LightRagClient
from avtorgraf.presentation.http_server import create_server


def main() -> None:
    settings = Settings.from_env()
    repository = ConversationRepository(settings.database_path)
    lightrag = LightRagClient(settings)
    chat_service = ChatService(settings, repository, lightrag)
    server = create_server(
        settings.app_host,
        settings.app_port,
        settings.static_dir,
        chat_service,
        lightrag,
    )
    print(f"Avtorgraf listening on http://{settings.app_host}:{settings.app_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
