# Рефакторинг задач тайм-слотов

**Дата**: 2025-10-16  
**Статус**: ✅ Завершено

## 📋 Проблема

До рефакторинга задачи тайм-слотов хранились в двух местах:

1. **JSONB поле** `time_slots.shift_tasks` — старый способ (напрямую в JSON)
2. **Таблица** `timeslot_task_templates` — новый способ (через веб-интерфейс)

При добавлении задач через веб-интерфейс (`/owner/timeslots/{id}/edit`), они сохранялись в таблицу `timeslot_task_templates`. Но **бот** при открытии смены и отображении задач читал **только** JSONB поле, игнорируя задачи из таблицы.

### Кейс пользователя

1. Создаётся запланированная смена на тайм-слот
2. Позже владелец добавляет задачи в тайм-слот через веб-интерфейс
3. Сотрудник открывает смену → **задачи не отображаются** ❌
4. При закрытии смены → **задачи не отображаются** ❌

### 🔴 Критическая проблема: Корректировки за задачи не создаются

**Дата обнаружения**: 2025-10-16 (ночь после деплоя)

**Проблема**: На проде после деплоя коммита `c05a40e` стали не создаваться корректировки `task_bonus` и `task_penalty`, хотя `shift_base` и `late_start` штрафы создавались.

**Диагностика**:
1. **Заблуждение**: Изначально казалось, что issue в боте (completed_tasks не сохраняются)
2. **Реальная причина**: В `core/celery/tasks/adjustment_tasks.py` строка 181 использовала **синхронный** `session.execute()` вместо `await session.execute()`:
   ```python
   # ❌ НЕПРАВИЛЬНО - синхронный код в async Celery
   template_result = session.execute(template_query)
   ```
   Это приводило к ошибке или None при попытке загрузить задачи из таблицы `timeslot_task_templates`.
3. **Симптомы**:
   - `shift_tasks` оставался пустым `[]`
   - Условие `if shift_tasks:` не выполнялось (строка 207)
   - Цикл обработки задач (строки 235-355) никогда не выполнялся
   - Корректировки `task_bonus`/`task_penalty` не создавались
   - Базовая оплата и штрафы за опоздания работали (т.к. находятся до этого блока)

**Проблемный коммит**: `c05a40e` "Исправление: инвалидация кэша календаря..."
- Изменена загрузка задач тайм-слота с `shift.time_slot.shift_tasks` (JSONB) на `TimeslotTaskTemplate` (таблица)
- Забыт `await` перед `session.execute()`

## ✅ Решение

### Этап 1: Исправление бота (загрузка из обоих источников)

**Файлы:**
- `apps/bot/handlers_div/shift_handlers.py`

**Изменения:**
1. Добавлена вспомогательная функция `_load_timeslot_tasks()`, которая загружает задачи из таблицы `timeslot_task_templates`
2. Обновлена `_handle_close_shift` — использует `_load_timeslot_tasks()`
3. Обновлена `_handle_my_tasks` — использует `_load_timeslot_tasks()`
4. Добавлено подробное логирование

**Результат:** Бот теперь отображает задачи, добавленные через веб-интерфейс ✅

### Этап 2: Удаление JSONB поля (чистота архитектуры)

**Файлы:**
- `domain/entities/time_slot.py` — удалено поле `shift_tasks` (JSONB)
- `apps/bot/handlers_div/shift_handlers.py` — упрощена функция `_load_timeslot_tasks()`
- `migrations/versions/47854ebf33dc_remove_shift_tasks_jsonb_from_timeslots.py` — миграция БД

**Миграция:**
```bash
# Dev
docker compose -f docker-compose.dev.yml exec web alembic upgrade head

# Prod
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic upgrade head'
```

**Результат:** Единый источник данных — только таблица `timeslot_task_templates` ✅

## 🎯 Архитектура после рефакторинга

### Хранение задач тайм-слотов

**Только таблица `timeslot_task_templates`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | PK |
| `timeslot_id` | Integer | FK → time_slots.id |
| `task_text` | String | Текст задачи |
| `is_mandatory` | Boolean | Обязательная задача |
| `deduction_amount` | Integer | Штраф/премия (₽) |
| `display_order` | Integer | Порядок отображения |
| `created_by_id` | Integer | FK → users.id |

### Загрузка задач в боте

```python
async def _load_timeslot_tasks(session: AsyncSession, timeslot: TimeSlot) -> list:
    """Загружает задачи тайм-слота из таблицы timeslot_task_templates."""
    template_query = select(TimeslotTaskTemplate).where(
        TimeslotTaskTemplate.timeslot_id == timeslot.id
    ).order_by(TimeslotTaskTemplate.display_order)
    
    template_result = await session.execute(template_query)
    templates = template_result.scalars().all()
    
    return [
        {
            'text': template.task_text,
            'is_mandatory': template.is_mandatory or False,
            'deduction_amount': template.deduction_amount or 0,
            'source': 'timeslot'
        }
        for template in templates
    ]
```

