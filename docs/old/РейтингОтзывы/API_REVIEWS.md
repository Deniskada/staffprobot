# API Документация: Система отзывов и рейтингов

## Обзор

Система отзывов и рейтингов предоставляет универсальный компонент для оценки сотрудников и объектов с системой модерации и обжалований.

## Основные возможности

- **Отзывы**: Создание отзывов о сотрудниках и объектах с рейтингом 1-5 звезд
- **Медиа-файлы**: Поддержка фотографий, видео, аудио и документов
- **Модерация**: Автоматическая и ручная модерация отзывов
- **Обжалования**: Система обжалования отклоненных отзывов
- **Рейтинги**: Автоматический расчет рейтингов с учетом "свежести" отзывов
- **Уведомления**: Интеграция с системой уведомлений

## Аутентификация

Все API endpoints требуют аутентификации. Используйте JWT токены в заголовке `Authorization: Bearer <token>`.

## Endpoints

### Отзывы

#### `GET /api/reviews/my-reviews`
Получение отзывов текущего пользователя.

**Параметры запроса:**
- `target_type` (optional): Тип цели (`employee` или `object`)
- `limit` (optional): Количество записей (по умолчанию 20)
- `offset` (optional): Смещение (по умолчанию 0)

**Ответ:**
```json
{
  "success": true,
  "reviews": [
    {
      "id": 1,
      "target_type": "employee",
      "target_id": 123,
      "contract_id": 456,
      "rating": 4.5,
      "title": "Отличный сотрудник",
      "content": "Очень ответственный и пунктуальный",
      "status": "approved",
      "is_anonymous": false,
      "created_at": "2025-09-28T10:00:00Z",
      "published_at": "2025-09-28T10:30:00Z"
    }
  ],
  "count": 1
}
```

#### `GET /api/reviews/available-targets/{target_type}`
Получение доступных целей для создания отзыва.

**Параметры пути:**
- `target_type`: Тип цели (`employee` или `object`)

**Ответ:**
```json
{
  "success": true,
  "target_type": "employee",
  "available_targets": [
    {
      "id": 123,
      "name": "Иван Петров",
      "contract_id": 456,
      "contract_number": "CONTRACT-001",
      "contract_title": "Договор на работу"
    }
  ],
  "count": 1
}
```

#### `POST /api/reviews/create`
Создание нового отзыва.

**Тело запроса (multipart/form-data):**
- `target_type`: Тип цели (`employee` или `object`)
- `target_id`: ID цели
- `contract_id`: ID договора
- `title`: Заголовок отзыва
- `rating`: Оценка (1.0 - 5.0)
- `content`: Содержание отзыва (optional)
- `is_anonymous`: Анонимный отзыв (boolean)
- `media_files`: Медиа-файлы (optional)

**Ответ:**
```json
{
  "success": true,
  "message": "Отзыв отправлен на модерацию",
  "review": {
    "id": 1,
    "target_type": "employee",
    "target_id": 123,
    "rating": 4.5,
    "title": "Отличный сотрудник",
    "status": "pending",
    "created_at": "2025-09-28T10:00:00Z"
  }
}
```

#### `GET /api/reviews/{review_id}`
Получение детальной информации об отзыве.

**Ответ:**
```json
{
  "success": true,
  "review": {
    "id": 1,
    "target_type": "employee",
    "target_id": 123,
    "contract_id": 456,
    "rating": 4.5,
    "title": "Отличный сотрудник",
    "content": "Очень ответственный и пунктуальный",
    "status": "approved",
    "is_anonymous": false,
    "reviewer_id": 789,
    "created_at": "2025-09-28T10:00:00Z",
    "published_at": "2025-09-28T10:30:00Z",
    "moderation_notes": null
  },
  "media_files": [
    {
      "id": 1,
      "file_type": "photo",
      "file_size": 1024000,
      "mime_type": "image/jpeg",
      "is_primary": true,
      "created_at": "2025-09-28T10:00:00Z"
    }
  ]
}
```

### Рейтинги

#### `GET /api/ratings/{target_type}/{target_id}`
Получение рейтинга объекта или сотрудника.

**Ответ:**
```json
{
  "success": true,
  "rating": {
    "id": 1,
    "target_type": "employee",
    "target_id": 123,
    "average_rating": 4.5,
    "total_reviews": 10,
    "last_updated": "2025-09-28T10:00:00Z",
    "stars": {
      "full_stars": 4,
      "has_half_star": true,
      "empty_stars": 0,
      "rating": 4.5,
      "formatted": "4.5"
    }
  }
}
```

#### `GET /api/ratings/top/{target_type}`
Получение топ рейтинговых объектов или сотрудников.

**Параметры запроса:**
- `limit` (optional): Количество записей (по умолчанию 10, максимум 50)

**Ответ:**
```json
{
  "success": true,
  "top_ratings": [
    {
      "id": 1,
      "target_type": "employee",
      "target_id": 123,
      "average_rating": 4.8,
      "total_reviews": 25,
      "last_updated": "2025-09-28T10:00:00Z",
      "stars": {
        "full_stars": 4,
        "has_half_star": true,
        "empty_stars": 0,
        "rating": 4.8,
        "formatted": "4.8"
      }
    }
  ],
  "count": 1
}
```

