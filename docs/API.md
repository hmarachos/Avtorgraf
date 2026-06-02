# АВТОГРАФ API Документация

Полная документация HTTP API для интеграции с системой АВТОГРАФ.

## Базовый URL

```
http://localhost:8080/api
```

В продакшене замените на ваш домен.

## Аутентификация

API не требует аутентификации на уровне приложения. Безопасность обеспечивается на уровне сети и reverse proxy.

## Эндпоинты

### POST /api/chat

Отправить вопрос в LightRAG и получить ответ с нормативными ссылками.

**Request:**
```http
POST /api/chat HTTP/1.1
Content-Type: application/json

{
  "question": "Можно ли подписывать Акта освидетельствования скрытых работ при выявленных дефектах бетона?",
  "session_id": "abc123def456",
  "mode": "mix"
}
```

**Parameters:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| question | string | Да | Вопрос пользователя (не может быть пустым) |
| session_id | string | Нет | ID сессии для продолжения диалога. Если не указан, будет создана новая сессия |
| mode | string | Нет | Режим поиска LightRAG: `mix`, `hybrid`, `global`, `local`, `naive`. По умолчанию: `mix` |

**Response (200 OK):**
```json
{
  "session_id": "abc123def456",
  "answer": "Согласно пункту 5.3.4 СН 1.03.01-2019 'Организация строительного производства', акт освидетельствования скрытых работ (АОСР) подписывается только после устранения всех выявленных дефектов...",
  "references": [
    {
      "title": "СН 1.03.01-2019",
      "source": "documents/sn_1_03_01_2019.pdf",
      "snippet": "5.3.4 Акт освидетельствования скрытых работ подписывается...",
      "metadata": {
        "page": 42,
        "section": "5.3"
      }
    }
  ],
  "elapsed_ms": 2450
}
```

**Response Fields:**

| Поле | Тип | Описание |
|------|-----|----------|
| session_id | string | ID сессии (новый или существующий) |
| answer | string | Ответ ассистента на вопрос |
| references | array | Массив нормативных ссылок |
| references[].title | string | Название документа или источника |
| references[].source | string | Путь к файлу или URL источника |
| references[].snippet | string | Фрагмент текста из документа |
| references[].metadata | object | Дополнительные метаданные (страница, раздел и т.д.) |
| elapsed_ms | integer | Время выполнения запроса к LightRAG в миллисекундах |

**Error Responses:**

```json
// 400 Bad Request - пустой вопрос
{
  "error": "Вопрос не может быть пустым"
}

// 502 Bad Gateway - LightRAG недоступен
{
  "error": "LightRAG недоступен: Connection refused"
}
```

---

### GET /api/health

Проверка доступности приложения и LightRAG сервера.

**Request:**
```http
GET /api/health HTTP/1.1
```

**Response (200 OK):**
```json
{
  "app": "ok",
  "lightrag": {
    "ok": true,
    "elapsed_ms": 120,
    "details": {
      "version": "1.0.0",
      "status": "running"
    }
  }
}
```

**Response Fields:**

| Поле | Тип | Описание |
|------|-----|----------|
| app | string | Статус приложения (всегда `"ok"`) |
| lightrag.ok | boolean | Доступность LightRAG сервера |
| lightrag.elapsed_ms | integer | Время ответа LightRAG в мс |
| lightrag.details | object | Дополнительная информация от LightRAG |

**Response (когда LightRAG недоступен):**
```json
{
  "app": "ok",
  "lightrag": {
    "ok": false,
    "error": "LightRAG недоступен: Connection timeout"
  }
}
```

---

### GET /api/sessions

Получить список последних сессий диалогов.

**Request:**
```http
GET /api/sessions HTTP/1.1
```

**Response (200 OK):**
```json
{
  "sessions": [
    {
      "id": "abc123def456",
      "title": "Можно ли подписывать Акт освидетельствования скрытых работ при выявленных дефектах бетона?",
      "created_at": "2026-06-02T10:30:00+00:00",
      "updated_at": "2026-06-02T11:15:00+00:00"
    },
    {
      "id": "xyz789ghi012",
      "title": "Какие документы нужны для согласования замены материалов?",
      "created_at": "2026-06-01T14:20:00+00:00",
      "updated_at": "2026-06-01T14:45:00+00:00"
    }
  ]
}
```

**Response Fields:**

