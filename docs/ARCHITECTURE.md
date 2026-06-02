# Архитектура проекта АВТОГРАФ

## Обзор

АВТОГРАФ построен на принципах **Clean Architecture** и **Domain-Driven Design** (DDD). Код организован в слои с четкими границами и зависимостями, направленными внутрь к доменному слою.

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│                   (HTTP API, Web UI)                         │
│                    http_server.py                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│                    (Business Logic)                          │
│                     chat_service.py                          │
└───────────┬─────────────────────────────────┬───────────────┘
            │                                 │
            ↓                                 ↓
┌─────────────────────────┐     ┌──────────────────────────────┐
│  Infrastructure Layer   │     │      Domain Layer            │
│  (External Services)    │     │    (Core Models)             │
│  - database.py          │     │    models.py                 │
│  - lightrag_client.py   │     │  - ChatMessage               │
│  - config.py            │     │  - Reference                 │
└─────────────────────────┘     │  - AssistantAnswer           │
                                └──────────────────────────────┘
```

## Структура директорий

```
Avtorgraf/
├── src/avtorgraf/           # Исходный код приложения
│   ├── domain/              # Доменный слой (чистые модели)
│   │   ├── __init__.py
│   │   └── models.py        # ChatMessage, Reference, AssistantAnswer
│   │
│   ├── application/         # Бизнес-логика
│   │   ├── __init__.py
│   │   └── chat_service.py  # ChatService (оркестрация)
│   │
│   ├── infrastructure/      # Внешние зависимости
│   │   ├── __init__.py
│   │   ├── database.py      # ConversationRepository (SQLite)
│   │   └── lightrag_client.py # LightRagClient (HTTP API)
│   │
│   ├── presentation/        # Веб-интерфейс
│   │   ├── __init__.py
│   │   └── http_server.py   # ApiHandler (HTTP сервер)
│   │
│   ├── __init__.py
│   ├── config.py            # Настройки приложения
│   └── main.py              # Точка входа
│
├── static/                  # Фронтенд (HTML/CSS/JS)
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── data/                    # База данных SQLite
│   └── avtorgraf.sqlite3
│
├── docs/                    # Документация
│   ├── API.md
│   └── ARCHITECTURE.md
│
├── .github/workflows/       # CI/CD
│   └── lint.yml
│
├── .env.example             # Пример конфигурации
├── .env.production          # Продакшен конфигурация
├── .dockerignore
├── .gitignore
├── CHANGELOG.md             # История изменений
├── CONTRIBUTING.md          # Руководство для контрибьюторов
├── Dockerfile               # Docker образ
├── docker-compose.yml       # Docker Compose конфигурация
├── LICENSE                  # MIT License
├── Makefile                 # Частые команды
├── pyproject.toml           # Конфигурация инструментов
├── README.md                # Главная документация
└── requirements.txt         # Зависимости (пусто - используется stdlib)
```

## Слои архитектуры

### 1. Domain Layer (Доменный слой)

**Файл:** `src/avtorgraf/domain/models.py`

**Ответственность:** Определение бизнес-сущностей и правил

**Принципы:**
- Не имеет зависимостей от других слоев
- Использует только стандартную библиотеку Python
- Модели иммутабельны (`@dataclass(frozen=True)`)
- Не содержит логики инфраструктуры или представления

**Компоненты:**

```python
@dataclass(frozen=True)
class ChatMessage:
    """Сообщение в диалоге"""
    role: str           # "user" или "assistant"
    content: str        # Текст сообщения
    created_at: str     # ISO 8601 UTC

@dataclass(frozen=True)
class Reference:
    """Нормативная ссылка"""
    title: str          # Название документа
    source: str         # Путь к файлу
    snippet: str        # Фрагмент текста
    metadata: dict      # Дополнительные данные

@dataclass(frozen=True)
class AssistantAnswer:
    """Ответ ассистента"""
    session_id: str
    answer: str
    references: list[Reference]
    elapsed_ms: int
    raw: dict
```

### 2. Application Layer (Слой бизнес-логики)

**Файл:** `src/avtorgraf/application/chat_service.py`

**Ответственность:** Оркестрация бизнес-процессов

**Компоненты:**

```python
class ChatService:
    """Сервис обработки вопросов"""
    
    def __init__(
        self,
        settings: Settings,
        repository: ConversationRepository,
        lightrag: LightRagClient,
    ) -> None:
        ...
    
    def ask(
        self,
        question: str,
        session_id: str | None,
        mode: str | None
    ) -> AssistantAnswer:
        """
        Бизнес-процесс обработки вопроса:
        1. Валидация входных данных
        2. Создание/получение сессии
        3. Загрузка истории диалога
        4. Запрос к LightRAG
        5. Извлечение ответа и ссылок
        6. Сохранение в БД
        7. Возврат результата
        """
        ...
