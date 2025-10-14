# Система отмены смен с учетом ответственности

## Обзор

Система учета отмены запланированных смен с модерацией всех отмен сотрудниками, расчетом штрафов после модерации и интеграцией с начислениями зарплаты.

**Обновлено:** 14.10.2025 - Изменена логика начисления штрафов (только после модерации), добавлен запрос фото, временные зоны в боте.

## Основные компоненты

### 1. База данных

#### Таблица `shift_cancellations`

Хранит полную информацию о каждой отмене смены:

- **Основные поля:**
  - `shift_schedule_id` - ссылка на запланированную смену
  - `employee_id` - сотрудник, чья смена отменена
  - `object_id` - объект, на котором была смена
  
- **Информация об отмене:**
  - `cancelled_by_id` - кто отменил (user_id)
  - `cancelled_by_type` - тип отменившего (employee/owner/manager/system)
  - `cancellation_reason` - причина отмены
  - `reason_notes` - дополнительные заметки
  - `hours_before_shift` - за сколько часов до смены была отмена
  
- **Уважительные причины (справки):**
  - `document_description` - описание документа (номер, дата)
  - `document_verified` - подтверждена ли справка
  - `verified_by_id`, `verified_at` - кто и когда проверил
  
- **Штрафы:**
  - `fine_amount` - сумма штрафа
  - `fine_reason` - причина штрафа (short_notice/invalid_reason)
  - `fine_applied` - применен ли к расчетному листу
  - `payroll_adjustment_id` - ссылка на корректировку
  
- **Контекст:**
  - `contract_id` - договор на момент отмены

### 2. Настройки штрафов

#### Поля в Object и OrgStructureUnit:

- `inherit_cancellation_settings` - наследовать от подразделения
- `cancellation_short_notice_hours` - минимальный срок отмены (часов)
- `cancellation_short_notice_fine` - штраф за короткий срок (₽)
- `cancellation_invalid_reason_fine` - штраф за неуважительную причину (₽)

#### Методы:

- `object.get_cancellation_settings()` - получить настройки с учетом наследования
- `org_unit.get_inherited_cancellation_settings()` - получить настройки подразделения

#### Логика наследования:

1. Если `inherit_cancellation_settings = False` и заданы локальные значения → использовать локальные
2. Иначе получить от родительского подразделения (рекурсивно)
3. По умолчанию: 24 часа, без штрафов

## Типы причин отмены

### Причины (`cancellation_reason`):

- **`short_notice`** - отмена в короткий срок (< X часов)
- **`no_reason`** - отмена без указания причины
- **`medical_cert`** ✅ - медицинская справка (уважительная, требует модерации)
- **`emergency_cert`** ✅ - справка от МЧС (уважительная, требует модерации)
- **`police_cert`** ✅ - справка от полиции (уважительная, требует модерации)
- **`owner_decision`** - решение владельца/управляющего
- **`contract_termination`** - автоматическая отмена при расторжении договора
- **`other`** - другая причина

### Типы отменивших (`cancelled_by_type`):

- **`employee`** - сотрудник отменил через бота
- **`owner`** - владелец отменил через веб
- **`manager`** - управляющий отменил через веб
- **`system`** - система (при расторжении договора)

## Логика работы

### 1. Отмена сотрудником через бота

**Процесс:**
1. Сотрудник открывает "Мои планы" (отображаются только будущие смены)
2. Выбирает смену для отмены
3. Система показывает кнопки выбора причины:
   - 🏥 Медицинская справка
   - 🚨 Справка от МЧС
   - 👮 Справка от полиции
   - ❓ Другая причина
4. **Для справок (1-3):**
   - Запрос описания документа (номер, дата)
   - Запрос фото (если есть `telegram_report_chat_id` у объекта/подразделения)
   - Фото отправляется в группу ТГ
   - Кнопка "⏩ Пропустить" для пропуска фото
5. **Для "Другая причина":**
   - Запрос текстового объяснения
   - Запрос фото (опционально, если есть `telegram_report_chat_id`)
   - Фото отправляется в группу ТГ
6. Расчет `hours_before_shift` (может быть отрицательным для уже начавшихся смен)
7. Создание записи `ShiftCancellation` **БЕЗ штрафов** (все отмены идут на модерацию)
8. Смена переводится в статус `cancelled`
9. Сотрудник получает уведомление: "Смена отменена, ожидает модерации"
10. Время отображается в timezone пользователя (по умолчанию Europe/Moscow)