#### `GET /api/ratings/{target_type}/{target_id}/statistics`
Получение статистики рейтинга.

**Ответ:**
```json
{
  "success": true,
  "statistics": {
    "average_rating": 4.5,
    "total_reviews": 10,
    "rating_distribution": {
      "5": 3,
      "4": 4,
      "3": 2,
      "2": 1,
      "1": 0
    },
    "recent_trend": "increasing"
  }
}
```

### Обжалования

#### `POST /api/appeals/create`
Подача обжалования на отзыв.

**Тело запроса (multipart/form-data):**
- `review_id`: ID отзыва
- `appeal_reason`: Причина обжалования
- `appeal_evidence`: Доказательства (optional)

**Ответ:**
```json
{
  "success": true,
  "message": "Обжалование успешно подано",
  "appeal_id": 1
}
```

#### `GET /api/appeals/my-appeals`
Получение обжалований пользователя.

**Ответ:**
```json
{
  "success": true,
  "appeals": [
    {
      "id": 1,
      "review_id": 123,
      "appeal_reason": "Несправедливое отклонение",
      "appeal_evidence": "Доказательства...",
      "status": "pending",
      "created_at": "2025-09-28T10:00:00Z"
    }
  ],
  "count": 1
}
```

#### `GET /api/appeals/details/{appeal_id}`
Получение деталей обжалования.

**Ответ:**
```json
{
  "success": true,
  "appeal": {
    "id": 1,
    "review_id": 123,
    "appellant_id": 789,
    "appeal_reason": "Несправедливое отклонение",
    "appeal_evidence": "Доказательства...",
    "status": "pending",
    "moderator_decision": null,
    "decision_notes": null,
    "created_at": "2025-09-28T10:00:00Z",
    "decided_at": null
  }
}
```

### Медиа-файлы

#### `POST /api/media/upload/{file_type}`
Загрузка медиа-файла.

**Параметры пути:**
- `file_type`: Тип файла (`photo`, `video`, `audio`, `document`)

**Тело запроса (multipart/form-data):**
- `file`: Файл для загрузки

**Ограничения по размеру:**
- Фотографии: до 5MB
- Видео: до 50MB
- Аудио: до 20MB
- Документы: до 10MB

**Ответ:**
```json
{
  "success": true,
  "file": {
    "file_name": "uuid_filename.jpg",
    "file_path": "/uploads/uuid_filename.jpg",
    "file_size": 1024000,
    "mime_type": "image/jpeg",
    "file_url": "/media/uuid_filename.jpg"
  }
}
```

#### `GET /api/media/limits`
Получение лимитов для медиа-файлов.

**Ответ:**
```json
{
  "success": true,
  "limits": {
    "photo": {
      "max_size_mb": 5,
      "max_size_bytes": 5242880,
      "allowed_mime_types": ["image/jpeg", "image/png", "image/gif"]
    },
    "video": {
      "max_size_mb": 50,
      "max_size_bytes": 52428800,
      "allowed_mime_types": ["video/mp4", "video/avi", "video/mov"]
    },
    "audio": {
      "max_size_mb": 20,
      "max_size_bytes": 20971520,
      "allowed_mime_types": ["audio/mp3", "audio/wav", "audio/ogg"]
    },
    "document": {
      "max_size_mb": 10,
      "max_size_bytes": 10485760,
      "allowed_mime_types": ["application/pdf", "application/msword"]
    }
  }
}
```

### Отчеты

#### `GET /api/reports/reviews/reviews-summary`
Сводный отчет по отзывам.

**Параметры запроса:**
- `period_days` (optional): Период в днях (по умолчанию 30)
- `target_type` (optional): Тип цели для фильтрации

**Ответ:**
```json
{
  "success": true,
  "period_days": 30,
  "start_date": "2025-08-28T10:00:00Z",
  "summary": {
    "total_reviews": 100,
    "status_breakdown": {
      "pending": 5,
      "approved": 85,
      "rejected": 10
    },
    "type_breakdown": {
      "employee": 60,
      "object": 40
    },
    "average_ratings": {
      "employee": 4.2,
      "object": 4.5
    }
  },
  "top_reviews": [
    {
      "id": 1,
      "target_type": "employee",
      "target_id": 123,
      "rating": 5.0,
      "title": "Отличный сотрудник",
      "created_at": "2025-09-28T10:00:00Z"
    }
  ]
}
```

#### `GET /api/reports/reviews/reviews-by-object`
Отзывы по конкретному объекту.

**Параметры запроса:**
- `object_id`: ID объекта
- `period_days` (optional): Период в днях

