# Автоматизация в StaffProBot

## 🤖 Система автоматических задач

StaffProBot использует **Celery** для выполнения фоновых задач и автоматизации рутинных процессов.

## 📋 Реализованные автоматические задачи

### 1. Автоматическое закрытие смен

**Задача**: `auto_close_shifts`  
**Расписание**: Каждый день в 00:00  
**Файл**: `core/celery/tasks/shift_tasks.py`

#### Логика работы:
1. Находит все активные смены, которые начались вчера
2. Определяет время закрытия по приоритету:
   - **Приоритет 1**: Время из тайм-слота (если есть)
   - **Приоритет 2**: Время закрытия объекта
   - **Приоритет 3**: Полночь (00:00)
3. **Учитывает часовой пояс объекта** - время закрытия конвертируется в UTC
4. Закрывает смену с флагом `auto_closed = True`
5. Рассчитывает общее время и оплату

#### Пример лога:
```
Auto-closed 0 shifts at midnight
Auto-close completed: 0 shifts closed
```

### 2. Автоматическое создание тайм-слотов на следующий год

**Задача**: `plan_next_year_timeslots`  
**Расписание**: 1 декабря в 03:00  
**Файл**: `core/celery/tasks/shift_tasks.py`

#### Логика работы:
1. Получает все активные объекты
2. Для каждого объекта создает тайм-слоты на весь следующий год
3. Учитывает:
   - `work_days_mask` - дни недели работы
   - `schedule_repeat_weeks` - периодичность повторения
   - `opening_time` и `closing_time` - время работы
   - `hourly_rate` - ставка оплаты
4. Пропускает уже существующие тайм-слоты

#### Пример результата:
```
Planned next year timeslots: created=1722
```

## 🌍 Система часовых поясов

### Автоматическая конвертация времени

Все автоматические задачи учитывают часовой пояс объекта:

- **Автоматическое закрытие смен** - время закрытия конвертируется в UTC с учетом часового пояса объекта
- **Создание тайм-слотов** - время работы объекта учитывается в локальном часовом поясе
- **Отображение времени** - в веб-интерфейсе время показывается в часовом поясе объекта

### Поддерживаемые часовые пояса

| Часовой пояс | UTC смещение | Описание |
|--------------|--------------|----------|
| Europe/Moscow | UTC+3 | Москва (по умолчанию) |
| Europe/London | UTC+0/+1 | Лондон |
| America/New_York | UTC-5/-4 | Нью-Йорк |
| America/Los_Angeles | UTC-8/-7 | Лос-Анджелес |
| Asia/Tokyo | UTC+9 | Токио |
| Asia/Shanghai | UTC+8 | Шанхай |
| Australia/Sydney | UTC+10/+11 | Сидней |

### Техническая реализация

- **WebTimezoneHelper** - конвертация времени в веб-интерфейсе
- **TimezoneHelper** - конвертация времени в боте
- **Поле timezone** - в модели Object
- **Автоматическая конвертация** - во всех местах отображения

## ⚙️ Конфигурация Celery

### Сервисы:
- **Celery Worker** - выполняет задачи
- **Celery Beat** - планировщик задач
- **RabbitMQ** - брокер сообщений
- **Redis** - хранилище результатов

### Расписание задач:
```python
beat_schedule={
    'auto-close-shifts': {
        'task': 'core.celery.tasks.shift_tasks.auto_close_shifts',
        'schedule': crontab(hour=0, minute=0),  # каждый день в 00:00
    },
    'plan-next-year-timeslots': {
        'task': 'core.celery.tasks.shift_tasks.plan_next_year_timeslots',
        'schedule': crontab(hour=3, minute=0, day_of_month=1, month_of_year=12),  # 1 декабря в 03:00
    },
}
```

## 🔧 Управление задачами

### Запуск задач вручную:
```bash
# Автоматическое закрытие смен
docker compose -f docker-compose.dev.yml exec celery_worker celery -A core.celery.celery_app call core.celery.tasks.shift_tasks.auto_close_shifts

# Создание тайм-слотов на следующий год
docker compose -f docker-compose.dev.yml exec celery_worker celery -A core.celery.celery_app call core.celery.tasks.shift_tasks.plan_next_year_timeslots
```

### Проверка статуса:
```bash
# Активные задачи
docker compose -f docker-compose.dev.yml exec celery_worker celery -A core.celery.celery_app inspect active

# Статистика
docker compose -f docker-compose.dev.yml exec celery_worker celery -A core.celery.celery_app inspect stats
```

### Логи:
```bash
# Логи worker'а
docker compose -f docker-compose.dev.yml logs celery_worker --tail=20

# Логи планировщика
docker compose -f docker-compose.dev.yml logs celery_beat --tail=20
```

## 📊 Мониторинг

### Логирование:
- Все задачи логируются с контекстом
- Указывается количество обработанных элементов
- Ошибки записываются с детальной информацией

### Метрики:
- Время выполнения задач
- Количество успешных/неудачных выполнений
- Статистика использования ресурсов

## 🚀 Развертывание

### Development:
```bash
docker compose -f docker-compose.dev.yml up -d
```

### Production:
```bash
docker compose -f docker-compose.prod.yml up -d
```

## 🔍 Отладка

### Проблемы с БД:
- Убедитесь, что используется `get_async_session()` вместо `DatabaseManager`
- Проверьте подключение к PostgreSQL

### Проблемы с планировщиком:
- Проверьте, что Celery Beat запущен
- Убедитесь, что pidfile не блокирует запуск

### Проблемы с задачами:
- Проверьте логи worker'а
- Убедитесь, что все импорты корректны
- Проверьте подключение к RabbitMQ

## 📝 Добавление новых задач

1. Создайте функцию в `core/celery/tasks/`
2. Добавьте расписание в `celery_app.py`
3. Протестируйте задачу вручную
4. Добавьте документацию

Пример:
```python
@celery_app.task(base=ShiftTask, bind=True)
def my_automation_task(self):
    """Описание задачи."""
    try:
        # Логика задачи
        return result
    except Exception as e:
        logger.error(f"Error in my_automation_task: {e}")
        return 0
```
