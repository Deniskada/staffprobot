# Логика открытия смен в боте StaffProBot

## Обзор

Документ описывает текущую логику открытия смен в Telegram-боте StaffProBot. Логика поддерживает два типа смен: **плановые** (заранее запланированные) и **спонтанные** (внеплановые).

## Архитектура

Логика реализована в следующих файлах:
- `apps/bot/handlers_div/shift_handlers.py` - основные обработчики
- `apps/bot/handlers_div/core_handlers.py` - обработчик геопозиции
- `apps/bot/services/shift_service.py` - сервис создания смен
- `apps/bot/services/shift_schedule_service.py` - сервис запланированных смен
- `apps/bot/services/timeslot_service.py` - сервис тайм-слотов

## Поток выполнения

### 1. Инициация открытия смены (`_handle_open_shift`)

**Триггер:** Пользователь нажимает кнопку "🔄 Открыть смену"

**Логика:**
1. ✅ Проверка регистрации пользователя
2. ✅ Проверка наличия активных смен (блокировка множественных смен)
3. **Поиск запланированных смен на сегодня:**
   - Вызов `ShiftScheduleService.get_user_planned_shifts_for_date(user_id, today)`
   - Получение всех запланированных смен со статусом "planned" или "confirmed"

**Ветвление:**
- **Если есть запланированные смены:** переход к выбору плановой смены
- **Если НЕТ запланированных смен:** переход к выбору объекта для спонтанной смены

### 2. Выбор плановой смены

**Триггер:** Есть запланированные смены на сегодня

**Логика:**
1. ✅ Создание состояния пользователя:
   - `action`: `UserAction.OPEN_SHIFT`
   - `step`: `UserStep.SHIFT_SELECTION`
2. ✅ Отображение списка запланированных смен с кнопками:
   - Формат: `📅 {object_name} {start_time}-{end_time}`
   - `callback_data`: `open_planned_shift:{schedule_id}`
3. ✅ Кнопка "❌ Отмена" → возврат в главное меню

### 3. Выбор объекта для спонтанной смены

**Триггер:** Нет запланированных смен на сегодня

**Логика:**
1. ✅ Получение доступных объектов:
   - Вызов `EmployeeObjectsService.get_employee_objects(user_id)`
   - Фильтрация по активным договорам
2. ✅ Создание состояния пользователя:
   - `action`: `UserAction.OPEN_SHIFT`
   - `step`: `UserStep.OBJECT_SELECTION`
   - `shift_type`: "spontaneous"
3. ✅ Отображение списка объектов с кнопками:
   - Формат: `🏢 {object_name} ({contracts_count} договор)`
   - `callback_data`: `open_shift_object:{object_id}`

### 4. Обработка выбора плановой смены (`_handle_open_planned_shift`)

**Триггер:** Пользователь выбирает конкретную плановую смену

**Логика:**
1. ✅ Получение данных запланированной смены:
   - Вызов `ShiftScheduleService.get_shift_schedule_by_id(schedule_id)`
2. ✅ Обновление состояния пользователя:
   - `selected_object_id`: ID объекта смены
   - `step`: `UserStep.LOCATION_REQUEST`
   - `shift_type`: "planned"
   - `selected_timeslot_id`: ID тайм-слота
   - `selected_schedule_id`: ID запланированной смены
3. ✅ Отображение информации о смене:
   - Объект, дата, время
4. ✅ Запрос геопозиции с кнопкой "📍 Отправить геопозицию"

### 5. Обработка выбора объекта (`_handle_open_shift_object_selection`)

**Триггер:** Пользователь выбирает объект для спонтанной смены

**Логика:**
1. ✅ Проверка доступа к объекту:
   - Вызов `EmployeeObjectsService.has_access_to_object(user_id, object_id)`
2. ✅ Получение данных объекта:
   - Вызов `EmployeeObjectsService.get_employee_object_by_id(user_id, object_id)`
3. ✅ Проверка свободных тайм-слотов:
   - Вызов `TimeSlotService.get_available_timeslots_for_object(object_id, today)`
   - Определение часовой ставки из тайм-слота или объекта
4. ✅ Обновление состояния пользователя:
   - `selected_object_id`: ID выбранного объекта
   - `step`: `UserStep.LOCATION_REQUEST`
   - `shift_type`: "spontaneous"
5. ✅ Отображение информации об объекте:
   - Название, ставка, количество доступных тайм-слотов
