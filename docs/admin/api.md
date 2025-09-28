# API документация

## 🌐 Обзор API

StaffProBot предоставляет RESTful API для интеграции с внешними системами и автоматизации процессов управления персоналом.

## 🔐 Аутентификация

### JWT токены
Все API запросы требуют JWT токен в заголовке Authorization:
```
Authorization: Bearer <your_jwt_token>
```

### Получение токена
```http
POST /api/auth/login
Content-Type: application/json

{
  "telegram_id": 123456789,
  "pin_code": "123456"
}
```

**Ответ:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "telegram_id": 123456789,
    "role": "owner",
    "username": "user123"
  }
}
```

## 📊 Основные эндпоинты

### Пользователи

#### Получить список пользователей
```http
GET /api/users?role=owner&limit=10&offset=0
Authorization: Bearer <token>
```

#### Создать пользователя
```http
POST /api/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "telegram_id": 987654321,
  "username": "newuser",
  "first_name": "John",
  "last_name": "Doe",
  "role": "employee"
}
```

#### Обновить пользователя
```http
PUT /api/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "first_name": "John Updated",
  "role": "manager"
}
```

### Объекты

#### Получить объекты пользователя
```http
GET /api/objects
Authorization: Bearer <token>
```

#### Создать объект
```http
POST /api/objects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Новый объект",
  "address": "ул. Примерная, 123",
  "latitude": 55.7558,
  "longitude": 37.6176,
  "description": "Описание объекта"
}
```

#### Обновить объект
```http
PUT /api/objects/{object_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Обновленное название",
  "address": "Новый адрес"
}
```

### Смены

#### Получить смены
```http
GET /api/shifts?object_id=1&date_from=2025-01-01&date_to=2025-01-31
Authorization: Bearer <token>
```

#### Создать смену
```http
POST /api/shifts
Authorization: Bearer <token>
Content-Type: application/json

{
  "object_id": 1,
  "user_id": 2,
  "start_time": "2025-01-01T09:00:00Z",
  "end_time": "2025-01-01T18:00:00Z",
  "description": "Описание смены"
}
```

#### Открыть смену
```http
POST /api/shifts/{shift_id}/open
Authorization: Bearer <token>
Content-Type: application/json

{
  "latitude": 55.7558,
  "longitude": 37.6176
}
```

#### Закрыть смену
```http
POST /api/shifts/{shift_id}/close
Authorization: Bearer <token>
Content-Type: application/json

{
  "latitude": 55.7558,
  "longitude": 37.6176,
  "notes": "Заметки по смене"
}
```

### Отчеты

#### Получить отчеты
```http
GET /api/reports?type=shifts&date_from=2025-01-01&date_to=2025-01-31
Authorization: Bearer <token>
```

#### Экспорт отчета
```http
GET /api/reports/export?type=shifts&format=excel&date_from=2025-01-01&date_to=2025-01-31
Authorization: Bearer <token>
```

## 🔧 Системные настройки

### Получить настройки
```http
GET /api/system-settings
Authorization: Bearer <token>
```

### Обновить домен
```http
POST /api/system-settings/domain
Authorization: Bearer <token>
Content-Type: application/json

{
  "domain": "yourdomain.com"
}
```

### Настроить SSL
```http
POST /api/system-settings/ssl/setup
Authorization: Bearer <token>
Content-Type: application/json

{
  "domain": "yourdomain.com",
  "email": "admin@yourdomain.com"
}
```

### Получить статус SSL
```http
GET /api/system-settings/ssl/status
Authorization: Bearer <token>
```

## 📈 Мониторинг

### Статус системы
```http
GET /api/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-28T13:42:10.751Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "bot": "healthy"
  },
  "metrics": {
    "uptime": 86400,
    "memory_usage": 512,
    "cpu_usage": 25.5
  }
}
```

### Метрики
```http
GET /api/metrics
Authorization: Bearer <token>
```

### Логи
```http
GET /api/logs?level=ERROR&limit=50&offset=0
Authorization: Bearer <token>
```

## 🔄 Webhooks

### Настройка webhook
```http
POST /api/webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://yourdomain.com/webhook",
  "events": ["shift.opened", "shift.closed", "user.created"],
  "secret": "your_webhook_secret"
}
```

### События webhook
```json
{
  "event": "shift.opened",
  "timestamp": "2025-09-28T13:42:10.751Z",
  "data": {
    "shift_id": 123,
    "user_id": 456,
    "object_id": 789,
    "opened_at": "2025-09-28T13:42:10.751Z"
  }
}
```

## 📊 Коды ответов

### Успешные ответы
- **200 OK** - запрос выполнен успешно
- **201 Created** - ресурс создан
- **204 No Content** - запрос выполнен, контент не возвращен

### Ошибки клиента
- **400 Bad Request** - неверный запрос
- **401 Unauthorized** - не авторизован
- **403 Forbidden** - нет прав доступа
- **404 Not Found** - ресурс не найден
- **422 Unprocessable Entity** - ошибка валидации

### Ошибки сервера
- **500 Internal Server Error** - внутренняя ошибка сервера
- **502 Bad Gateway** - ошибка шлюза
- **503 Service Unavailable** - сервис недоступен

## 📝 Примеры использования

### Python
```python
import requests
import json

# Аутентификация
auth_response = requests.post('http://localhost:8001/api/auth/login', json={
    'telegram_id': 123456789,
    'pin_code': '123456'
})
token = auth_response.json()['access_token']

# Заголовки для API запросов
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Получение объектов
objects = requests.get('http://localhost:8001/api/objects', headers=headers)
print(objects.json())

# Создание смены
shift_data = {
    'object_id': 1,
    'user_id': 2,
    'start_time': '2025-01-01T09:00:00Z',
    'end_time': '2025-01-01T18:00:00Z'
}
response = requests.post('http://localhost:8001/api/shifts', 
                        headers=headers, json=shift_data)
print(response.json())
```

### JavaScript
```javascript
// Аутентификация
const authResponse = await fetch('http://localhost:8001/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    telegram_id: 123456789,
    pin_code: '123456'
  })
});

const { access_token } = await authResponse.json();

// API запросы
const apiCall = async (endpoint, options = {}) => {
  const response = await fetch(`http://localhost:8001/api${endpoint}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${access_token}`,
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
  
  return response.json();
};

// Использование
const objects = await apiCall('/objects');
const shifts = await apiCall('/shifts?object_id=1');
```

### cURL
```bash
# Аутентификация
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "pin_code": "123456"}' | \
  jq -r '.access_token')

# Получение объектов
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/objects

# Создание смены
curl -X POST http://localhost:8001/api/shifts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "object_id": 1,
    "user_id": 2,
    "start_time": "2025-01-01T09:00:00Z",
    "end_time": "2025-01-01T18:00:00Z"
  }'
```

## 🔒 Безопасность

### Rate Limiting
- **100 запросов в минуту** для аутентифицированных пользователей
- **10 запросов в минуту** для неаутентифицированных запросов

### Валидация данных
- Все входные данные валидируются
- SQL injection защита
- XSS защита

### HTTPS
- Все API запросы должны использовать HTTPS в продакшене
- SSL сертификаты автоматически обновляются

## 📚 Дополнительные ресурсы

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`
- **OpenAPI Schema**: `http://localhost:8001/openapi.json`

---

**Связанные разделы**:
- [Установка и настройка](installation.md)
- [Мониторинг и логи](monitoring.md)
- [Безопасность](security.md)
