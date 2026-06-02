# АВТОГРАФ

MVP Web UI для помощи проектировщику, авторскому и техническому надзору на стройке. Приложение проксирует вопросы в LightRAG, хранит историю сессий в SQLite и показывает ответы с нормативными источниками.

## Архитектура

- `domain` — модели диалога и источников.
- `application` — сценарий вопрос-ответ.
- `infrastructure` — SQLite и LightRAG API client.
- `presentation` — HTTP API и статический адаптивный сайт.

## Настройка

Все чувствительные параметры лежат в `.env`:

- `LIGHTRAG_BASE_URL` — адрес сервера LightRAG.
- `LIGHTRAG_API_KEY` — API key, если включен.
- `LIGHTRAG_BEARER_TOKEN` — bearer token, если используется авторизация.
- `SYSTEM_PROMPT` — строгие правила ответа по НПА РБ.

## Локальный запуск

```bash
PYTHONPATH=src python -m avtorgraf.main
```

Сайт будет доступен на `http://localhost:8080`.

## Docker Compose

```bash
docker compose up --build
```

SQLite хранится в docker volume `avtorgraf-data`.

## API

- `POST /api/chat` — вопрос в LightRAG.
- `GET /api/health` — статус приложения и LightRAG.
- `GET /api/documents` — список документов LightRAG.
- `GET /api/documents/pipeline_status` — статус обработки документов.