**Ответ:**
```json
{
  "success": true,
  "object_id": 123,
  "period_days": 30,
  "reviews": [
    {
      "id": 1,
      "rating": 4.5,
      "title": "Хороший объект",
      "content": "Удобное расположение",
      "status": "approved",
      "is_anonymous": false,
      "created_at": "2025-09-28T10:00:00Z",
      "published_at": "2025-09-28T10:30:00Z",
      "media_files": []
    }
  ],
  "count": 1,
  "object_rating": {
    "average_rating": 4.5,
    "total_reviews": 1,
    "last_updated": "2025-09-28T10:30:00Z"
  }
}
```

#### `GET /api/reports/reviews/moderation-stats`
Статистика модерации.

**Параметры запроса:**
- `period_days` (optional): Период в днях

**Ответ:**
```json
{
  "success": true,
  "period_days": 30,
  "start_date": "2025-08-28T10:00:00Z",
  "reviews_stats": {
    "total": 100,
    "pending": 5,
    "approved": 85,
    "rejected": 10,
    "approval_rate": 85.0
  },
  "appeals_stats": {
    "total": 10,
    "pending": 2,
    "approved": 6,
    "rejected": 2,
    "approval_rate": 60.0
  },
  "moderation_performance": {
    "average_moderation_time_hours": 24.5,
    "target_moderation_time_hours": 48
  }
}
```

### Модерация (только для модераторов и суперадминов)

#### `GET /moderator/api/`
Дашборд модератора.

**Ответ:**
```json
{
  "success": true,
  "statistics": {
    "total_reviews": 100,
    "pending_reviews": 5,
    "overdue_reviews": 1,
    "approved_reviews": 85,
    "rejected_reviews": 10
  },
  "appeal_statistics": {
    "total_appeals": 10,
    "pending_appeals": 2,
    "overdue_appeals": 0,
    "approved_appeals": 6,
    "rejected_appeals": 2
  },
  "recent_pending": [
    {
      "id": 1,
      "title": "Отзыв о сотруднике",
      "target_type": "employee",
      "created_at": "2025-09-28T10:00:00Z"
    }
  ],
  "recent_appeals": [
    {
      "id": 1,
      "review_id": 123,
      "status": "pending",
      "created_at": "2025-09-28T10:00:00Z"
    }
  ]
}
```

#### `POST /moderator/api/reviews/{review_id}/moderate`
Модерация отзыва.

**Тело запроса:**
```json
{
  "status": "approved",
  "moderation_notes": "Отзыв соответствует требованиям"
}
```

**Ответ:**
```json
{
  "success": true,
  "message": "Отзыв успешно обработан"
}
```

#### `POST /moderator/api/appeals/{appeal_id}/review`
Рассмотрение обжалования.

**Тело запроса:**
```json
{
  "decision": "approved",
  "decision_notes": "Обжалование обосновано"
}
```

**Ответ:**
```json
{
  "success": true,
  "message": "Обжалование рассмотрено"
}
```

## Коды ошибок

- `400` - Неверные параметры запроса
- `401` - Не авторизован
- `403` - Недостаточно прав доступа
- `404` - Ресурс не найден
- `422` - Ошибка валидации данных
- `500` - Внутренняя ошибка сервера

## Ограничения

### Права на создание отзывов
- Владельцы могут оставлять отзывы о сотрудниках
- Сотрудники могут оставлять отзывы об объектах
- Отзыв можно оставить только по завершенному или активному договору
- Один отзыв на договор по конкретной цели

### Обжалования
- Максимум 1 обжалование на отзыв
- Обжаловать можно только отклоненные отзывы
- Время на рассмотрение обжалования: 72 часа

### Модерация
- Время на модерацию: 48 часов
- Автоматические фильтры: спам, нецензурная лексика, дублирование
- Минимальная длина контента: 20 символов

## Примеры использования

### Создание отзыва с медиа-файлами

```python
import requests

# Загрузка медиа-файла
with open('photo.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8001/api/media/upload/photo',
        files=files,
        headers={'Authorization': 'Bearer <token>'}
    )
    media_info = response.json()['file']

# Создание отзыва
data = {
    'target_type': 'employee',
    'target_id': 123,
    'contract_id': 456,
    'title': 'Отличный сотрудник',
    'rating': 5.0,
    'content': 'Очень ответственный и пунктуальный',
    'is_anonymous': False
}

files = {'media_files': open('photo.jpg', 'rb')}

response = requests.post(
    'http://localhost:8001/api/reviews/create',
    data=data,
    files=files,
    headers={'Authorization': 'Bearer <token>'}
)
```

### Получение рейтинга сотрудника

```python
response = requests.get(
    'http://localhost:8001/api/ratings/employee/123',
    headers={'Authorization': 'Bearer <token>'}
)

rating_data = response.json()['rating']
print(f"Рейтинг: {rating_data['average_rating']}/5.0")
print(f"Количество отзывов: {rating_data['total_reviews']}")
```

### Подача обжалования

```python
data = {
    'review_id': 123,
    'appeal_reason': 'Отзыв был отклонен несправедливо',
    'appeal_evidence': 'Доказательства корректности отзыва'
}

response = requests.post(
    'http://localhost:8001/api/appeals/create',
    data=data,
    headers={'Authorization': 'Bearer <token>'}
)
```
