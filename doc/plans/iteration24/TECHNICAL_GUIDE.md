# 📖 Техническое руководство — Итерация 24

## Архитектура системы уведомлений

### Компоненты

```
┌─────────────────────────────────────────────────────────────┐
│                    NotificationService                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Create     │  │   Retrieve   │  │   Update     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Notification Model                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  user_id | type | channel | status | priority        │   │
│  │  title | message | data | scheduled_at | sent_at     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Channel Router                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Email   │  │   SMS    │  │   Push   │  │ Telegram │   │
│  │ Channel  │  │ Channel  │  │ Channel  │  │ Channel  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Delivery Status                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Pending  │  │   Sent   │  │Delivered │  │  Failed  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Структура файлов

### Новые файлы

```
staffprobot/
├── domain/entities/
│   ├── notification.py              # Основная модель уведомлений
│   └── notification_preferences.py  # Настройки пользователей
│
├── core/notifications/
│   ├── __init__.py
│   ├── base_channel.py              # Базовый класс канала
│   ├── email_channel.py             # Email доставка
│   ├── sms_channel.py               # SMS доставка
│   ├── push_channel.py              # Web Push доставка
│   ├── telegram_channel.py          # Telegram доставка
│   └── channel_router.py            # Маршрутизатор каналов
│
├── core/utils/
│   └── notification_rate_limiter.py # Rate limiting
│
├── shared/services/
│   ├── notification_service.py      # Основной сервис (восстановлен)
│   └── notification_analytics.py    # Аналитика
│
├── shared/templates/notifications/
│   ├── base_templates.py            # Универсальные шаблоны
│   ├── email/                       # HTML шаблоны для email
│   │   ├── base.html
│   │   ├── shift_reminder.html
│   │   ├── contract_signed.html
│   │   └── daily_digest.html
│   └── sms/                         # Text шаблоны для SMS
│       └── templates.txt
│
├── apps/web/
│   ├── routes/
│   │   └── notifications.py         # API endpoints (восстановлен)
│   ├── templates/
│   │   └── shared/
│   │       └── notification_settings.html  # UI настроек
│   └── static/
│       ├── js/
│       │   ├── push_notifications.js       # Push подписка
│       │   └── sw.js                       # Service Worker
│       └── css/
│           └── notifications.css
│
├── core/celery/tasks/
│   └── notification_scheduler.py    # Celery задачи
│
└── tests/
    ├── unit/
    │   ├── test_notification_service.py
    │   └── test_channels.py
    └── integration/
        └── test_notification_flow.py
```

---

## Модель данных

### Notification

```python
class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Тип и канал
    type = Column(Enum(NotificationType), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    
    # Статус и приоритет
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    
    # Содержимое
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Дополнительные данные
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    user = relationship("User", back_populates="notifications")
```

### NotificationPreferences

```python
class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Настройки по типам (JSON)
    # {
    #   "shift": {"enabled": true, "channels": ["email", "telegram"], "frequency": "instant"},
    #   "contract": {"enabled": true, "channels": ["email"], "frequency": "instant"},
    #   ...
    # }
    preferences = Column(JSON, nullable=False, default={})
    
    # Общие настройки
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    push_subscriptions = Column(JSON, default=[])  # Web Push subscriptions
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="notification_preferences")
```

---

## API Endpoints

### Уведомления

```python
# Получить список уведомлений
GET /api/notifications?status=unread&type=shift&limit=20&offset=0
Response: {
    "total": 42,
    "unread_count": 15,
    "notifications": [
        {
            "id": 1,
            "type": "shift",
            "title": "Напоминание о смене",
            "message": "Смена начинается через 2 часа",
            "created_at": "2025-10-09T10:00:00Z",
            "is_read": false,
            "priority": "high"
        }
    ]
}

# Получить количество непрочитанных
GET /api/notifications/unread/count
Response: {"count": 15}

# Отметить как прочитанное
POST /api/notifications/{id}/read
Response: {"success": true}

# Отметить все как прочитанные
POST /api/notifications/read-all
Response: {"success": true, "marked": 15}

