from __future__ import annotations

from avtorgraf.application.chat_service import ChatService
from avtorgraf.application.image_service import ImageAnalysisService
from avtorgraf.config import Settings
from avtorgraf.infrastructure.database import ConversationRepository
from avtorgraf.infrastructure.lightrag_client import LightRagClient
from avtorgraf.infrastructure.vision_client import VisionClient
from avtorgraf.presentation.http_server import create_server


def main() -> None:
    """
    Точка входа приложения АВТОГРАФ.
    
    Инициализирует все компоненты и запускает HTTP сервер.
    """
    settings = Settings.from_env()
    repository = ConversationRepository(settings.database_path)
    lightrag = LightRagClient(settings)
    vision = VisionClient(settings)
    
    chat_service = ChatService(settings, repository, lightrag)
    image_service = ImageAnalysisService(settings, lightrag, vision)
    
    server = create_server(
        settings.app_host,
        settings.app_port,
        settings.static_dir,
        chat_service,
        image_service,
        lightrag,
    )
    print(f"🚀 Avtorgraf запущен на http://{settings.app_host}:{settings.app_port}")
    print(f"📊 База данных: {settings.database_path}")
    print(f"🔗 LightRAG: {settings.lightrag_base_url}")
    print(f"👁️ Vision модель: {settings.vision_model}")
    server.serve_forever()


if __name__ == "__main__":
    main()
