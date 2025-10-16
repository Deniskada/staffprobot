# 🐛 PHASE 2 SMOKE TEST - БАГ РЕПОРТ

## 📊 Резюме
Найдено **4 критических баги** при smoke-тестировании Phase 2

---

## 🔴 БАГ #1: Название задачи тайм-слота отображается неправильно

**Сценарий:** 3 (Комбо: тайм-слот + объект)

**Наблюдение:**
```
Видно: "Эта задача стоит 123р"
Ожидалось: "Уборка дома" или реальное название задачи
```

**Анализ:**
- Строка 48 в `_load_timeslot_tasks()` правильно берёт `template.task_text`
- Строка 1639 в `_show_my_tasks_list()` правильно отображает `task.get('text')`
- **ВОЗМОЖНАЯ ПРИЧИНА**: В БД таблица `timeslot_task_templates` содержит некорректные данные
  - Поле `task_text` содержит: "Эта задача стоит 123р" вместо реального названия

**Что проверить:**
```sql
SELECT id, timeslot_id, task_text, deduction_amount, display_order 
FROM timeslot_task_templates 
WHERE timeslot_id = <your_timeslot_id>
ORDER BY display_order;
-- Что находится в task_text? Это должно быть название задачи, а не "Эта задача стоит 123р"
```

**Действия:**
- [ ] Проверить, как менеджер создаёт задачи в тайм-слотах (веб-интерфейс)
- [ ] Возможно, при сохранении перепутались поля (title + price)
- [ ] Проверить `apps/web/routes/manager_timeslots.py` строка где сохраняется task_text

---

## 🔴 БАГ #2: ignore_object_tasks не работает

**Сценарий:** 4 (Запланированная смена + ignore_object_tasks=true)

**Наблюдение:**
```
ignore_object_tasks = true
Ожидалось: только задачи тайм-слота
Видно: обе задачи (тайм-слот + объект)
```

**Анализ логики:**
Строки 96-97 в `_collect_shift_tasks()`:
```python
if not timeslot.ignore_object_tasks and object_ and object_.shift_tasks:
    # добавляем задачи объекта
```

**Возможные причины:**
1. ❓ `timeslot.ignore_object_tasks` хранит неправильное значение в БД
2. ❓ Флаг не обновился при редактировании тайм-слота
3. ❓ При загрузке `timeslot` из БД в `_handle_my_tasks` атрибут не загружается

**Что проверить:**
```sql
SELECT id, slot_date, ignore_object_tasks FROM time_slots 
WHERE id = <your_timeslot_id>;
-- Должно быть: ignore_object_tasks = true или false (но ТОЧНО то, что ты установил)
```

**Действия:**
- [ ] Проверить в БД значение `ignore_object_tasks`
- [ ] Проверить, правильно ли загружается `timeslot` в `_handle_my_tasks` (строка 1558-1561)
- [ ] Добавить логирование: `logger.info(f"timeslot.ignore_object_tasks={timeslot.ignore_object_tasks}")`

---

## 🔴 БАГ #3: Смена/объект закрываются со ВТОРОЙ попытки

**Сценарий:** 7 (Закрытие смены после "Мои задачи")

**Наблюдение:**
```
1️⃣ Отправляю геопозицию → ничего не происходит, бот молчит
2️⃣ Отправляю /start
3️⃣ Отправляю геопозицию → смена закрывается успешно
```

**Анализ:**
В `core_handlers.py` `handle_location()` обрабатывает сообщение с координатами.

**Возможные причины:**
1. **UserState не сохраняет координаты** - первое сообщение не парсится
2. **Таймаут на обработку** - первое сообщение идёт в timeout, второе обрабатывается
3. **Геопозиция неправильного формата** - первая попытка падает с ошибкой, вторая работает

**Что проверить:**
```bash
# В логах ищи:
docker compose -f docker-compose.dev.yml logs -f bot --tail 200 | grep -i "location\|coordinate\|close_shift"

# Должны быть логи:
- Получение location сообщения
- Парсинг координат
- Проверка расстояния
- Закрытие смены
```

**Действия:**
- [ ] Добавить логирование в начало `handle_location()`: 
  ```python
  logger.info(f"[LOCATION] Received location: {update.message.location}, user_state: {user_state}")
  ```
- [ ] Проверить, парсится ли первая геопозиция
- [ ] Может быть проблема с `UserState.LOCATION_REQUEST` шагом

---

## 🔴 БАГ #4: Корректировки за задачи не создаются после 23:00

**Сценарий:** 8 (Корректировки за задачи)

**Наблюдение:**
```
Время тестирования: после 23:00 МСК
Тестировал: спонтанная смена + задачи объекта (выполнена полностью)
Ожидалось: task_bonus в salary_adjustments
Видно: ничего (или только shift_base)
```

**Анализ:**
Celery задача `process_closed_shifts_adjustments` запускается каждые 10 минут.