# Удалить уведомление
DELETE /api/notifications/{id}
Response: {"success": true}
```

### Настройки уведомлений

```python
# Получить настройки
GET /api/notifications/preferences
Response: {
    "shift": {
        "enabled": true,
        "channels": ["email", "telegram"],
        "frequency": "instant"
    },
    "contract": {
        "enabled": true,
        "channels": ["email"],
        "frequency": "instant"
    },
    ...
}

# Обновить настройки
POST /api/notifications/preferences
Body: {
    "shift": {
        "enabled": true,
        "channels": ["email", "telegram", "push"],
        "frequency": "instant"
    }
}
Response: {"success": true}

# Подписаться на Push
POST /api/notifications/push/subscribe
Body: {
    "endpoint": "https://...",
    "keys": {...}
}
Response: {"success": true}

# Отписаться от Push
POST /api/notifications/push/unsubscribe
Body: {"endpoint": "https://..."}
Response: {"success": true}
```

### Админка

```python
# Статистика
GET /admin/notifications/analytics?date_from=2025-10-01&date_to=2025-10-09
Response: {
    "total_sent": 1524,
    "by_channel": {
        "email": 824,
        "telegram": 600,
        "sms": 50,
        "push": 50
    },
    "delivery_rate": 0.95,
    "read_rate": 0.72,
    "error_rate": 0.05
}

# Отправить тестовое уведомление
POST /admin/notifications/test
Body: {
    "user_id": 123,
    "type": "shift",
    "channel": "email"
}
Response: {"success": true, "notification_id": 9999}
```

---

## Использование в коде

### Создание уведомления

```python
from shared.services.notification_service import NotificationService
from domain.entities.notification import NotificationType, NotificationChannel

# В роутах/сервисах
notification_service = NotificationService(session)

# Простое уведомление
await notification_service.create_notification(
    user_id=user.id,
    type=NotificationType.SHIFT,
    channel=NotificationChannel.TELEGRAM,
    title="Напоминание о смене",
    message="Смена начинается через 2 часа на объекте {object_name}",
    data={"object_id": 1, "shift_id": 42}
)

# Запланированное уведомление
from datetime import datetime, timedelta

await notification_service.create_notification(
    user_id=user.id,
    type=NotificationType.CONTRACT,
    channel=NotificationChannel.EMAIL,
    title="Договор истекает",
    message="Ваш договор истекает через 7 дней",
    scheduled_at=datetime.now() + timedelta(days=7)
)

# Использование шаблона
from shared.templates.notifications.base_templates import NotificationTemplateManager

template_manager = NotificationTemplateManager()
rendered = template_manager.render(
    template_name="shift_reminder",
    channel=NotificationChannel.EMAIL,
    user_name="Иван Иванов",
    object_name="Офис А",
    shift_time="14:00-22:00"
)

await notification_service.create_notification(
    user_id=user.id,
    type=NotificationType.SHIFT,
    channel=NotificationChannel.EMAIL,
    title=rendered["title"],
    message=rendered["message"]
)
```

### Проверка настроек пользователя

```python
# Сервис автоматически проверяет настройки перед отправкой
# Если канал отключен - уведомление не отправляется

# Получить настройки
preferences = await notification_service.get_user_preferences(user_id)

# Проверить, включен ли тип
if preferences.is_enabled(NotificationType.SHIFT):
    # Получить каналы
    channels = preferences.get_channels(NotificationType.SHIFT)
    # ["email", "telegram"]
```

### Отправка дайджеста

```python
from core.celery.tasks.notification_scheduler import send_daily_digests

# Celery задача (автоматически)
send_daily_digests.delay()

# Или вручную
await notification_service.create_and_send_digest(
    user_id=user.id,
    period="daily"  # hourly, daily
)
```

---

## Конфигурация каналов

### Email (SMTP)

```python
# .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@staffprobot.ru
SMTP_PASSWORD=app_specific_password
SMTP_FROM=StaffProBot <notifications@staffprobot.ru>
SMTP_TLS=true

# Для Gmail: включить "App Passwords"
# Для других: проверить настройки SMTP
```

### SMS (Twilio)

```python
# .env
SMS_PROVIDER=twilio  # twilio, smsc, smsaero
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=***
TWILIO_PHONE_NUMBER=+79991234567

