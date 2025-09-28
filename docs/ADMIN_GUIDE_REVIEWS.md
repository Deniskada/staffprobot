# Административное руководство: Система отзывов и рейтингов

## Обзор системы

Система отзывов и рейтингов - это универсальный компонент для оценки сотрудников и объектов с интегрированной системой модерации и обжалований.

## Архитектура системы

### Компоненты

1. **Модели данных** (`domain/entities/review.py`)
   - `Review` - основная модель отзывов
   - `ReviewMedia` - медиа-файлы отзывов
   - `ReviewAppeal` - обжалования отзывов
   - `Rating` - рейтинги объектов/сотрудников
   - `SystemRule` - правила системы

2. **Сервисы** (`shared/services/`)
   - `RatingService` - расчет и управление рейтингами
   - `ModerationService` - модерация отзывов
   - `AppealService` - обработка обжалований
   - `ReviewPermissionService` - проверка прав
   - `MediaService` - работа с медиа-файлами

3. **API endpoints** (`apps/web/routes/`)
   - `shared_reviews.py` - API отзывов
   - `shared_ratings.py` - API рейтингов
   - `shared_appeals.py` - API обжалований
   - `moderator.py` - API модерации
   - `review_reports.py` - API отчетов

4. **Веб-интерфейсы** (`apps/web/templates/`)
   - Роли: owner, employee, manager, moderator
   - Компоненты: shared/templates/reviews/

## Настройка системы

### Переменные окружения

```bash
# Настройки медиа-файлов
MEDIA_UPLOAD_DIR=/app/uploads
MAX_PHOTO_SIZE=5242880  # 5MB
MAX_VIDEO_SIZE=52428800  # 50MB
MAX_AUDIO_SIZE=20971520  # 20MB
MAX_DOCUMENT_SIZE=10485760  # 10MB

# Настройки модерации
MODERATION_TIME_LIMIT_HOURS=48
APPEAL_TIME_LIMIT_HOURS=72
MIN_CONTENT_LENGTH=20

# Настройки рейтингов
RATING_HALF_LIFE_DAYS=90
INITIAL_RATING=5.0
RATING_PRECISION=0.5
```

### Конфигурация базы данных

```sql
-- Индексы для производительности
CREATE INDEX CONCURRENTLY idx_reviews_target_type_id ON reviews(target_type, target_id);
CREATE INDEX CONCURRENTLY idx_reviews_status_created ON reviews(status, created_at);
CREATE INDEX CONCURRENTLY idx_reviews_contract_id ON reviews(contract_id);
CREATE INDEX CONCURRENTLY idx_ratings_target_type_id ON ratings(target_type, target_id);
CREATE INDEX CONCURRENTLY idx_review_appeals_status ON review_appeals(status);
```

## Управление модерацией

### Роли модераторов

1. **Модератор** - базовая роль для модерации контента
2. **Суперадмин** - полный доступ ко всем функциям

### Назначение ролей

```python
# Через API
POST /admin/users/{user_id}/roles
{
    "roles": ["moderator"]
}

# Через базу данных
INSERT INTO user_roles (user_id, role) VALUES (123, 'moderator');
```

### Интерфейс модератора

**URL:** `/moderator/`

**Основные функции:**
- Дашборд с общей статистикой
- Список отзывов на модерации
- Рассмотрение обжалований
- Статистика работы модераторов

### Автоматические фильтры

#### Спам-фильтр
```python
SPAM_PATTERNS = [
    r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
    r'\b(?:buy now|discount|promo code)\b'
]
```

#### Фильтр нецензурной лексики
```python
PROFANITY_PATTERNS = [
    r'\b(?:fuck|shit|asshole)\b'
]
```

#### Фильтр личной информации
```python
PERSONAL_INFO_PATTERNS = [
    r'\b\d{10,12}\b',  # Телефоны
    r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'  # Email
]
```

### Настройка фильтров

```python
# В shared/services/moderation_service.py
class ModerationService:
    def __init__(self, db: AsyncSession):
        self.spam_patterns = [
            # Добавьте свои паттерны
        ]
        self.profanity_patterns = [
            # Добавьте свои паттерны
        ]
        self.personal_info_patterns = [
            # Добавьте свои паттерны
        ]
```

## Мониторинг системы

### Ключевые метрики

1. **Производительность модерации**
   - Среднее время модерации
   - Количество просроченных отзывов
   - Процент одобренных отзывов

2. **Качество контента**
   - Процент отзывов, прошедших автоматические фильтры
   - Количество обжалований
   - Процент одобренных обжалований

3. **Использование системы**
   - Количество отзывов в день/неделю/месяц
   - Активность по ролям
   - Популярность медиа-файлов

### Дашборд администратора

**URL:** `/admin/reviews/`

**Разделы:**
- Общая статистика
- Производительность модерации
- Качество контента
- Пользовательская активность
- Системные настройки

### Алерты и уведомления

```python
# Настройка алертов
ALERT_CONFIG = {
    "moderation_overdue": {
        "threshold": 48,  # часов
        "channels": ["email", "telegram"]
    },
    "appeal_overdue": {
        "threshold": 72,  # часов
        "channels": ["email", "telegram"]
    },
    "high_rejection_rate": {
        "threshold": 0.3,  # 30%
        "channels": ["email"]
    }
}
```

## Управление контентом

### Массовые операции