Проверяемый код: `core/celery/tasks/adjustment_tasks.py` (170-206 загрузка задач)

**Возможные причины:**
1. **Смена не попала в выборку** - может быть вероятностный баг в SQL WHERE
2. **Задачи не загружаются** - ошибка в `_load_timeslot_tasks` или при загрузке object.shift_tasks
3. **Условие пропуска** - на строке 258 условие `if (not amount_value or float(amount_value) == 0) and not is_mandatory` пропускает задачи
4. **После 23:00 БД в другом часовом поясе** - смена "закрыта" но в БД ещё "active"

**Что проверить:**
```sql
-- 1. Смены в последние 20 минут (для Celery window)
SELECT id, user_id, object_id, status, closed_at FROM shifts 
WHERE closed_at > NOW() - INTERVAL '20 minutes'
ORDER BY closed_at DESC;

-- 2. Есть ли уже корректировки для этой смены?
SELECT * FROM salary_adjustments WHERE shift_id = <shift_id>;

-- 3. Данные о задачах в shift.notes
SELECT id, notes FROM shifts WHERE id = <shift_id>;
-- Должен быть JSON с [TASKS]{...completed_tasks: [...]}

-- 4. Задачи объекта
SELECT id, shift_tasks FROM objects WHERE id = <object_id>;
```

**Действия:**
- [ ] Проверь SQL выше - найди смену
- [ ] Посмотри содержимое `shift.notes` - там должны быть completed_tasks
- [ ] Запусти Celery вручную:
  ```bash
  docker compose -f docker-compose.dev.yml exec web python -c "
  from core.celery.tasks.adjustment_tasks import process_closed_shifts_adjustments
  from apps.api.app import app  # or your Celery app
  result = process_closed_shifts_adjustments.delay()
  print(result)
  "
  ```
- [ ] Проверь логи Celery worker:
  ```bash
  docker compose -f docker-compose.dev.yml logs celery_worker --tail 50
  ```

---

## 🔧 ДИАГНОСТИКА ДЛЯ РАЗРАБОТЧИКА

### Обрадак действий:

**1. БАГ #1 - Название задачи (КРИТИЧНО)**
```python
# Добавить логирование в _load_timeslot_tasks()
logger.info(f"Loaded task from template: task_text='{template.task_text}', deduction_amount={template.deduction_amount}")

# Запросить SQL результат
SELECT task_text FROM timeslot_task_templates WHERE id = <task_id> LIMIT 1;
```

**2. БАГ #2 - ignore_object_tasks (КРИТИЧНО)**
```python
# Добавить в _collect_shift_tasks()
logger.info(f"timeslot.ignore_object_tasks = {timeslot.ignore_object_tasks if timeslot else 'NO_TIMESLOT'}")

# Добавить в _handle_my_tasks()
logger.info(f"Loaded timeslot: {timeslot}, ignore={timeslot.ignore_object_tasks if timeslot else None}")
```

**3. БАГ #3 - Двойная геопозиция (КРИТИЧНО)**
```python
# В handle_location() в начале
logger.info(f"[LOCATION] Got location update: {update.message.location}")
logger.info(f"[LOCATION] User state: action={user_state.action}, step={user_state.step}")

# Проверить логи, ищи "LOCATION" в first attempt vs second attempt
```

**4. БАГ #4 - Корректировки (ВЫСОКИЙ ПРИОРИТЕТ)**
```bash
# Запусти вручную:
docker compose -f docker-compose.dev.yml exec web python << 'EOF'
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_async_session
from core.celery.tasks.adjustment_tasks import process_closed_shifts_adjustments

# Запусти задачу вручную для последней закрытой смены
asyncio.run(process_closed_shifts_adjustments())
EOF
```

---

## 📋 ACTION ITEMS ДЛЯ ТЕСТЕРА

**После диагностики запусти:**

1. БАГ #1 - Проверь в БД `timeslot_task_templates`:
   ```sql
   SELECT COUNT(*), GROUP_CONCAT(task_text) FROM timeslot_task_templates;
   ```

2. БАГ #2 - Проверь флаг:
   ```sql
   SELECT id, ignore_object_tasks FROM time_slots WHERE ignore_object_tasks = true LIMIT 1;
   ```

3. БАГ #3 - Смотри логи бота при отправке геолокации

4. БАГ #4 - Запусти вручную Celery задачу и проверь логи

---

## 📊 Итоговый статус

| Баг | Сценарий | Тип | Статус |
|-----|----------|-----|--------|
| #1 | 3 | Данные в БД | 🔴 Критично |
| #2 | 4 | Логика кода | 🔴 Критично |
| #3 | 7 | Асинхронная обработка | 🔴 Критично |
| #4 | 8 | Celery/Расстояния | 🔴 Высокий приоритет |

**Phase 2 НЕ готова к production до фиксинга этих 4 багов!**