### Создание/редактирование через веб

**Роут:** `/owner/timeslots/{id}/edit` (POST)  
**Файл:** `apps/web/routes/owner_timeslots.py`

**Логика:**
1. Получить `task_texts[]` из формы
2. Удалить все существующие `TimeslotTaskTemplate` для данного `timeslot_id`
3. Создать новые `TimeslotTaskTemplate` записи
4. Сохранить в БД

## 📊 Преимущества

### До рефакторинга

- ❌ Дублирование данных (JSONB + таблица)
- ❌ Несинхронизация (бот видит только JSONB)
- ❌ Сложность поддержки (два источника истины)
- ❌ Задачи через веб не отображались в боте

### После рефакторинга

- ✅ Единый источник данных (только таблица)
- ✅ Бот и веб используют одни данные
- ✅ Простота поддержки (один источник истины)
- ✅ Задачи через веб сразу видны в боте
- ✅ Возможность редактирования через веб для активных смен

## 🧪 Тестирование

### Сценарий 1: Добавление задач для существующей смены

1. Создать запланированную смену на тайм-слот ✅
2. Добавить задачи через `/owner/timeslots/{id}/edit` ✅
3. Открыть смену в боте → задачи отображаются ✅
4. Нажать "Мои задачи" → задачи отображаются ✅
5. Закрыть смену → задачи для отметки ✅

### Сценарий 2: Комбинирование задач

1. Объект имеет задачи в `object.shift_tasks` (JSONB) ✅
2. Тайм-слот имеет задачи в `timeslot_task_templates` ✅
3. `timeslot.ignore_object_tasks = False` ✅
4. Открыть смену → обе группы задач отображаются ✅

### Сценарий 3: Игнорирование задач объекта

1. Объект имеет задачи в `object.shift_tasks` ✅
2. Тайм-слот имеет задачи в `timeslot_task_templates` ✅
3. `timeslot.ignore_object_tasks = True` ✅
4. Открыть смену → только задачи тайм-слота ✅

## 📝 Связанные задачи

- ✅ Исправлен роут `/owner/timeslots/{id}/edit` (добавлен импорт `select`)
- ✅ Исправлен формат ставки (`int(float())` для поддержки "500.0")
- ✅ Удалён неиспользуемый импорт `ShiftTaskService`
- ✅ Обновлена документация в `doc/vision_v1/entities/timeslots.md`

### ✅ Исправление корректировок за задачи (2025-10-16, поздно)

**Файл**: `core/celery/tasks/adjustment_tasks.py` строка 181

**Проблема**: Синхронный `session.execute()` в асинхронной Celery задаче.

**Fix**: Добавлен `await`:
```python
# ДО (❌)
template_result = session.execute(template_query)

# ПОСЛЕ (✅)
template_result = await session.execute(template_query)
```

**Результат**: Celery задача `process_closed_shifts_adjustments` теперь корректно загружает задачи из таблицы `timeslot_task_templates` и создаёт корректировки `task_bonus`/`task_penalty`.

**Тестирование на prod**: Убедиться, что после этого fix корректировки за задачи создаются в течение 10 минут после закрытия смены.

## 🚀 Деплой

### Порядок деплоя на prod

1. Закоммитить изменения:
```bash
git add apps/bot/handlers_div/shift_handlers.py \
        domain/entities/time_slot.py \
        migrations/versions/47854ebf33dc_remove_shift_tasks_jsonb_from_timeslots.py \
        doc/TIMESLOT_TASKS_REFACTORING.md

git commit -m "Рефакторинг: унификация хранения задач тайм-слотов"
git push origin main
```

2. Обновить код на проде:
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git pull origin main'
```

3. Применить миграцию:
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic upgrade head'
```

4. Перезапустить контейнеры:
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml restart web bot'
```

5. Проверить логи:
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml logs bot --tail 50'
```

## ⚠️ Важные замечания

1. **Старые данные в JSONB не мигрируются** — они просто удаляются при применении миграции
2. **Downgrade возможен** — миграция восстановит колонку, но данные не вернутся
3. **Object.shift_tasks остаётся** — это задачи объекта (не тайм-слота), они хранятся в JSONB

## 🔗 Ссылки

- **Техническое видение:** `doc/vision.md`
- **Документация по задачам:** `doc/vision_v1/entities/shift_task.md`
- **Роуты тайм-слотов:** `doc/vision_v1/entities/timeslots.md`
- **Бот-логика смен:** `doc/bot_shift_logic.md`