**Файлы:**
- `apps/bot/handlers_div/schedule_handlers.py` - обработчики бота
- `apps/bot/handlers_div/shift_handlers.py` - обработка фото
- `apps/bot/handlers_div/utility_handlers.py` - роутинг текстовых сообщений
- `shared/services/shift_cancellation_service.py` - логика отмены
- `core/state/user_state_manager.py` - состояния (INPUT_DOCUMENT, INPUT_PHOTO)
- `core/utils/timezone_helper.py` - конвертация времени

### 2. Отмена владельцем/управляющим через веб

**Процесс:**
1. Владелец/управляющий открывает страницу смен (`/owner/shifts` или `/manager/shifts`)
2. Нажимает "Отменить смену" в списке или на странице детальной информации
3. В модальном окне:
   - Выбирает причину (обязательно):
     - Решение владельца
     - Изменение расписания
     - Просьба сотрудника
     - Другая причина
   - Добавляет примечание (опционально)
4. Система создает `ShiftCancellation` с `cancelled_by_type = 'owner'/'manager'`
5. Штрафы НЕ начисляются (отмена по инициативе руководства)
6. Смена переводится в статус `cancelled`

**Endpoints:**
- `POST /owner/shifts/schedule/{schedule_id}/cancel` (Form: reason, notes)
- `POST /manager/shifts/schedule/{schedule_id}/cancel` (Form: reason, notes)

**Файлы:**
- `apps/web/routes/cancellations.py` - роуты отмены
- `apps/web/templates/owner/shifts/list.html` - модал отмены
- `apps/web/templates/owner/shifts/detail.html` - модал отмены
- `apps/web/templates/manager/shifts/list.html` - модал отмены
- `apps/web/templates/manager/shifts/detail.html` - модал отмены (дублирующая кнопка удалена)

### 3. Автоотмена при расторжении договора

**Процесс:**
1. При расторжении договора через `ContractService.terminate_contract_by_telegram_id()`
2. Получение всех активных договоров сотрудника (кроме расторгаемого)
3. Вычисление `lost_objects = terminated_contract.allowed_objects - remaining_objects`
4. Поиск запланированных смен на `lost_objects` с `planned_start > now()`
5. Для каждой смены:
   - `status = 'cancelled'`
   - Создание `ShiftCancellation`:
     - `cancelled_by_type = 'system'`
     - `cancellation_reason = 'contract_termination'`
     - `reason_notes = "Расторгнут договор №XXX. Причина: ..."`
     - Без штрафов

**Файлы:**
- `apps/web/services/contract_service.py::_cancel_shifts_on_contract_termination()`

### 4. Модерация отмен

**Процесс:**
1. Владелец открывает `/owner/cancellations`
2. Видит список **ВСЕХ** отмен сотрудниками (`cancelled_by_type = 'employee'`)
3. Для каждой отмены:
   - Информация: сотрудник, объект, дата/время, причина
   - Если есть объяснение (`reason_notes`) - отображается
   - Если есть описание документа (`document_description`) - отображается
   - Статус верификации
   - Кнопки "✅ Подтвердить" / "❌ Отклонить"
4. **При подтверждении:**
   - `document_verified = True`
   - Штрафы НЕ начисляются
5. **При отклонении:**
   - `document_verified = False`
   - Получение настроек штрафов через `object.get_cancellation_settings()` (с учетом наследования)
   - Создание **ДВУХ** отдельных штрафов (если применимы):
     - **Штраф 1:** Короткий срок (`cancellation_fine_short_notice`)
       - Если `hours_before_shift < short_notice_hours`
       - Сумма: `short_notice_fine` (например, 1000₽)
       - Описание: "Штраф за отмену смены менее чем за Xч"
     - **Штраф 2:** Недействительная причина (`cancellation_fine_invalid_reason`)
       - Сумма: `invalid_reason_fine` (например, 2000₽)
       - Описание: "Штраф за отмену смены без уважительной причины"
       - Для "Другая причина" + объяснение: "...без уважительной причины. Объяснение: {текст}"
   - Оба штрафа создаются как отдельные записи в `payroll_adjustments`
   - В таблице начислений тип отображается как "Штраф за отмену смены"
   - Детали в столбце "Описание"
   - Обновление `cancellation.fine_amount = total`, `fine_reason = 'both'/'short_notice'/'invalid_reason'`

**Endpoints:**
- `GET /owner/cancellations` - список для модерации
- `POST /owner/cancellations/{cancellation_id}/verify` - верификация

**Файлы:**
- `apps/web/routes/cancellations.py`
- `apps/web/templates/owner/cancellations/list.html`

## Интеграция с начислениями

### PayrollAdjustment типы:

- `cancellation_fine` - общий штраф за отмену
- `cancellation_fine_short_notice` - штраф за отмену менее чем за X часов
- `cancellation_fine_invalid_reason` - штраф за неуважительную причину

