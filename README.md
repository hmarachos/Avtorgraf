# 🏗️ АВТОГРАФ

> **Интеллектуальный помощник проектировщика, авторского и технического надзора в строительстве**

АВТОГРАФ — это веб-приложение на базе LightRAG для специалистов строительной отрасли Республики Беларусь. Система предоставляет быстрый доступ к нормативно-технической документации через чат-интерфейс с поддержкой контекста диалога.

## 🎯 Возможности

- 💬 **Интеллектуальный чат** — задавайте вопросы по нормативам РБ и получайте ответы с точными ссылками на документы
- 📚 **База знаний LightRAG** — использует граф знаний для поиска релевантной информации в СН, СТБ, инструкциях
- 🔄 **История диалогов** — сохранение сессий для продолжения разговора в любой момент
- 🎭 **Роли пользователей** — ГИП, Авторский надзор, Технический надзор
- 📱 **Адаптивный интерфейс** — работает на всех устройствах
- 🔍 **5 режимов поиска** — mix, hybrid, global, local, naive для разных типов запросов

## 🏛️ Архитектура

Проект построен на принципах Clean Architecture и Domain-Driven Design:

```
src/avtorgraf/
├── domain/              # Доменные модели (ChatMessage, Reference, AssistantAnswer)
├── application/         # Бизнес-логика (ChatService)
├── infrastructure/      # Внешние зависимости (SQLite, LightRAG API)
└── presentation/        # HTTP API и веб-интерфейс
```

### Технологический стек

- **Backend:** Python 3.12+, стандартная библиотека (http.server, sqlite3, urllib)
- **Frontend:** Vanilla JavaScript, HTML5, CSS3
- **База данных:** SQLite (хранение сессий и истории)
- **AI Backend:** LightRAG (граф знаний + RAG)
- **Развертывание:** Docker, docker-compose

### Компоненты

#### Domain (Доменный слой)

- `models.py` — неизменяемые модели данных:
  - `ChatMessage` — сообщение в диалоге
  - `Reference` — нормативная ссылка из базы знаний
  - `AssistantAnswer` — ответ ассистента с метаданными

#### Application (Бизнес-логика)

- `chat_service.py` — сервис обработки вопросов:
  - Управление сессиями
  - Формирование контекста из истории
  - Извлечение ответов и ссылок из LightRAG
  - Валидация входных данных

#### Infrastructure (Инфраструктура)

- `database.py` — репозиторий для SQLite:
  - Создание и управление сессиями
  - Сохранение истории сообщений
  - Получение последних N сообщений для контекста
  
- `lightrag_client.py` — HTTP клиент LightRAG:
  - Аутентификация через API Key или Bearer Token
  - Обработка таймаутов и ошибок
  - Запросы к API (/query, /health, /documents)

#### Presentation (Представление)

- `http_server.py` — HTTP сервер с API:
  - `POST /api/chat` — отправка вопроса
  - `GET /api/health` — проверка доступности
  - `GET /api/sessions` — список сессий
  - `GET /api/documents` — документы в LightRAG
  - `GET /api/documents/pipeline_status` — статус обработки
  - Раздача статических файлов

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.12 или выше
- Docker и docker-compose (для контейнерного запуска)
- Доступ к LightRAG серверу

### Вариант 1: Локальный запуск

1. **Клонируйте репозиторий:**

```bash
git clone https://github.com/your-username/avtorgraf.git
cd avtorgraf
```

2. **Создайте файл конфигурации:**

```bash
cp .env.example .env
```

3. **Настройте переменные окружения в `.env`:**

