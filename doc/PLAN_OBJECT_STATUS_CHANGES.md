# План изменений: Статус работы объектов на основе событий от бота

## Текущая ситуация

1. **Бот управляет ObjectOpening:**
   - При открытии смены: если объект закрыт → открывает через `ObjectOpeningService.open_object()`
   - При закрытии последней смены: закрывает объект через `ObjectOpeningService.close_object()`

2. **Дашборд владельца:**
   - Анализирует смены на сегодня и вычисляет статус по времени открытия/закрытия
   - Сравнивает с `opening_time`/`closing_time` объекта

3. **Уведомления:**
   - Типы уже есть: `OBJECT_OPENED`, `OBJECT_CLOSED`, `OBJECT_LATE_OPENING`, `OBJECT_EARLY_CLOSING`, `OBJECT_NO_SHIFTS_TODAY`
   - Но не отправляются при открытии/закрытии объекта

## Предлагаемые изменения

### 1. Обновить ObjectOpeningService

**Добавить методы:**

```python
async def check_and_notify_opening_status(
    self,
    opening: ObjectOpening,
    object: Object
) -> Dict[str, Any]:
    """Проверить статус открытия объекта и отправить уведомление.
    
    Проверяет:
    - Вовремя ли открылся объект (opened_at vs opening_time + threshold)
    - Отправляет уведомление: OBJECT_OPENED или OBJECT_LATE_OPENING
    """
    # 1. Получить настройки опоздания (с учетом наследования org_unit)
    # 2. Сравнить opened_at с opening_time + threshold
    # 3. Создать уведомление
    # 4. Вернуть статус: {'status': 'timely_opening' | 'late_opening', 'delay_minutes': int}

async def check_and_notify_closing_status(
    self,
    opening: ObjectOpening,
    object: Object
) -> Dict[str, Any]:
    """Проверить статус закрытия объекта и отправить уведомление.
    
    Проверяет:
    - Вовремя ли закрылся объект (closed_at vs closing_time)
    - Отправляет уведомление: OBJECT_CLOSED или OBJECT_EARLY_CLOSING
    """
    # 1. Сравнить closed_at с closing_time
    # 2. Создать уведомление
    # 3. Вернуть статус: {'status': 'closed' | 'early_closing', 'early_minutes': int}
```

### 2. Обновить бот (ShiftService)

**При открытии смены (`open_shift`):**

После строки 121 (после `opening_service.open_object()`):
```python
# Проверяем статус открытия и отправляем уведомление
opening_result = await opening_service.open_object(...)
if opening_result:
    # Загружаем объект с настройками
    obj = await self._get_object(session, object_id)
    status_result = await opening_service.check_and_notify_opening_status(
        opening_result,
        obj
    )
    logger.info(
        f"Object opening status checked",
        object_id=object_id,
        status=status_result.get('status'),
        delay_minutes=status_result.get('delay_minutes')
    )
```

**При закрытии последней смены:**

В `core_handlers.py` после закрытия объекта (строка ~396):
```python
# Проверяем статус закрытия и отправляем уведомление
obj = await self._get_object(session, closed_shift_object_id)
status_result = await opening_service.check_and_notify_closing_status(
    opening,
    obj
)
logger.info(
    f"Object closing status checked",
    object_id=closed_shift_object_id,
    status=status_result.get('status'),
    early_minutes=status_result.get('early_minutes')
)
```

### 3. Обновить дашборд владельца (`apps/web/routes/owner.py`)

**Использовать ObjectOpening вместо анализа смен:**

```python
# Вместо анализа смен (строки 212-346):
# 1. Получить последнее ObjectOpening для объекта
last_opening = await session.execute(
    select(ObjectOpening)
    .where(ObjectOpening.object_id == obj.id)
    .order_by(desc(ObjectOpening.opened_at))
    .limit(1)
)

# 2. Если объект открыт (closed_at IS NULL):
if last_opening and last_opening.closed_at is None:
    # Проверить статус открытия (используя opened_at и настройки объекта)
    # Уже проверено при открытии, можем взять из последнего уведомления или пересчитать
    work_status = 'timely_opening' | 'late_opening'
    work_employee = last_opening.opener.first_name + " " + last_opening.opener.last_name

# 3. Если объект закрыт (closed_at IS NOT NULL):
if last_opening and last_opening.closed_at:
    # Проверить статус закрытия
    # Уже проверено при закрытии, можем взять из последнего уведомления или пересчитать
    work_status = 'closed' | 'early_closing'
    work_employee = last_opening.closer.first_name + " " + last_opening.closer.last_name
```

**Альтернативный подход (проще):**
- Сохранять статус в отдельное поле `ObjectOpening.work_status` при создании/обновлении
- Или использовать последнее уведомление типа `OBJECT_*` для объекта

### 4. Обновить auto_close_shifts (`core/celery/tasks/shift_tasks.py`)

**Добавить проверку "Нет смен на объекте":**

После закрытия ObjectOpening (строка ~443):