6. ✅ Запрос геопозиции с кнопкой "📍 Отправить геопозицию"

### 6. Обработка геопозиции (`handle_location`)

**Триггер:** Пользователь отправляет геопозицию

**Логика:**
1. ✅ Получение координат: `f"{location.latitude},{location.longitude}"`
2. ✅ Обновление состояния: `step = UserStep.PROCESSING`
3. **Вызов сервиса создания смены:**
   ```python
   result = await shift_service.open_shift(
       user_id=user_id,
       object_id=user_state.selected_object_id,
       coordinates=coordinates,
       shift_type=shift_type,  # "planned" или "spontaneous"
       timeslot_id=timeslot_id,  # для плановых смен
       schedule_id=schedule_id   # для плановых смен
   )
   ```

**Обработка результата:**
- **Успех:** Отображение информации о созданной смене
- **Ошибка:** Отображение ошибки с кнопками повторной попытки или отмены

### 7. Создание смены (`ShiftService.open_shift`)

**Логика создания:**
1. ✅ **Валидация:**
   - Проверка существования объекта
   - Поиск пользователя по `telegram_id`
   - Проверка отсутствия активных смен
   - Валидация геолокации (расстояние до объекта)

2. ✅ **Определение часовой ставки:**
   - **Для плановых смен:**
     - Приоритет: ставка из `ShiftSchedule`
     - Fallback: ставка из объекта
   - **Для спонтанных смен:**
     - Приоритет: ставка из доступного тайм-слота
     - Fallback: ставка из объекта

3. ✅ **Создание записи Shift:**
   ```python
   new_shift = Shift(
       user_id=db_user.id,  # Внутренний ID из БД
       object_id=object_id,
       start_time=datetime.now(),
       status='active',
       start_coordinates=coordinates,
       hourly_rate=hourly_rate,
       time_slot_id=timeslot_id if shift_type == "planned" else None,
       schedule_id=schedule_id if shift_type == "planned" else None,
       is_planned=shift_type == "planned"
   )
   ```

## Типы смен

### Плановые смены (`shift_type = "planned"`)
- **Источник:** Запланированные смены из `ShiftSchedule`
- **Связи:** `time_slot_id`, `schedule_id`
- **Флаг:** `is_planned = True`
- **Ставка:** Из запланированной смены или объекта

### Спонтанные смены (`shift_type = "spontaneous"`)
- **Источник:** Выбор объекта пользователем
- **Связи:** `time_slot_id = None`, `schedule_id = None`
- **Флаг:** `is_planned = False`
- **Ставка:** Из доступного тайм-слота или объекта

## Состояния пользователя

### UserAction.OPEN_SHIFT
- `step`: `UserStep.SHIFT_SELECTION` | `UserStep.OBJECT_SELECTION` | `UserStep.LOCATION_REQUEST` | `UserStep.PROCESSING`
- `shift_type`: "planned" | "spontaneous"
- `selected_object_id`: ID выбранного объекта
- `selected_timeslot_id`: ID тайм-слота (для плановых)
- `selected_schedule_id`: ID запланированной смены (для плановых)

## Обработка ошибок

### Основные ошибки:
1. **Пользователь не зарегистрирован** → предложение `/start`
2. **Уже есть активная смена** → блокировка создания новой
3. **Нет доступа к объекту** → отказ в доступе
4. **Неправильная геолокация** → предложение повторной отправки
5. **Объект не найден** → ошибка с возвратом в меню

### Повторные попытки:
- Кнопка "📍 Отправить геопозицию повторно" при ошибке геолокации
- Кнопка "❌ Отмена" для выхода из процесса

## Особенности реализации

### Геолокация
- Обязательная проверка расстояния до объекта
- Использование `max_distance_meters` из настроек объекта
- Кнопка `request_location=True` для удобства пользователя

### Часовые пояса
- Форматирование времени в часовом поясе объекта
- Использование `timezone_helper.format_local_time()`

### Множественные роли
- Поддержка системы множественных ролей пользователей
- Фильтрация объектов по активным договорам
- Проверка доступа через `EmployeeObjectsService`

## Заключение

Текущая логика открытия смен обеспечивает:
- ✅ Разделение плановых и спонтанных смен
- ✅ Валидацию доступа и геолокации
- ✅ Гибкое определение часовых ставок
- ✅ Удобный пользовательский интерфейс
- ✅ Обработку ошибок с возможностью повторных попыток
- ✅ Поддержку множественных ролей

Логика не требует изменений и работает корректно.
