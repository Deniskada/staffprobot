# Бот: команды и callback-data

## Команды
- /start
- /help
- /status

## Callback data (паттерны)
- `analytics`
- `analytics_cancel`
- `cancel_media_upload:*` - отмена загрузки медиа для задачи (при закрытии смены)
- `cancel_my_task_media:*` - отмена загрузки медиа для задачи (во время смены)
- `cancel_shift_*`
- `close_object` - закрыть объект (Phase 4B)
- `close_shift`
- `close_shift_*`
- `close_shift_select:*`
- `close_shift_with_tasks:*` - продолжить закрытие смены после отметки задач
- `complete_my_task:shift_id:task_idx` - отметить задачу во время смены (Phase 4C)
- `complete_shift_task:shift_id:task_idx` - отметить задачу при закрытии смены (Phase 4A)
- `confirm_delete_*`
- `confirm_delete_object:*`
- `confirm_delete_timeslot:*`
- `create_*`
- `create_additional_*`
- `create_additional_slot:*`
- `create_regular_*`
- `create_regular_slot:*`
- `create_slot_*`
- `create_slot_custom_*`
- `create_slot_custom_date:*`
- `create_slot_date:*`
- `create_slot_week:*`
- `create_timeslot:*`
- `delete_*`
- `delete_object:*`
- `delete_slot_*`
- `delete_slot_custom_*`
- `delete_slot_custom_date:*`
- `delete_slot_date:*`
- `delete_slot_week:*`
- `delete_timeslot:*`
- `delete_timeslots:*`
- `edit_*`
- `edit_field:*`
- `edit_object:*`
- `edit_slot_*`
- `edit_slot_custom_*`
- `edit_slot_custom_date:*`
- `edit_slot_date:*`
- `edit_slot_week:*`
- `edit_timeslot:*`
- `edit_timeslot_*`
- `edit_timeslot_employees:*`
- `edit_timeslot_notes:*`
- `edit_timeslot_rate:*`
- `edit_timeslot_time:*`
- `edit_timeslots:*`
- `format_*`
- `get_report`
- `get_telegram_id`
- `main_menu`
- `manage_*`
- `manage_timeslots:*`
- `my_tasks` - показать задачи активной смены (Phase 4C, заменяет кнопку "Помощь")
- `open_object` - открыть объект (Phase 4B)
- `open_planned_*`
- `open_planned_shift:*`
- `open_shift`
- `open_shift_*`
- `open_shift_object:*`
- `period_*`
- `report_object_*`
- `retry_*`
- `retry_close_*`
- `retry_close_location:*`
- `retry_location:*`
- `schedule_select_object_*`
- `schedule_select_slot_*`
- `schedule_shift`
- `select_object_to_open:*` - выбор объекта для открытия (Phase 4B)
- `status`
- `toggle_timeslot_*`
- `toggle_timeslot_status:*`
- `view_*`
- `view_schedule`
- `view_timeslots:*`
- `week_*`

## Основные кнопки главного меню
- 🏢 Открыть объект (`open_object`)
- 🔒 Закрыть объект (`close_object`)
- 🔄 Открыть смену (`open_shift`)
- 🔚 Закрыть смену (`close_shift`)
- 📅 Запланировать смену (`schedule_shift`)
- 📋 Мои планы (`view_schedule`)
- 📊 Отчет (`get_report`)
- 📝 Мои задачи (`my_tasks`) - заменяет кнопку "Помощь" (с 12.10.2025)
- 📈 Статус (`status`)
- 🆔 Мой Telegram ID (`get_telegram_id`)

## UserAction (типы состояний)
- `OPEN_SHIFT` - открытие смены
- `CLOSE_SHIFT` - закрытие смены
- `OPEN_OBJECT` - открытие объекта (Phase 4B)
- `CLOSE_OBJECT` - закрытие объекта (Phase 4B)
- `MY_TASKS` - просмотр и выполнение задач во время смены (Phase 4C)
- `CREATE_OBJECT` - создание объекта
- `EDIT_OBJECT` - редактирование объекта
- `SCHEDULE_SHIFT` - планирование смены
- `VIEW_SCHEDULE` - просмотр расписания
- `CANCEL_SCHEDULE` - отмена запланированной смены
- `CREATE_TIMESLOT` - создание тайм-слота
- `EDIT_TIMESLOT_*` - редактирование тайм-слота
- `REPORT_DATES` - выбор дат для отчета

## Обработка особых случаев и исправления

### Экранирование Markdown
**Проблема:** При использовании `parse_mode='Markdown'` в Telegram, специальные символы в динамическом тексте (названия объектов, статусы) вызывали ошибки парсинга.

**Решение:** Все динамические данные (названия объектов, статусы смен и т.д.) экранируются через функцию `escape_markdown()` перед отправкой сообщений.

**Файл:** `apps/bot/handlers_div/schedule_handlers.py`

**Экранируемые символы:** `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`

### Игнорирование повторного медиа после отчёта
**Проблема:** После успешной загрузки медиа-отчёта по задаче, если пользователь отправлял ещё одно фото/видео, бот отвечал: "ℹ️ Фото/видео получено, но не в контексте отчёта".

**Решение:** В `_handle_received_media` добавлена проверка состояния `UserStep.TASK_COMPLETION`. Если пользователь уже завершил загрузку задачи, повторные медиа игнорируются без сообщений.

**Файл:** `apps/bot/handlers_div/shift_handlers.py`

### Защита от NULL object_id
**Проблема:** В редких случаях смена может быть создана без привязки к объекту (`object_id=NULL`), что приводит к ошибке SQL при попытке закрыть смену.

**Решение:** Перед обработкой закрытия смены выполняется проверка `shift.get('object_id')`. Если `object_id` отсутствует, пользователь получает сообщение: "❌ Смена не привязана к объекту. Обратитесь к администратору."

**Файл:** `apps/bot/handlers_div/shift_handlers.py`
