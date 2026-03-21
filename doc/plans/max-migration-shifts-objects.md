# План миграции: смены и объекты в UnifiedBotRouter (MAX)

## Этап 1: Открытие/закрытие смен

### Зависимости
- Резолвер: (provider, external_id) → internal_user_id
- State: ключ по internal_user_id (совместимость с TG)
- Сервисы: поддержка internal_user_id (shift_service, employee_objects_service)
- Геолокация: парсинг location в MaxAdapter (message_created)

### Шаги
1. Добавить `get_telegram_id_for_internal_user` — для legacy-сервисов (если есть)
2. Расширить shift_service: `open_shift(internal_user_id=..., coordinates=...)`
3. Расширить employee_objects_service: `get_employee_objects(internal_user_id=...)`
4. MaxAdapter: парсинг location из body.attachments
5. shared/bot_unified/shift_handlers_unified.py — обработчики open_shift, close_shift
6. user_state_manager: использовать internal_user_id как ключ (для MAX)

### Callback-цепочка
- open_shift → выбор объекта (open_shift_object:N) → запрос геолокации → handle_location
- close_shift → выбор смены (close_shift_select:N) → запрос геолокации → handle_location

## Этап 2: Открытие/закрытие объектов

Аналогично, callback_data: open_object, close_object, select_object_to_open:N

## Этап 3: Остальное

schedule_shift, view_schedule, get_report, my_tasks, status
