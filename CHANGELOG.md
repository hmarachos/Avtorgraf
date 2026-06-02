# Changelog

Все значимые изменения в проекте АВТОГРАФ будут документированы в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Планируется
- Экспорт диалогов в PDF/DOCX
- Поддержка изображений чертежей
- Мобильное приложение
- Голосовой ввод

## [1.0.0] - 2026-06-02

### Добавлено
- ✨ Базовая функциональность чата с LightRAG
- 🎭 Выбор роли пользователя (ГИП, АН, ТН)
- 🔍 5 режимов поиска (mix, hybrid, global, local, naive)
- 💾 Сохранение истории диалогов в SQLite
- 📱 Адаптивный веб-интерфейс
- 🐳 Docker и docker-compose поддержка
- 📚 Полная документация
- 🔒 Поддержка аутентификации LightRAG (API Key, Bearer Token)
- 🎯 Быстрые шаблоны вопросов
- 🏥 Health check эндпоинт
- 📊 API для получения статуса документов

### Технические детали
- Clean Architecture с разделением на domain/application/infrastructure/presentation
- Python 3.12+ со стандартной библиотекой (без внешних зависимостей)
- Vanilla JavaScript для фронтенда
- ThreadingHTTPServer для обработки параллельных запросов
- SQLite для хранения сессий и сообщений

### Инфраструктура
- Dockerfile для контейнеризации
- docker-compose.yml для удобного развертывания
- GitHub Actions для линтинга
- Makefile для частых команд
- pyproject.toml для конфигурации инструментов

### Документация
- 📖 Подробный README.md с примерами
- 🤝 CONTRIBUTING.md для контрибьюторов
- 📝 CHANGELOG.md для отслеживания изменений
- ⚙️ .env.example с описанием переменных

[Unreleased]: https://github.com/your-username/avtorgraf/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-username/avtorgraf/releases/tag/v1.0.0
