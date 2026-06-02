from __future__ import annotations

from avtorgraf.application.chat_service import ChatService
from avtorgraf.config import Settings
from avtorgraf.infrastructure.database import ConversationRepository
from avtorgraf.infrastructure.lightrag_client import LightRagClient
from avtorgraf.presentation.http_server import create_server


def main() -> None:
    """
    Точка входа приложения АВТОГРАФ.
    
    Инициализирует все компоненты и запускает HTTP сервер.
    """
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
    print(f"🚀 Avtorgraf запущен на http://{settings.app_host}:{settings.app_port}")
    print(f"📊 База данных: {settings.database_path}")
    print(f"🔗 LightRAG: {settings.lightrag_base_url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
