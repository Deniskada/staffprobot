# 🔧 PHASE 2 BUG FIXES - Систематический план

## 📊 Очередность фиксинга

1. **БАГ #4** (корректировки) - ПЕРВЫЙ! Это дает нам видимость что работает
2. **БАГ #1** (название задачи) - ВТОРОЙ, проверяем данные в БД
3. **БАГ #2** (флаг ignore) - ТРЕТИЙ, фиксим логику загрузки
4. **БАГ #3** (геопозиция) - ЧЕТВЕРТЫЙ, самый сложный

---

## 🔴 ФИХ #4: Корректировки не создаются

### ГИПОТЕЗА:
Статус смены `'closed'` вместо `'completed'` → Celery её не видит

### ДЕЙСТВИЕ 1: Проверить статусы в БД
```bash
# Запросить последние смены
psql -U postgres -d staffprobot_dev << 'EOF'
SELECT id, status, user_id, closed_at FROM shifts 
WHERE closed_at > NOW() - INTERVAL '2 hours'
ORDER BY closed_at DESC LIMIT 10;
EOF

# Результат: какой статус? 'closed' или 'completed'?
```

### ДЕЙСТВИЕ 2: Если статус 'closed', то фиксим adjustment_tasks.py
```python
# apps/web/services/shift_service.py или где закрывается смена
# БЫЛО:
shift.status = 'closed'

# БУДЕТ:
shift.status = 'completed'
```

### ДЕЙСТВИЕ 3: Если статус правильный, то фиксим SQL
```python
# core/celery/tasks/adjustment_tasks.py строка 49
# БЫЛО:
Shift.status == 'completed',

# ПРОВЕРЯЕМ: может быть нужны оба статуса
Shift.status.in_(['closed', 'completed']),
```

### ДЕЙСТВИЕ 4: Запустить Celery вручную
```bash
docker compose -f docker-compose.dev.yml exec web python << 'EOF'
import asyncio
from core.celery.celery_app import celery_app

# Запустить задачу вручную
result = celery_app.send_task('process_closed_shifts_adjustments')
print(f"Task queued: {result}")

# Проверить логи
import time
time.sleep(5)
EOF

# И проверить логи Celery
docker compose -f docker-compose.dev.yml logs celery_worker --tail 50 | grep -i "adjustment\|found"
```

---

## 🔴 ФИХ #1: Название задачи - "Эта задача стоит 123р"

### ГИПОТЕЗА:
В БД таблица `timeslot_task_templates` содержит неправильные данные

### ДЕЙСТВИЕ 1: Проверить данные в БД
```bash
psql -U postgres -d staffprobot_dev << 'EOF'
SELECT id, timeslot_id, task_text, deduction_amount FROM timeslot_task_templates 
WHERE task_text LIKE '%стоит%'
LIMIT 5;

-- Или все задачи последнего тайм-слота
SELECT id, task_text, deduction_amount FROM timeslot_task_templates 
WHERE timeslot_id = (SELECT MAX(id) FROM time_slots)
ORDER BY display_order;
EOF
```

### ДЕЙСТВИЕ 2: Если данные неправильные, очистить
```bash
psql -U postgres -d staffprobot_dev << 'EOF'
-- Найти тайм-слоты с неправильными названиями
SELECT DISTINCT timeslot_id FROM timeslot_task_templates 
WHERE task_text LIKE '%стоит%';

-- Удалить неправильные задачи
DELETE FROM timeslot_task_templates 
WHERE task_text LIKE '%стоит%';
EOF
```

### ДЕЙСТВИЕ 3: Проверить где это создается
```bash
grep -r "Эта задача стоит\|стоит.*р" /home/sa/projects/staffprobot --include="*.py" --include="*.js"
# Если найдется - это баг в веб-интерфейсе при создании задач
```

### ДЕЙСТВИЕ 4: Проверить код создания задач менеджером
```python
# apps/web/routes/manager_timeslots.py
# ИЩИ: где сохраняется task_text в timeslot_task_templates
# ПРОВЕРЬ: не перепутаны ли поля (description + price)
```

---

## 🔴 ФИХ #2: ignore_object_tasks не работает

### ГИПОТЕЗА:
Флаг `ignore_object_tasks` не загружается при получении тайм-слота

### ДЕЙСТВИЕ 1: Добавить логирование в код
```python
# apps/bot/handlers_div/shift_handlers.py строка 1558-1561
# В _handle_my_tasks()

if shift_obj.time_slot_id:
    timeslot_query = select(TimeSlot).where(TimeSlot.id == shift_obj.time_slot_id)
    timeslot_result = await session.execute(timeslot_query)
    timeslot = timeslot_result.scalar_one_or_none()
    
    # ДОБАВЬ:
    logger.info(f"[DEBUG] Loaded timeslot: id={timeslot.id if timeslot else None}, ignore_object_tasks={timeslot.ignore_object_tasks if timeslot else 'NO_TIMESLOT'}")
```

