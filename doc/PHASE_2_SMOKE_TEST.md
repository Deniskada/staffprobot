# 🧪 Smoke Test План для Phase 2: Унификация загрузки задач

## 📋 Цель
Проверить, что унифицированная функция `_collect_shift_tasks()` работает корректно в **"Мои задачи"** и все задачи загружаются правильно.

---

## 🎯 Сценарии тестирования

### **Сценарий 1: Спонтанная смена + Задачи объекта**
**Условие:** Откройте спонтанную смену на объекте с задачами

**Шаги:**
1. Нажмите "Открыть смену" → "⚡ Внеплановая смена"
2. Выберите объект (убедитесь, что у объекта есть `shift_tasks` в БД)
3. Отправьте геопозицию
4. ✅ Смена открывается
5. Нажмите "Мои задачи" 
6. **ПРОВЕРКА**: Должны отобразиться ВСЕ задачи объекта

**Ожидаемый результат:**
- ✅ Список задач показан
- ✅ Каждая задача имеет иконку (⚠️/⭐), текст, цену
- ✅ Нет ошибок в логах

**SQL для проверки:**
```sql
SELECT id, name, shift_tasks FROM objects WHERE id = <object_id> LIMIT 1;
-- Должны быть задачи в shift_tasks (JSONB)
```

---

### **Сценарий 2: Запланированная смена + Задачи тайм-слота**
**Условие:** На сегодня есть тайм-слот с задачами

**Шаги:**
1. Нажмите "Открыть смену" → "📅 Запланированные смены"
2. Выберите запланированную смену
3. Отправьте геопозицию
4. ✅ Смена открывается
5. Нажмите "Мои задачи"
6. **ПРОВЕРКА**: Должны отобразиться задачи из `TimeslotTaskTemplate`

**Ожидаемый результат:**
- ✅ Список задач из тайм-слота показан
- ✅ Каждая задача имеет: текст, цену, иконку медиа (если нужна)
- ✅ Нет ошибок "Задача не найдена"

**SQL для проверки:**
```sql
SELECT id, timeslot_id FROM shifts WHERE status = 'active' ORDER BY created_at DESC LIMIT 1;
SELECT id, slot_date, ignore_object_tasks FROM time_slots WHERE id = <timeslot_id>;
SELECT task_text, deduction_amount, requires_media FROM timeslot_task_templates 
  WHERE timeslot_id = <timeslot_id> ORDER BY display_order;
```

---

### **Сценарий 3: Запланированная смена + Комбо (тайм-слот + объект)**
**Условие:** Тайм-слот имеет `ignore_object_tasks = false` + объект имеет `shift_tasks`

**Шаги:**
1. Откройте запланированную смену (с `ignore_object_tasks = false`)
2. Смена открывается
3. Нажмите "Мои задачи"
4. **ПРОВЕРКА**: Должны быть задачи ИЗ ОБОИХ источников (тайм-слот + объект)

**Ожидаемый результат:**
- ✅ Задачи из тайм-слота (первые, с источником 'timeslot')
- ✅ Задачи из объекта (вторые, с источником 'object')
- ✅ Всего задач = кол-во из TimeslotTaskTemplate + кол-во из object.shift_tasks

**SQL для проверки:**
```sql
SELECT COUNT(*) FROM timeslot_task_templates WHERE timeslot_id = <timeslot_id>;
SELECT jsonb_array_length(shift_tasks) FROM objects WHERE id = <object_id>;
-- Сумма должна равняться количеству задач в "Мои задачи"
```

---

### **Сценарий 4: Запланированная смена + ignore_object_tasks = true**
**Условие:** Тайм-слот имеет `ignore_object_tasks = true`

**Шаги:**
1. Откройте запланированную смену (с `ignore_object_tasks = true`)
2. Нажмите "Мои задачи"
3. **ПРОВЕРКА**: Должны быть ТОЛЬКО задачи тайм-слота, БЕЗ задач объекта

**Ожидаемый результат:**
- ✅ Показаны только задачи из `TimeslotTaskTemplate`
- ✅ Задачи объекта НЕ видны
- ✅ Количество задач = COUNT(*) из timeslot_task_templates

---

### **Сценарий 5: Отметить задачу как выполненную**
**Условие:** Активная смена с задачами

**Шаги:**
1. Откройте "Мои задачи"
2. Нажмите на первую задачу (без медиа-отчета)
3. ✅ Задача получает галочку ✓
4. Нажмите ещё раз
5. ✅ Галочка убирается

**Ожидаемый результат:**
- ✅ Toggle работает корректно
- ✅ В `UserState` сохраняется `completed_tasks`
- ✅ После /start список обновляется

**Логирование:**
Поиск в логах: `[MY_TASKS] Task: ...`

---

### **Сценарий 6: Задача с медиа-отчетом**
**Условие:** В "Мои задачи" есть задача с иконкой 📸