```python
# Одобрение нескольких отзывов
POST /moderator/api/reviews/bulk-moderate
{
    "review_ids": [1, 2, 3],
    "status": "approved",
    "moderation_notes": "Массовое одобрение"
}

# Отклонение с одинаковой причиной
POST /moderator/api/reviews/bulk-moderate
{
    "review_ids": [4, 5, 6],
    "status": "rejected",
    "moderation_notes": "Спам-контент"
}
```

### Управление медиа-файлами

```python
# Очистка неиспользуемых файлов
POST /admin/media/cleanup
{
    "older_than_days": 30,
    "dry_run": true
}

# Сжатие изображений
POST /admin/media/optimize
{
    "file_types": ["photo"],
    "quality": 85
}
```

### Управление рейтингами

```python
# Пересчет рейтинга
POST /api/ratings/{target_type}/{target_id}/recalculate

# Массовый пересчет
POST /admin/ratings/recalculate-all
{
    "target_type": "employee",
    "batch_size": 100
}
```

## Безопасность

### Права доступа

```python
# Проверка прав на создание отзыва
async def can_create_review(user_id, target_type, target_id, contract_id):
    # 1. Пользователь участвует в договоре
    # 2. Договор активен или завершен
    # 3. Цель связана с договором
    # 4. Отзыв еще не оставлен
    # 5. Есть права по роли
```

### Валидация данных

```python
# Валидация рейтинга
def validate_rating(rating: float) -> bool:
    return 1.0 <= rating <= 5.0 and rating % 0.5 == 0

# Валидация медиа-файлов
def validate_media_file(file: UploadFile, file_type: str) -> bool:
    limits = MEDIA_LIMITS[file_type]
    return (
        file.content_type in limits["allowed_mime_types"] and
        file.size <= limits["max_size_bytes"]
    )
```

### Аудит действий

```python
# Логирование действий модератора
logger.info(
    "Review moderated",
    review_id=review_id,
    moderator_id=moderator_id,
    action=status,
    notes=moderation_notes
)

# Логирование создания отзыва
logger.info(
    "Review created",
    review_id=review.id,
    reviewer_id=review.reviewer_id,
    target_type=review.target_type,
    target_id=review.target_id
)
```

## Производительность

### Оптимизация запросов

```python
# Использование индексов
query = select(Review).where(
    and_(
        Review.target_type == target_type,
        Review.target_id == target_id,
        Review.status == 'approved'
    )
).options(joinedload(Review.media))

# Пагинация
query = query.limit(limit).offset(offset)
```

### Кэширование

```python
# Кэширование рейтингов
@cache(expire=300)  # 5 минут
async def get_rating(target_type: str, target_id: int):
    return await rating_service.get_rating(target_type, target_id)

# Кэширование статистики
@cache(expire=600)  # 10 минут
async def get_moderation_stats():
    return await moderation_service.get_moderation_statistics()
```

### Мониторинг производительности

```python
# Метрики времени ответа
@timed_metric("review_api_response_time")
async def create_review_endpoint():
    pass

# Метрики использования ресурсов
@memory_metric("review_processing_memory")
async def process_review_media():
    pass
```

## Резервное копирование

### Экспорт данных

```bash
# Экспорт отзывов
pg_dump -t reviews -t review_media -t review_appeals -t ratings \
    staffprobot_prod > reviews_backup.sql

# Экспорт медиа-файлов
tar -czf media_backup.tar.gz /app/uploads/
```

### Восстановление

```bash
# Восстановление данных
psql staffprobot_prod < reviews_backup.sql

# Восстановление медиа-файлов
tar -xzf media_backup.tar.gz -C /app/
```

## Обслуживание системы

### Ежедневные задачи

1. **Проверка просроченных отзывов**
   ```bash
   curl -X GET "http://localhost:8001/moderator/api/reviews/overdue"
   ```

2. **Очистка временных файлов**
   ```bash
   find /app/uploads/temp -type f -mtime +1 -delete
   ```

3. **Проверка логов ошибок**
   ```bash
   grep "ERROR" /var/log/staffprobot/reviews.log | tail -100
   ```

### Еженедельные задачи

1. **Анализ производительности модерации**
2. **Обновление фильтров спама**
3. **Архивирование старых отзывов**

### Ежемесячные задачи

1. **Анализ качества контента**
2. **Обновление правил модерации**
3. **Оптимизация базы данных**

## Устранение неполадок

### Частые проблемы

1. **Медленная модерация**
   - Проверить количество модераторов
   - Увеличить лимиты времени
   - Оптимизировать фильтры

2. **Ошибки загрузки медиа**
   - Проверить права доступа к папке uploads
   - Увеличить лимиты размера файлов
   - Проверить свободное место на диске

3. **Неточные рейтинги**
   - Пересчитать рейтинги
   - Проверить алгоритм расчета
   - Обновить веса отзывов

### Логи и диагностика

```bash
# Логи модерации
tail -f /var/log/staffprobot/moderation.log

# Логи API
tail -f /var/log/staffprobot/api.log

# Логи производительности
tail -f /var/log/staffprobot/performance.log
```

## Обновления системы

### Миграции базы данных

```bash
# Применение миграций
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# Откат миграций
docker compose -f docker-compose.prod.yml exec web alembic downgrade -1
```

### Обновление кода

```bash
# Обновление сервисов
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Проверка работоспособности
curl -X GET "http://localhost:8001/health"
```

### Тестирование обновлений

```bash
# Запуск тестов
docker compose -f docker-compose.prod.yml exec web pytest tests/unit/test_review_services.py

# Тестирование производительности
docker compose -f docker-compose.prod.yml exec web pytest tests/performance/
```

---

*Документация обновлена: 28 сентября 2025*
*Версия системы: 1.0.0*