```env
# Сервер приложения
APP_HOST=0.0.0.0
APP_PORT=8080

# База данных
DATABASE_PATH=data/avtorgraf.sqlite3

# Статические файлы
STATIC_DIR=static

# LightRAG конфигурация
LIGHTRAG_BASE_URL=http://46.17.105.48:9621
LIGHTRAG_API_KEY=your-api-key-here
LIGHTRAG_BEARER_TOKEN=
LIGHTRAG_TIMEOUT_SECONDS=35

# Режим поиска по умолчанию (mix, hybrid, global, local, naive)
DEFAULT_QUERY_MODE=mix

# Системный промпт для LightRAG
SYSTEM_PROMPT=Отвечай как помощник проектировщика, авторского и технического надзора в Республике Беларусь. Используй только найденный в LightRAG контекст. Если в базе нет подтверждения, прямо скажи, что нормативное основание не найдено. Обязательно указывай пункты СН, СТБ, инструкций или кодексов РБ, когда они присутствуют в контексте. Не подменяй нормы РБ нормами РФ.
```

4. **Запустите приложение:**

```bash
PYTHONPATH=src python -m avtorgraf.main
```

5. **Откройте браузер:**

```
http://localhost:8080
```

### Вариант 2: Docker Compose (рекомендуется)

1. **Настройте `.env` файл** (как в варианте 1)

2. **Запустите контейнер:**

```bash
docker compose up --build
```

3. **Приложение доступно:**

```
http://localhost:8080
```

База данных автоматически сохраняется в Docker volume `avtorgraf-data`.

### Остановка приложения

**Локальный запуск:**
```bash
Ctrl+C
```

**Docker Compose:**
```bash
docker compose down
```

Для удаления данных:
```bash
docker compose down -v
```

## 📖 Использование

### Веб-интерфейс

1. **Выберите роль** — ГИП, Авторский надзор или Технический надзор
2. **Выберите режим поиска:**
   - `mix` — комбинированный (рекомендуется)
   - `hybrid` — гибридный поиск
   - `global` — глобальный граф знаний
   - `local` — локальный поиск
   - `naive` — базовый поиск
3. **Задайте вопрос** или используйте быстрые шаблоны
4. **Получите ответ** с нормативными ссылками

### Примеры вопросов

- "Подрядчик просит согласовать отечественный аналог оборудования. Какая процедура согласования замены материалов и какие документы нужны?"
- "Строители залили бетон с дефектами и требуют подписать акт освидетельствования скрытых работ. Как корректно отказать и что записать в журнал авторского надзора?"
- "Что проверит инспектор Госстройнадзора на объекте и какие документы должны быть на строительной площадке?"
- "Составь черновик записи в журнал авторского надзора по выявленному отступлению от проектной документации."

### HTTP API

#### POST /api/chat

Отправка вопроса в LightRAG.

**Запрос:**
```json
{
  "question": "Можно ли подписывать Акт при выявленных дефектах бетона?",
  "session_id": "abc123",
  "mode": "mix"
}
```

**Ответ:**
```json
{
  "session_id": "abc123",
  "answer": "Согласно СН 1.03.01-2019...",
  "references": [
    {
      "title": "СН 1.03.01-2019",
      "source": "documents/sn_1_03_01_2019.pdf",
      "snippet": "Акт освидетельствования...",
      "metadata": {}
    }
  ],
  "elapsed_ms": 2450
}
```

#### GET /api/health

Проверка доступности приложения и LightRAG.

**Ответ:**
```json
{
  "app": "ok",
  "lightrag": {
    "ok": true,
    "elapsed_ms": 120,
    "details": {}
  }
}
```

#### GET /api/sessions

Список последних сессий.

**Ответ:**
```json
{
  "sessions": [
    {
      "id": "abc123",
      "title": "Можно ли подписывать акт при выявленных дефектах бетона?",
      "created_at": "2026-06-02T10:30:00+00:00",
      "updated_at": "2026-06-02T11:15:00+00:00"
    }
  ]
}
```

#### GET /api/documents

Список документов в базе знаний LightRAG.

**Ответ:**
```json
{
  "documents": [
    {"id": "doc1", "name": "СН 1.03.01-2019.pdf", "status": "processed"},
    {"id": "doc2", "name": "СТБ 1937-2022.pdf", "status": "processed"}
  ]
}
```