```python
# Проверка "Нет смен на объекте"
for object_id in closed_object_ids:
    active_count = await opening_service.get_active_shifts_count(object_id)
    
    if active_count == 0:
        # Закрываем ObjectOpening
        opening = await opening_service.get_active_opening(object_id)
        if opening:
            opening.closed_at = now_utc.replace(tzinfo=None)
            opening.closed_by = None
            closed_openings_count += 1
            logger.info(f"Auto-closed ObjectOpening {opening.id} for object {object_id}")
        
        # НОВОЕ: Проверяем, в пределах ли графика работы объекта
        obj_query = select(Object).where(Object.id == object_id)
        obj_result = await session.execute(obj_query)
        obj = obj_result.scalar_one_or_none()
        
        if obj and obj.opening_time and obj.closing_time:
            # Определяем локальное время
            obj_timezone = obj.timezone or "Europe/Moscow"
            obj_tz = pytz.timezone(obj_timezone)
            now_local = now_utc.astimezone(obj_tz)
            current_time = now_local.time()
            
            # Проверяем, в пределах ли графика работы
            if obj.opening_time <= current_time <= obj.closing_time:
                # Отправляем уведомление OBJECT_NO_SHIFTS_TODAY
                from domain.entities.notification import Notification, NotificationType
                from domain.entities.user import User
                
                owner_query = select(User).where(User.id == obj.owner_id)
                owner_result = await session.execute(owner_query)
                owner = owner_result.scalar_one_or_none()
                
                if owner:
                    notification = Notification(
                        user_id=owner.id,
                        type_code=NotificationType.OBJECT_NO_SHIFTS_TODAY,
                        status='pending',
                        priority='normal',
                        data={
                            'object_id': object_id,
                            'object_name': obj.name,
                            'checked_at': now_utc.isoformat()
                        }
                    )
                    session.add(notification)
                    logger.info(
                        f"Created OBJECT_NO_SHIFTS_TODAY notification",
                        object_id=object_id,
                        owner_id=owner.id
                    )
```

### 5. Создать сервис для уведомлений об объектах

**Новый файл: `apps/web/services/object_notification_service.py`:**

```python
class ObjectNotificationService:
    """Сервис для отправки уведомлений об объектах."""
    
    async def notify_object_opened(
        self,
        session: AsyncSession,
        opening: ObjectOpening,
        object: Object,
        is_late: bool,
        delay_minutes: int
    ) -> Notification:
        """Отправить уведомление об открытии объекта."""
        # Определить тип уведомления
        notification_type = NotificationType.OBJECT_LATE_OPENING if is_late else NotificationType.OBJECT_OPENED
        
        # Получить владельца объекта
        owner = await self._get_owner(session, object.owner_id)
        
        # Создать уведомление
        notification = Notification(
            user_id=owner.id,
            type_code=notification_type,
            status='pending',
            priority='normal' if not is_late else 'high',
            data={
                'object_id': object.id,
                'object_name': object.name,
                'opened_at': opening.opened_at.isoformat(),
                'delay_minutes': delay_minutes if is_late else 0
            }
        )
        session.add(notification)
        return notification
    
    async def notify_object_closed(
        self,
        session: AsyncSession,
        opening: ObjectOpening,
        object: Object,
        is_early: bool,
        early_minutes: int
    ) -> Notification:
        """Отправить уведомление о закрытии объекта."""
        # Аналогично notify_object_opened
```

## Порядок реализации

1. **Этап 1: ObjectOpeningService** (0.3 дня)
   - Добавить методы `check_and_notify_opening_status` и `check_and_notify_closing_status`
   - Интегрировать с ObjectNotificationService

2. **Этап 2: Бот** (0.2 дня)
   - Обновить `ShiftService.open_shift` - вызывать проверку при открытии
   - Обновить `core_handlers.py` - вызывать проверку при закрытии

3. **Этап 3: Дашборд** (0.3 дня)
   - Переделать логику вычисления статуса - использовать ObjectOpening
   - Упростить код (не нужно анализировать смены)

4. **Этап 4: auto_close_shifts** (0.2 дня)
   - Добавить проверку "Нет смен на объекте"
   - Отправлять уведомления только в пределах графика работы

5. **Этап 5: Тестирование** (0.2 дня)
   - Проверить уведомления при открытии/закрытии
   - Проверить дашборд владельца
   - Проверить уведомление "Нет смен на объекте"

## Вопросы для обсуждения

1. **Сохранять ли статус в ObjectOpening?**
   - Вариант А: Сохранять `work_status`, `work_delay`, `work_early` в `ObjectOpening`
   - Вариант Б: Использовать последнее уведомление для получения статуса
   - Вариант В: Пересчитывать при запросе дашборда (текущий подход, но на основе ObjectOpening)

2. **Уведомление "Нет смен на объекте":**
   - Отправлять каждый раз при запуске задачи или только один раз за день?
   - По логике пользователя: "столько раз, сколько будет запускаться задача пока на объекте не появится активная смена"

3. **Порог раннего закрытия:**
   - Сейчас хардкод: 5 минут
   - Вынести в настройки объекта?