### Структура корректировки:

```python
{
    "adjustment_type": "cancellation_fine_short_notice",
    "amount": -500.00,  # Отрицательная сумма (вычет)
    "description": "Штраф за отмену смены менее чем за 12ч",
    "details": {
        "cancellation_id": 123,
        "shift_schedule_id": 456,
        "cancellation_reason": "short_notice",
        "hours_before_shift": 12.5,
        "planned_start": "2025-10-15T09:00:00"
    }
}
```

## Аналитика

### GET /owner/analytics/cancellations

**Показатели:**
- Всего отмен за период
- Сумма штрафов (начислено/применено)
- Процент уважительных причин
- Распределение по типам отменивших
- Распределение по причинам
- Топ-10 сотрудников по количеству отмен
- Детальная таблица всех отмен

**Фильтры:**
- Период (date_from, date_to)
- Объект
- Сотрудник

## API Reference

### ShiftCancellationService

#### `cancel_shift()`
```python
async def cancel_shift(
    shift_schedule_id: int,
    cancelled_by_user_id: int,
    cancelled_by_type: str,
    cancellation_reason: str,
    reason_notes: Optional[str] = None,
    document_description: Optional[str] = None,
    contract_id: Optional[int] = None
) -> Dict[str, Any]
```

**Возвращает:**
```python
{
    'success': bool,
    'cancellation_id': int or None,
    'fine_amount': Decimal or None,
    'message': str
}
```

#### `verify_cancellation_document()`
```python
async def verify_cancellation_document(
    cancellation_id: int,
    verified_by_user_id: int,
    is_approved: bool
) -> Dict[str, Any]
```

## Миграции

### 1. `add_shift_cancellations_table.py`
Создает таблицу `shift_cancellations` со всеми индексами.

### 2. `add_cancellation_settings_fields.py`
Добавляет поля настроек штрафов за отмену в `objects` и `org_structure_units`.

## Использование

### Настройка штрафов для объекта

1. Открыть `/owner/objects/{id}/edit`
2. В секции "Штрафы за отмену смены":
   - Снять галочку "Наследовать от подразделения" (если нужны кастомные настройки)
   - Указать минимальный срок отмены (часов): `24`
   - Указать штраф за короткий срок: `500₽`
   - Указать штраф за неуважительную причину: `1000₽`
3. Сохранить

### Модерация справок

1. Открыть `/owner/cancellations`
2. Просмотреть список отмен с уважительными причинами
3. Для каждой справки:
   - Прочитать описание документа
   - Нажать "✅ Подтвердить" или "❌ Отклонить"
4. При подтверждении штраф автоматически снимается

### Просмотр аналитики

1. Открыть `/owner/analytics/cancellations`
2. Выбрать период и фильтры
3. Нажать "Применить"
4. Просмотреть статистику и детальный список
5. При необходимости - экспорт в Excel (TODO)

## TODO / Будущие улучшения

- ✅ Таблица shift_cancellations
- ✅ Настройки штрафов в Object/OrgStructureUnit
- ✅ Автоотмена при расторжении договора
- ✅ Отмена сотрудником через бота с выбором причины
- ✅ Отмена владельцем/управляющим через веб
- ✅ Модерация уважительных причин
- ✅ Интеграция с PayrollAdjustment
- ✅ Аналитика отмен
- ⏳ Уведомления в Telegram при отмене смены
- ⏳ Экспорт аналитики в Excel
- ⏳ Загрузка файлов справок (сейчас только текстовое описание)
- ⏳ Celery задача для напоминания о неподтвержденных справках (48ч)
- ⏳ Блокировка записи на смены при частых отменах без уважительных причин

## Примеры сценариев

### Сценарий 1: Сотрудник отменяет смену за 2 часа с медицинской справкой

1. Сотрудник в боте: "Мои смены" → выбирает смену → "Отменить"
2. Выбирает "🏥 Медицинская справка"
3. Вводит описание: "№123 от 13.10.2025"
4. **Результат:**
   - Смена отменена (`status = 'cancelled'`)
   - Создана запись `ShiftCancellation`:
     - `hours_before_shift = 2`
     - `cancellation_reason = 'medical_cert'`
     - `document_description = "№123 от 13.10.2025"`
   - Штраф начислен: 500₽ (короткий срок) + 1000₽ (неподтвержденная справка) = 1500₽
   - Сотрудник уведомлен: "Штраф 1500₽. Справка будет проверена владельцем"
   - Владелец уведомлен об отмене
5. Владелец открывает `/owner/cancellations`, проверяет справку
6. Если подтверждает → штраф снимается (amount = 0)
7. Если отклоняет → штраф остается