#### GET /api/documents/pipeline_status

Статус обработки документов.

**Ответ:**
```json
{
  "pipeline": "idle",
  "processed": 125,
  "pending": 0,
  "errors": 0
}
```

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `APP_HOST` | Адрес для прослушивания | `0.0.0.0` |
| `APP_PORT` | Порт HTTP сервера | `8080` |
| `DATABASE_PATH` | Путь к SQLite базе | `data/avtorgraf.sqlite3` |
| `STATIC_DIR` | Директория статических файлов | `static` |
| `LIGHTRAG_BASE_URL` | URL сервера LightRAG | `http://46.17.105.48:9621` |
| `LIGHTRAG_API_KEY` | API ключ для аутентификации | `` |
| `LIGHTRAG_BEARER_TOKEN` | Bearer токен (альтернатива API Key) | `` |
| `LIGHTRAG_TIMEOUT_SECONDS` | Таймаут запросов к LightRAG | `35` |
| `DEFAULT_QUERY_MODE` | Режим поиска по умолчанию | `mix` |
| `SYSTEM_PROMPT` | Системный промпт для формирования ответов | См. `.env.example` |

### Режимы поиска LightRAG

- **mix** — оптимальный баланс между скоростью и качеством
- **hybrid** — комбинирует векторный и графовый поиск
- **global** — поиск по всему графу знаний (медленнее, но точнее)
- **local** — локальный контекст вокруг найденных сущностей
- **naive** — базовый векторный поиск

### Системный промпт

Вы можете настроить поведение ассистента через переменную `SYSTEM_PROMPT`. Текущий промпт настроен на:
- Использование только базы знаний LightRAG
- Приоритет норм Республики Беларусь
- Обязательное указание пунктов нормативов
- Честное признание отсутствия информации

## 🗄️ База данных

АВТОГРАФ использует SQLite для хранения сессий и истории диалогов.

### Схема

**Таблица `sessions`:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | TEXT | Уникальный идентификатор сессии (PRIMARY KEY) |
| title | TEXT | Заголовок сессии (первый вопрос, обрезанный до 80 символов) |
| created_at | TEXT | Дата создания (ISO 8601 UTC) |

**Таблица `messages`:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Автоинкремент (PRIMARY KEY) |
| session_id | TEXT | Ссылка на сессию (FOREIGN KEY) |
| role | TEXT | Роль отправителя (`user` или `assistant`) |
| content | TEXT | Содержимое сообщения |
| created_at | TEXT | Время отправки (ISO 8601 UTC) |

### Резервное копирование

**Локальный запуск:**
```bash
cp data/avtorgraf.sqlite3 data/avtorgraf-backup-$(date +%Y%m%d).sqlite3
```

**Docker:**
```bash
docker compose exec avtorgraf cp /app/data/avtorgraf.sqlite3 /app/data/avtorgraf-backup-$(date +%Y%m%d).sqlite3
```

Или скопируйте файл из volume:
```bash
docker run --rm -v avtorgraf-data:/data -v $(pwd):/backup alpine cp /data/avtorgraf.sqlite3 /backup/avtorgraf-backup.sqlite3
```

## 🛠️ Разработка

### Структура проекта

```
Avtorgraf/
├── src/
│   └── avtorgraf/
│       ├── domain/              # Доменные модели
│       │   └── models.py
│       ├── application/         # Бизнес-логика
│       │   └── chat_service.py
│       ├── infrastructure/      # Внешние зависимости
│       │   ├── database.py
│       │   └── lightrag_client.py
│       ├── presentation/        # HTTP API
│       │   └── http_server.py
│       ├── config.py            # Конфигурация
│       └── main.py              # Точка входа
├── static/                      # Фронтенд
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── data/                        # База данных SQLite
├── .env.example                 # Пример конфигурации
├── docker-compose.yml           # Docker Compose конфигурация
├── Dockerfile                   # Docker образ
├── LICENSE                      # Лицензия
└── README.md                    # Документация
```