# Альтернатива: SMSC.ru
SMSC_LOGIN=your_login
SMSC_PASSWORD=***
SMSC_SENDER=StaffProBot
```

### Push (Web Push)

```python
# Генерация VAPID ключей:
# pip install pywebpush
# python -c "from pywebpush import webpush; print(webpush.generate_vapid_keys())"

# .env
VAPID_PUBLIC_KEY=BD...
VAPID_PRIVATE_KEY=***
VAPID_SUBJECT=mailto:admin@staffprobot.ru
```

### Telegram (уже настроен)

```python
# .env
TELEGRAM_BOT_TOKEN=123456:ABC...
```

---

## Celery задачи

### Планировщик

```python
# core/celery/tasks/notification_scheduler.py

@celery_app.task
def process_scheduled_notifications():
    """Отправка запланированных уведомлений (каждые 5 минут)."""
    # Найти все уведомления с scheduled_at <= now и status = pending
    # Отправить через соответствующий канал
    # Обновить status на sent/failed
    pass

@celery_app.task
def send_hourly_digests():
    """Отправка часовых дайджестов (каждый час)."""
    # Найти пользователей с frequency = hourly_digest
    # Собрать уведомления за последний час
    # Отправить дайджест
    pass

@celery_app.task
def send_daily_digests():
    """Отправка ежедневных дайджестов (каждый день в 9:00)."""
    # Найти пользователей с frequency = daily_digest
    # Собрать уведомления за последний день
    # Отправить дайджест
    pass

@celery_app.task
def cleanup_old_notifications():
    """Очистка старых прочитанных уведомлений (раз в неделю)."""
    # Удалить read_at < 30 дней назад
    pass
```

### Beat расписание

```python
# core/celery/celery_app.py

app.conf.beat_schedule = {
    'process-scheduled-notifications': {
        'task': 'core.celery.tasks.notification_scheduler.process_scheduled_notifications',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут
    },
    'send-hourly-digests': {
        'task': 'core.celery.tasks.notification_scheduler.send_hourly_digests',
        'schedule': crontab(minute=0),  # Каждый час
    },
    'send-daily-digests': {
        'task': 'core.celery.tasks.notification_scheduler.send_daily_digests',
        'schedule': crontab(hour=9, minute=0),  # Каждый день в 9:00
    },
    'cleanup-old-notifications': {
        'task': 'core.celery.tasks.notification_scheduler.cleanup_old_notifications',
        'schedule': crontab(day_of_week=1, hour=3, minute=0),  # Понедельник в 3:00
    },
}
```

---

## Тестирование

### Unit тесты

```python
# tests/unit/test_notification_service.py

import pytest
from shared.services.notification_service import NotificationService

@pytest.mark.asyncio
async def test_create_notification(session, test_user):
    service = NotificationService(session)
    
    notification = await service.create_notification(
        user_id=test_user.id,
        type=NotificationType.SHIFT,
        channel=NotificationChannel.EMAIL,
        title="Test",
        message="Test message"
    )
    
    assert notification.id is not None
    assert notification.status == NotificationStatus.PENDING

@pytest.mark.asyncio
async def test_mark_as_read(session, test_notification):
    service = NotificationService(session)
    
    success = await service.mark_as_read(test_notification.id)
    
    assert success
    assert test_notification.read_at is not None
```

### Integration тесты

```python
# tests/integration/test_notification_flow.py

@pytest.mark.asyncio
async def test_full_notification_flow(session, test_user, mock_email):
    """Тест полного цикла: создание → планирование → отправка → чтение."""
    service = NotificationService(session)
    
    # 1. Создание
    notification = await service.create_notification(
        user_id=test_user.id,
        type=NotificationType.SHIFT,
        channel=NotificationChannel.EMAIL,
        title="Test",
        message="Test message",
        scheduled_at=datetime.now() + timedelta(minutes=1)
    )
    
    # 2. Проверка запланированности
    assert notification.is_scheduled()
    
    # 3. Эмуляция отправки планировщиком
    from core.celery.tasks.notification_scheduler import process_scheduled_notifications
    process_scheduled_notifications()
    
    # 4. Проверка отправки
    await session.refresh(notification)
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    
    # 5. Отметка как прочитанное
    await service.mark_as_read(notification.id)
    await session.refresh(notification)
    assert notification.read_at is not None