### ДЕЙСТВИЕ 2: Тестировать снова и смотреть логи
```bash
docker compose -f docker-compose.dev.yml logs -f bot --tail 100 | grep "\[DEBUG\] Loaded timeslot"

# Должно быть: ignore_object_tasks=True или False (точно, как ты установил)
```

### ДЕЙСТВИЕ 3: Если флаг неправильный в логах, проверить БД
```bash
psql -U postgres -d staffprobot_dev << 'EOF'
SELECT id, slot_date, ignore_object_tasks FROM time_slots 
WHERE ignore_object_tasks = true
LIMIT 1;
EOF
```

### ДЕЙСТВИЕ 4: Если БД правильная, но логирование показывает неправильное - баг в загрузке
```python
# Может быть, need selectinload для timeslot
# В _handle_my_tasks() проверь, как загружается shift с relationshipами
```

---

## 🔴 ФИХ #3: Геопозиция нужна дважды

### ГИПОТЕЗА:
Первое сообщение с location не парсится или падает в timeout

### ДЕЙСТВИЕ 1: Добавить логирование
```python
# apps/bot/handlers_div/core_handlers.py в handle_location()
# В НАЧАЛЕ функции:

logger.info(
    f"[LOCATION_DEBUG] Received location message",
    user_id=update.message.from_user.id,
    latitude=update.message.location.latitude if update.message.location else None,
    user_state_action=user_state.action if user_state else None,
    user_state_step=user_state.step if user_state else None
)
```

### ДЕЙСТВИЕ 2: Тестировать и смотреть логи
```bash
# 1️⃣ Отправь геопозицию ПЕРВЫЙ раз
# 2️⃣ Смотри логи:
docker compose -f docker-compose.dev.yml logs -f bot --tail 50 | grep "\[LOCATION_DEBUG\]"

# Должно быть: latitude = правильное число, action = CLOSE_SHIFT, step = LOCATION_REQUEST

# 3️⃣ Если НИЧЕГО не видно - значит, обработчик не вызывается для location
```

### ДЕЙСТВИЕ 3: Проверить, регистрирован ли handler для message с location
```python
# apps/bot/bot.py или handlers registration
# Должна быть регистрация для message handler с location

# Ищи что-то типа:
# application.add_handler(MessageHandler(filters.LOCATION, handle_location))
```

### ДЕЙСТВИЕ 4: Если handler зарегистрирован, но не вызывается - проверить user_state
```python
# Может быть, user_state.step != UserStep.LOCATION_REQUEST
# Добавь дополнительное логирование:

if not user_state or user_state.step != UserStep.LOCATION_REQUEST:
    logger.warning(
        f"[LOCATION] Ignoring location - invalid state",
        has_state=bool(user_state),
        step=user_state.step if user_state else None,
        expected_step=UserStep.LOCATION_REQUEST
    )
```

---

## 📋 CHECKLIST

### Шаг 1: Подготовка
- [ ] Откроешь БД консоль
- [ ] Откроешь логи контейнеров
- [ ] Откроешь редактор для кода

### Шаг 2: ФИХ #4 (Статус смены)
- [ ] Проверить статусы в БД
- [ ] Если 'closed' - изменить на 'completed'
- [ ] Запустить Celery вручную
- [ ] Проверить salary_adjustments

### Шаг 3: ФИХ #1 (Название задачи)
- [ ] Проверить timeslot_task_templates в БД
- [ ] Если неправильные данные - удалить
- [ ] Пересоздать задачи через веб

### Шаг 4: ФИХ #2 (Флаг ignore)
- [ ] Добавить логирование в _handle_my_tasks()
- [ ] Тестировать "Мои задачи"
- [ ] Проверить логи
- [ ] Если неправильно - разбираться с загрузкой

### Шаг 5: ФИХ #3 (Геопозиция)
- [ ] Добавить логирование в handle_location()
- [ ] Отправить геопозицию ПЕРВЫЙ раз
- [ ] Смотреть логи
- [ ] Найти почему не обрабатывается

### Шаг 6: Финал
- [ ] Запустить все 8 сценариев smoke test снова
- [ ] Убедиться, что все работает
- [ ] Коммит: "Фиксинг: 4 критических бага Phase 2"

---

## 🚀 КОМАНДА ДЛЯ БЫСТРОГО СТАРТА

```bash
# 1. Откройте логи
docker compose -f docker-compose.dev.yml logs -f bot web --tail 50

# 2. В ОТДЕЛЬНОМ окне терминала - проверьте БД
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev

# 3. Начните тестировать сценарии с логированием
```

---

## 📊 ФИНАЛЬНЫЙ СТАТУС

После фиксинга всех 4 багов:
- ✅ Сценарий 3 - название задачи правильное
- ✅ Сценарий 4 - флаг ignore работает
- ✅ Сценарий 7 - геопозиция с первой попытки
- ✅ Сценарий 8 - корректировки создаются

**Phase 2 READY FOR PRODUCTION** ✅