| Поле | Тип | Описание |
|------|-----|----------|
| sessions | array | Массив сессий (до 20 последних) |
| sessions[].id | string | Уникальный ID сессии |
| sessions[].title | string | Заголовок сессии (первые 80 символов первого вопроса) |
| sessions[].created_at | string | Дата и время создания (ISO 8601 UTC) |
| sessions[].updated_at | string | Дата и время последнего сообщения (ISO 8601 UTC) |

---

### GET /api/documents

Получить список документов в базе знаний LightRAG.

**Request:**
```http
GET /api/documents HTTP/1.1
```

**Response (200 OK):**
```json
{
  "documents": [
    {
      "id": "doc_001",
      "name": "СН 1.03.01-2019.pdf",
      "status": "processed",
      "size": 2457600,
      "processed_at": "2026-05-15T08:00:00+00:00"
    },
    {
      "id": "doc_002",
      "name": "СТБ 1937-2022.pdf",
      "status": "processed",
      "size": 1843200,
      "processed_at": "2026-05-15T08:05:00+00:00"
    }
  ],
  "total": 125
}
```

**Error Response (502 Bad Gateway):**
```json
{
  "error": "LightRAG HTTP 500: Internal Server Error"
}
```

---

### GET /api/documents/pipeline_status

Получить статус обработки документов в LightRAG.

**Request:**
```http
GET /api/documents/pipeline_status HTTP/1.1
```

**Response (200 OK):**
```json
{
  "pipeline": "idle",
  "processed": 125,
  "pending": 0,
  "errors": 0,
  "current_document": null,
  "progress_percent": 100
}
```

**Response Fields:**

| Поле | Тип | Описание |
|------|-----|----------|
| pipeline | string | Статус конвейера: `idle`, `processing`, `error` |
| processed | integer | Количество обработанных документов |
| pending | integer | Количество документов в очереди |
| errors | integer | Количество ошибок обработки |
| current_document | string/null | Имя текущего обрабатываемого документа |
| progress_percent | integer | Процент выполнения (0-100) |

**Error Response (502 Bad Gateway):**
```json
{
  "error": "LightRAG недоступен: Connection refused"
}
```

---

## Коды ответов

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 400 | Некорректные параметры запроса |
| 404 | Эндпоинт не найден |
| 502 | Ошибка при взаимодействии с LightRAG |

---

## Примеры использования

### cURL

```bash
# Отправить вопрос
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Какие документы нужны для согласования замены материалов?",
    "mode": "mix"
  }'

# Проверить health
curl http://localhost:8080/api/health

# Получить сессии
curl http://localhost:8080/api/sessions
```

### Python

```python
import requests

# Отправить вопрос
response = requests.post(
    "http://localhost:8080/api/chat",
    json={
        "question": "Какие документы нужны для согласования замены материалов?",
        "mode": "mix"
    }
)
data = response.json()
print(f"Ответ: {data['answer']}")
print(f"Время: {data['elapsed_ms']}ms")
```

### JavaScript (Fetch API)

```javascript
// Отправить вопрос
async function askQuestion(question, sessionId = null, mode = 'mix') {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId, mode })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  return await response.json();
}

// Использование
try {
  const result = await askQuestion('Какие документы нужны для согласования замены материалов?');
  console.log('Ответ:', result.answer);
  console.log('Ссылки:', result.references);
} catch (error) {
  console.error('Ошибка:', error.message);
}
```

---

## Rate Limiting

API не имеет встроенного rate limiting. Рекомендуется настроить ограничения на уровне reverse proxy (например, Nginx).

Пример конфигурации Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/chat {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://localhost:8080;
}
```

---

## Безопасность

- Используйте HTTPS в продакшене
- Настройте CORS для ограничения доступа
- Добавьте аутентификацию на уровне reverse proxy
- Логируйте все обращения к API
- Регулярно обновляйте зависимости

---

## Обработка ошибок

Все ошибки возвращаются в формате JSON:

```json
{
  "error": "Описание ошибки"
}
```

Рекомендуется проверять HTTP статус код и обрабатывать ошибки соответствующим образом:

```javascript
async function safeApiCall(url, options) {
  try {
    const response = await fetch(url, options);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    
    return data;
  } catch (error) {
    console.error('API Error:', error.message);
    throw error;
  }
}
```

---

## Версионирование

Текущая версия API: **v1**

API не имеет префикса версии в URL. При значительных изменениях будет добавлен префикс `/api/v2/`.