**Шаги:**
1. Откройте "Мои задачи"
2. Нажмите на задачу с 📸
3. ✅ Бот запрашивает отправить фото/видео
4. Отправьте фото
5. ✅ Фото отправляется в Telegram группу
6. ✅ Задача отмечается как выполненная ✅

**Ожидаемый результат:**
- ✅ Медиа загружается в Telegram
- ✅ В `task_media` сохраняется ссылка и тип
- ✅ Задача помечается как завершённая

---

### **Сценарий 7: Закрытие смены после "Мои задачи"**
**Условие:** Выполнили задачи в "Мои задачи", теперь закрываем смену

**Шаги:**
1. Откройте "Мои задачи"
2. Отметьте 2-3 задачи как выполненные
3. Закройте смену (через главное меню)
4. Отправьте геопозицию
5. ✅ Смена закрывается
6. **ПРОВЕРКА**: В `shift.notes` должны сохраниться `completed_tasks`

**SQL для проверки:**
```sql
SELECT id, notes FROM shifts 
WHERE status = 'closed' 
ORDER BY closed_at DESC LIMIT 1;
-- В notes должен быть JSON с [TASKS]{...completed_tasks: [0, 1, 2]}
```

**Логирование:**
```
logger.info("Saved completed tasks info", shift_id=..., completed_count=..., total_count=..., media_count=...)
```

---

### **Сценарий 8: Корректировки за задачи**
**Условие:** Смена закрыта, задачи выполнены

**Шаги:**
1. Закройте смену с выполненными задачами
2. Подождите 10-15 минут (или проверьте вручную Celery задачу)
3. Проверьте, что создались корректировки

**SQL для проверки:**
```sql
SELECT * FROM salary_adjustments 
WHERE shift_id = <shift_id> 
ORDER BY created_at DESC;
-- Должны быть корректировки:
-- - shift_base (за саму смену)
-- - task_bonus или task_penalty (за задачи)
```

**Ожидаемые корректировки:**
- ✅ `shift_base` - оплата за смену
- ✅ `task_bonus` - премия за выполненную задачу
- ✅ `task_penalty` - штраф за невыполненную задачу (если есть)
- ✅ `task_completed` - нулевая корректировка для задач с медиа (если требуется)

---

## ⚠️ Что проверять в логах

### Важные логи:
```
[MY_TASKS] Loading/creating state for user ...
[MY_TASKS] Combined tasks from timeslot and object
[MY_TASKS] Reusing existing state with ... completed tasks
[MY_TASKS] Task list shown successfully
```

### На что обращать внимание:
```
❌ ERROR: IndexError: list index out of range
❌ ERROR: Task not found
❌ ERROR: Loading/creating state failed
```

---

## 📱 Checklist для тестера

| # | Сценарий | Статус | Примечания |
|---|----------|--------|-----------|
| 1 | Спонтанная смена + объект-задачи | ☐ | |
| 2 | Запланированная смена + тайм-слот-задачи | ☐ | |
| 3 | Комбо: тайм-слот + объект (ignore=false) | ☐ | |
| 4 | Только тайм-слот (ignore=true) | ☐ | |
| 5 | Toggle выполнения задачи | ☐ | |
| 6 | Медиа-отчет для задачи | ☐ | |
| 7 | Закрытие смены с сохранением в notes | ☐ | |
| 8 | Создание корректировок в salary_adjustments | ☐ | |

---

## 🔧 Полезные команды

### Проверить состояние смены:
```sql
SELECT id, user_id, object_id, time_slot_id, status, start_time, closed_at, notes 
FROM shifts 
WHERE status IN ('active', 'closed')
ORDER BY created_at DESC LIMIT 5;
```

### Проверить задачи тайм-слота:
```sql
SELECT id, timeslot_id, task_text, deduction_amount, requires_media, display_order
FROM timeslot_task_templates
WHERE timeslot_id = <timeslot_id>
ORDER BY display_order;
```

### Проверить корректировки:
```sql
SELECT id, shift_id, adjustment_type, amount, details, created_at
FROM salary_adjustments
WHERE shift_id = <shift_id>
ORDER BY created_at;
```

### Просмотр логов Docker:
```bash
docker compose -f docker-compose.dev.yml logs -f bot --tail 100
docker compose -f docker-compose.dev.yml logs -f web --tail 100
```

---

## 📊 Метрики успеха

✅ **Все 8 сценариев пройдены без ошибок**
✅ **В логах нет ERROR сообщений про задачи**
✅ **Корректировки создаются за выполненные задачи**
✅ **Медиа загружается в Telegram группу**
✅ **UserState сохраняет completed_tasks между действиями**

---

## 🚀 Следующие шаги после smoke test

1. Если все ОК → готово к Phase 3 (Фиксинг "Закрыть объект")
2. Если есть ошибки → залог в Cursor/Project Brain с описанием проблемы