### Сценарий 2: Расторжение договора с автоотменой смен

1. Владелец расторгает договор с сотрудником (объекты: [1, 2, 3])
2. У сотрудника есть другой активный договор (объекты: [2, 3, 4])
3. **Вычисление:**
   - `remaining_objects = {2, 3, 4}`
   - `lost_objects = {1, 2, 3} - {2, 3, 4} = {1}`
4. Система находит все запланированные смены на объект 1
5. Для каждой смены:
   - `status = 'cancelled'`
   - Создает `ShiftCancellation`:
     - `cancelled_by_type = 'system'`
     - `cancellation_reason = 'contract_termination'`
     - `reason_notes = "Расторгнут договор №456. Причина: по соглашению сторон"`
     - Без штрафов
6. Сотрудник уведомлен об отмене смен

### Сценарий 3: Владелец отменяет смену за сотрудника

1. Владелец на странице смены `/owner/shifts/` или `/owner/shifts/{id}` нажимает "Отменить смену"
2. Открывается модальное окно с формой:
   - Выпадающий список причин (обязательно)
   - Поле примечания (опционально)
3. Выбирает причину "Просьба сотрудника", добавляет примечание
3. Добавляет заметку "Семейные обстоятельства"
4. **Результат:**
   - Смена отменена
   - `ShiftCancellation`:
     - `cancelled_by_type = 'owner'`
     - `cancellation_reason = 'employee_request'`
     - `reason_notes = "Семейные обстоятельства"`
     - Без штрафов (владелец не штрафует)
   - Сотрудник уведомлен об отмене

## Безопасность и права доступа

- **Отмена через бота:** Сотрудник может отменить только свои смены
- **Отмена через веб (владелец):** Только смены на своих объектах
- **Отмена через веб (управляющий):** Только смены на доступных объектах
- **Модерация:** Только владелец объекта может верифицировать справки
- **Аналитика:** Только данные по объектам владельца

## Производительность

- **Индексы:**
  - `shift_schedule_id`, `employee_id` - быстрый поиск отмен
  - `cancelled_by_type`, `cancellation_reason` - фильтрация
  - `created_at` - сортировка и фильтрация по датам
  - `fine_applied` - выборка неприменённых штрафов

- **Кэширование:**
  - Настройки штрафов кэшируются на уровне объекта (метод возвращает dict)
  - Статистика аналитики может быть закэширована в Redis (TODO)

## Интеграция с другими модулями

- **Contracts:** Автоотмена при расторжении (`contract_service.py::_cancel_shifts_on_contract_termination`)
- **Payroll:** Штрафы как PayrollAdjustment (отдельные записи для каждого типа штрафа)
- **Notifications:** Уведомления об отмене и верификации (TODO)
- **Analytics:** Отдельная страница статистики `/owner/analytics/cancellations`
- **Calendar:** Очистка кэша после планирования смены для немедленного отображения

## Важные детали реализации

### Eager Loading
Все запросы к объектам и подразделениям используют eager loading для предотвращения ошибок `greenlet_spawn`:
```python
object_query = select(Object).where(...).options(
    joinedload(Object.org_unit).joinedload('parent').joinedload('parent').joinedload('parent')
)
```

### Временные зоны
- Все даты хранятся в UTC
- В боте время конвертируется в timezone пользователя через `timezone_helper.py`
- Функции: `get_user_timezone(user)`, `convert_utc_to_local(dt, tz)`

### Кэш календаря
- После планирования смены очищается: `cache.clear_pattern("calendar_shifts:*")` и `cache.clear_pattern("api_response:*")`
- Frontend вызывает `window.universalCalendar.refresh()` без setTimeout

### Состояния бота
- `UserAction.CANCEL_SHIFT` - действие отмены
- `UserStep.INPUT_DOCUMENT` - ввод описания/объяснения
- `UserStep.INPUT_PHOTO` - загрузка фото
- Обработка фото в `shift_handlers.py::handle_media()` - приоритет над задачами

### Очистка контекста
После завершения отмены обязательна полная очистка:
```python
context.user_data.pop('cancelling_shift_id', None)
context.user_data.pop('cancel_reason', None)
context.user_data.pop('cancel_reason_notes', None)
context.user_data.pop('cancel_document_description', None)
context.user_data.pop('report_chat_id', None)
```

## Известные ограничения

- Нет автоматических уведомлений сотруднику/владельцу об отмене (TODO)
- Фото отправляется в группу, но не сохраняется в БД для истории
- Нет API для получения фото обратно из группы
- Timezone пользователя захардкожен (Europe/Moscow), нет настройки в профиле