```

---

## Безопасность

### Rate Limiting

```python
from core.utils.notification_rate_limiter import NotificationRateLimiter

limiter = NotificationRateLimiter()

# Проверка лимита перед отправкой
if not await limiter.check_limit(user_id, notification_type):
    logger.warning(f"Rate limit exceeded for user {user_id}")
    return False

# Лимиты:
# - 10 уведомлений/час на пользователя (обычные)
# - Без лимита для urgent уведомлений
```

### Валидация данных

```python
# Email
from email_validator import validate_email

def validate_email_address(email: str) -> bool:
    try:
        validate_email(email)
        return True
    except:
        return False

# Телефон
import phonenumbers

def validate_phone_number(phone: str) -> bool:
    try:
        parsed = phonenumbers.parse(phone, "RU")
        return phonenumbers.is_valid_number(parsed)
    except:
        return False
```

### Отписка от email

```python
# Генерация токена
import hashlib
import hmac

def generate_unsubscribe_token(user_id: int, secret: str) -> str:
    data = f"{user_id}:{secret}"
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()

# В email шаблоне
unsubscribe_url = f"https://staffprobot.ru/unsubscribe/{token}"
```

---

## Мониторинг

### Метрики Prometheus

```python
from prometheus_client import Counter, Histogram

notifications_sent = Counter(
    'notifications_sent_total',
    'Total notifications sent',
    ['channel', 'type', 'status']
)

notification_duration = Histogram(
    'notification_send_duration_seconds',
    'Time to send notification',
    ['channel']
)

# Использование
with notification_duration.labels(channel='email').time():
    await email_channel.send(notification)
    notifications_sent.labels(channel='email', type='shift', status='sent').inc()
```

### Логирование

```python
from core.logging.logger import logger

# При отправке
logger.info(
    "Notification sent",
    notification_id=notification.id,
    user_id=user_id,
    channel=channel.value,
    type=notification_type.value,
    duration_ms=duration
)

# При ошибке
logger.error(
    "Failed to send notification",
    notification_id=notification.id,
    channel=channel.value,
    error=str(e)
)
```

---

## Оптимизация

### Кэширование

```python
from core.cache.redis_cache import cached

class NotificationService:
    @cached(key_prefix="user_notifications", ttl=300)  # 5 минут
    async def get_user_notifications(self, user_id: int, filters: dict):
        # Запрос к БД
        pass
    
    @cached(key_prefix="unread_count", ttl=60)  # 1 минута
    async def get_unread_count(self, user_id: int):
        # Запрос к БД
        pass
```

### Batch отправка

```python
# Для email
async def send_batch_emails(notifications: List[Notification]):
    """Отправка пачки email за один SMTP connection."""
    async with EmailChannel() as channel:
        for notification in notifications:
            await channel.send(notification)
```

---

## Миграция

### Этапы

1. **Создать новые таблицы** (Alembic миграция)
2. **Восстановить NotificationService** (удалить заглушки)
3. **Интегрировать каналы** (Email → SMS → Push)
4. **Мигрировать существующие уведомления** (из старой таблицы)
5. **Переключить код** (использовать новый сервис)
6. **Удалить старую таблицу** (после проверки)

### Обратная совместимость

```python
# Старый код продолжает работать через адаптер
class LegacyNotificationAdapter:
    """Адаптер для старого кода."""
    
    def __init__(self, new_service: NotificationService):
        self.service = new_service
    
    def create_notification(self, user_id, type, payload):
        # Маппинг на новый формат
        return self.service.create_notification(
            user_id=user_id,
            type=NotificationType(type),
            channel=NotificationChannel.TELEGRAM,  # default
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            data=payload
        )
```

---

## Дополнительные материалы

- [RFC 5322](https://datatracker.ietf.org/doc/html/rfc5322) - Email формат
- [Web Push Protocol](https://datatracker.ietf.org/doc/html/rfc8030)
- [Twilio API Docs](https://www.twilio.com/docs/sms)
- [PyWebPush](https://github.com/web-push-libs/pywebpush)