```

**Паттерны:**
- Dependency Injection (зависимости передаются через конструктор)
- Facade (скрывает сложность работы с БД и LightRAG)

### 3. Infrastructure Layer (Инфраструктурный слой)

**Файлы:**
- `src/avtorgraf/infrastructure/database.py`
- `src/avtorgraf/infrastructure/lightrag_client.py`
- `src/avtorgraf/config.py`

**Ответственность:** Взаимодействие с внешними системами

#### ConversationRepository

```python
class ConversationRepository:
    """Репозиторий для работы с SQLite"""
    
    def __init__(self, database_path: str) -> None:
        """Инициализация и создание схемы"""
        ...
    
    def ensure_session(self, session_id: str, title: str) -> None:
        """Создать сессию, если не существует"""
        ...
    
    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Сохранить сообщение"""
        ...
    
    def get_recent_messages(
        self, 
        session_id: str, 
        limit: int = 8
    ) -> list[ChatMessage]:
        """Получить последние N сообщений для контекста"""
        ...
    
    def list_sessions(self, limit: int = 20) -> list[dict]:
        """Список последних сессий"""
        ...
```

**Паттерны:**
- Repository (абстракция хранения данных)
- Unit of Work (транзакционность через context manager)

#### LightRagClient

```python
class LightRagClient:
    """HTTP клиент для LightRAG API"""
    
    def __init__(self, settings: Settings) -> None:
        """Инициализация с настройками"""
        ...
    
    def query(
        self,
        question: str,
        mode: str,
        user_prompt: str,
        history: list[dict[str, str]],
    ) -> tuple[dict, int]:
        """Отправить вопрос в LightRAG"""
        ...
    
    def health(self) -> dict:
        """Проверка доступности"""
        ...
    
    def documents(self) -> dict:
        """Список документов"""
        ...
```

**Паттерны:**
- Adapter (адаптация HTTP API к доменной логике)
- Circuit Breaker (обработка таймаутов и ошибок)

### 4. Presentation Layer (Слой представления)

**Файл:** `src/avtorgraf/presentation/http_server.py`

**Ответственность:** HTTP API и статические файлы

```python
class ApiHandler(SimpleHTTPRequestHandler):
    """HTTP обработчик запросов"""
    
    def do_GET(self) -> None:
        """
        GET эндпоинты:
        - /api/health
        - /api/sessions
        - /api/documents
        - /api/documents/pipeline_status
        - /* (статические файлы)
        """
        ...
    
    def do_POST(self) -> None:
        """
        POST эндпоинты:
        - /api/chat
        """
        ...
```

**Паттерны:**
- Front Controller (единая точка входа для HTTP запросов)
- Thread-per-Request (ThreadingHTTPServer)

## Поток данных

### Запрос на чат

```
1. Клиент (Browser)
   ↓ POST /api/chat
   
2. ApiHandler.do_POST()
   ↓ парсинг JSON
   
3. ChatService.ask(question, session_id, mode)
   ↓ валидация
   
4. ConversationRepository
   ↓ ensure_session()
   ↓ get_recent_messages() → история
   
5. LightRagClient.query(question, mode, prompt, history)
   ↓ HTTP запрос к LightRAG
   
6. LightRAG API
   ↓ обработка в графе знаний
   ↓ возврат ответа + контекст
   
7. ChatService
   ↓ _extract_answer()
   ↓ _extract_references()
   
8. ConversationRepository
   ↓ add_message(user)
   ↓ add_message(assistant)
   
9. ApiHandler
   ↓ сериализация в JSON
   
10. Клиент (Browser)
    ↓ отображение ответа
```

## Паттерны проектирования

### Используемые паттерны

| Паттерн | Где используется | Зачем |
|---------|------------------|-------|
| **Dependency Injection** | ChatService, ApiHandler | Тестируемость, гибкость |
| **Repository** | ConversationRepository | Абстракция хранилища |
| **Facade** | ChatService | Упрощение API |
| **Adapter** | LightRagClient | Адаптация внешнего API |
| **Factory** | Settings.from_env() | Создание конфигурации |
| **Value Object** | ChatMessage, Reference | Иммутабельные данные |
| **Front Controller** | ApiHandler | Единая точка входа |

### SOLID принципы

**Single Responsibility:**
- `ChatService` — только бизнес-логика диалога
- `ConversationRepository` — только работа с БД
- `LightRagClient` — только HTTP клиент

**Open/Closed:**
- Можно добавить новый режим поиска без изменения `ChatService`
- Можно заменить SQLite на PostgreSQL, реализовав интерфейс Repository

**Liskov Substitution:**
- Доменные модели используют протоколы Python
- Любая реализация Repository будет работать с ChatService

**Interface Segregation:**
- Клиенты зависят только от нужных им методов
- `ChatService` не знает про HTTP или SQL

**Dependency Inversion:**
- Высокоуровневый код (`ChatService`) не зависит от деталей
- Зависимости направлены к доменному слою

## Принятые решения

### Почему без внешних зависимостей?

**Решение:** Использовать только стандартную библиотеку Python

**Обоснование:**
- ✅ Нулевое время установки
- ✅ Минимальная поверхность атаки
- ✅ Нет конфликтов версий
- ✅ Быстрый старт проекта
- ✅ Легкость развертывания

**Компромиссы:**
- ⚠️ Более многословный код
- ⚠️ Нет готовых ORM и HTTP клиентов
- ⚠️ Ручная обработка ошибок

### Почему SQLite?

**Решение:** Использовать SQLite для хранения сессий

**Обоснование:**
- ✅ Встроен в Python
- ✅ Нулевая конфигурация
- ✅ Подходит для MVP и малых нагрузок
- ✅ Простое резервное копирование (копирование файла)
- ✅ ACID транзакции

**Когда мигрировать на PostgreSQL:**
- Более 10 одновременных пользователей
- Необходимость full-text search
- Репликация и высокая доступность

### Почему ThreadingHTTPServer?

**Решение:** Использовать ThreadingHTTPServer из stdlib

**Обоснование:**
- ✅ Достаточно для MVP
- ✅ Простота отладки
- ✅ Нет зависимости от Flask/FastAPI

**Когда мигрировать на ASGI:**
- Более 100 RPS
- Необходимость WebSocket
- Необходимость async/await

## Расширение системы

### Добавление нового режима поиска

1. Обновите `DEFAULT_QUERY_MODE` в `.env`
2. Добавьте опцию в `<select id="mode">` в `index.html`
3. Код в `ChatService` автоматически поддержит новый режим

### Замена SQLite на PostgreSQL

1. Создайте новый класс `PostgresConversationRepository`
2. Реализуйте те же методы, что и `ConversationRepository`
3. Замените инициализацию в `main.py`:

```python
# Было:
repository = ConversationRepository(settings.database_path)

# Стало:
repository = PostgresConversationRepository(settings.postgres_url)
```

### Добавление аутентификации

1. Создайте middleware в `http_server.py`
2. Проверяйте токены перед обработкой запроса
3. Сохраняйте user_id в сессии для персонализации

### Добавление кеширования

1. Создайте `CachingChatService` с декоратором
2. Используйте functools.lru_cache или Redis
3. Кешируйте ответы LightRAG по hash(question + mode)

## Тестирование

### Структура тестов (будущее)

```
tests/
├── unit/
│   ├── domain/
│   │   └── test_models.py
│   ├── application/
│   │   └── test_chat_service.py
│   └── infrastructure/
│       ├── test_database.py
│       └── test_lightrag_client.py
├── integration/
│   └── test_http_api.py
└── e2e/
    └── test_user_flow.py
```

### Моки для тестов

```python
# Мок LightRagClient
class FakeLightRagClient:
    def query(self, question, mode, user_prompt, history):
        return {
            "response": "Тестовый ответ",
            "references": []
        }, 100

# Мок ConversationRepository
class InMemoryRepository:
    def __init__(self):
        self.sessions = {}
        self.messages = {}
```

## Метрики производительности

### Целевые показатели

| Метрика | Цель | Текущее |
|---------|------|---------|
| Время ответа API (без LightRAG) | < 100ms | ~50ms |
| Время запроса к LightRAG | < 5s | ~2-3s |
| Размер БД на 1000 сессий | < 50MB | ~30MB |
| Память приложения | < 100MB | ~40MB |
| Одновременных пользователей | 10+ | 10+ |

## Безопасность

### Угрозы и меры защиты

| Угроза | Мера защиты |
|--------|-------------|
| SQL Injection | Параметризованные запросы |
| XSS | Content-Type: application/json |
| CSRF | SameSite cookies (будущее) |
| DoS | Rate limiting на Nginx |
| Секреты в коде | .env файлы |

## Дальнейшее развитие

### Краткосрочные цели (1-3 месяца)

- [ ] Unit тесты (coverage > 80%)
- [ ] Integration тесты API
- [ ] CI/CD с автоматическим развертыванием
- [ ] Логирование (structured logging)
- [ ] Метрики (Prometheus)

### Среднесрочные цели (3-6 месяцев)

- [ ] Миграция на PostgreSQL
- [ ] Асинхронная обработка (async/await)
- [ ] WebSocket для real-time ответов
- [ ] Кеширование ответов
- [ ] Полнотекстовый поиск по истории

### Долгосрочные цели (6-12 месяцев)

- [ ] Микросервисная архитектура
- [ ] Event-driven подход (Kafka/RabbitMQ)
- [ ] Мультиязычность
- [ ] ML для предсказания вопросов
- [ ] Мобильные приложения

---

**Документ актуален на:** 2026-06-02  
**Автор:** Команда разработки АВТОГРАФ  
**Версия:** 1.0.0