### Запуск в режиме разработки

```bash
# Установите Python 3.12+
python --version

# Запустите приложение с автоматической перезагрузкой (используйте watchdog или nodemon)
PYTHONPATH=src python -m avtorgraf.main
```

### Линтинг и форматирование

```bash
# Установите инструменты разработки
pip install ruff mypy black isort

# Форматирование кода
black src/
isort src/

# Проверка типов
mypy src/

# Линтинг
ruff check src/
```

### Тестирование API

```bash
# Health check
curl http://localhost:8080/api/health

# Отправка вопроса
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Какие документы нужны для подписания Акта освидетельствования  скрытых работ?",
    "mode": "mix"
  }'

# Список сессий
curl http://localhost:8080/api/sessions

# Документы LightRAG
curl http://localhost:8080/api/documents
```

### Подключение к другому LightRAG серверу

Измените в `.env`:
```env
LIGHTRAG_BASE_URL=http://your-lightrag-server:9621
LIGHTRAG_API_KEY=your-api-key
```

## 🐳 Docker

### Сборка образа

```bash
docker build -t avtorgraf:latest .
```

### Запуск контейнера

```bash
docker run -d \
  --name avtorgraf \
  -p 8080:8080 \
  -v avtorgraf-data:/app/data \
  --env-file .env \
  avtorgraf:latest
```

### Просмотр логов

```bash
docker compose logs -f
```

### Вход в контейнер

```bash
docker compose exec avtorgraf sh
```

## 🔒 Безопасность

- ✅ Используйте сильные API ключи для LightRAG
- ✅ Не коммитьте `.env` файл в репозиторий
- ✅ Используйте HTTPS в продакшене
- ✅ Ограничьте доступ к SQLite файлу
- ✅ Регулярно обновляйте зависимости
- ✅ Настройте rate limiting на уровне reverse proxy

### Пример конфигурации Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name avtorgraf.example.com;

    ssl_certificate /etc/letsencrypt/live/avtorgraf.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/avtorgraf.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    location /api/chat {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8080;
    }
}
```

## 📊 Мониторинг

### Проверка здоровья приложения

```bash
# Bash
watch -n 5 'curl -s http://localhost:8080/api/health | jq'

# Python
python -c "import urllib.request, json; print(json.loads(urllib.request.urlopen('http://localhost:8080/api/health').read()))"
```

### Метрики для отслеживания

- Время ответа LightRAG (`elapsed_ms` в ответах)
- Количество сессий в базе
- Размер SQLite файла
- Доступность LightRAG (`/api/health`)

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие АВТОГРАФ! 

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменений (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

## 👥 Авторы

- Команда разработки АВТОГРАФ

## 🙏 Благодарности

- [LightRAG](https://github.com/HKUDS/LightRAG) — фреймворк для построения графа знаний
- Сообщество специалистов строительного надзора РБ
- Авторы нормативно-технической документации Республики Беларусь

## 📞 Поддержка

- 📧 Email: support@example.com
- 💬 Telegram: @avtorgraf_support
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/avtorgraf/issues)

## 🗺️ Дорожная карта

- [ ] Экспорт диалогов в PDF/DOCX
- [ ] Поддержка мультимодальности (изображения чертежей)
- [ ] Интеграция с системами документооборота
- [ ] Мобильное приложение (iOS/Android)
- [ ] Голосовой ввод вопросов
- [ ] Умные уведомления об изменениях в нормативах
- [ ] Коллаборативные сессии (несколько пользователей в одном чате)
- [ ] API для интеграции с внешними системами

---

<div align="center">

**Сделано с ❤️ для специалистов строительной отрасли Республики Беларусь**

[⬆ Вернуться к началу](#-автограф)

</div>
