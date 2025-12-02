# План исправления критических ошибок в payroll_tasks.py

## 🎯 Цель
Исправить 2 критические ошибки в `core/celery/tasks/payroll_tasks.py`, чтобы начисления создавались автоматически через Celery.

---

## 🔍 Проблемы

### Ошибка 1: Отсутствует импорт
**Строка 79:** `payment_period = await get_payment_period_for_date(schedule, today)`  
**Ошибка:** `NameError: name 'get_payment_period_for_date' is not defined`

### Ошибка 2: Необъявленная переменная
**Строка 431:** `total_entries_updated += 1`  
**Ошибка:** `NameError: name 'total_entries_updated' is not defined`

---

## ✅ План действий

### Шаг 1: Анализ зависимостей
✅ **ВЫПОЛНЕНО** - Функция найдена в `shared/services/payment_schedule_service.py:9`

### Шаг 2: Проверка текущих импортов
✅ **ВЫПОЛНЕНО** - Уже импортируется `PayrollAdjustmentService` из `shared.services`

### Шаг 3: Внести изменения в код (DEV)

**Изменение 1 - Добавить импорт (после строки 20):**
```python
from shared.services.payroll_adjustment_service import PayrollAdjustmentService
from shared.services.payment_schedule_service import get_payment_period_for_date  # ← ДОБАВИТЬ
```

**Изменение 2 - Объявить переменную (строка 62):**
```python
total_entries_created = 0
total_entries_updated = 0  # ← ДОБАВИТЬ
total_adjustments_applied = 0
errors = []
```

**Изменение 3 - Обновить логирование (строка 462):**
```python
logger.info(
    f"Payroll entries creation completed",
    entries_created=total_entries_created,
    entries_updated=total_entries_updated,  # ← ДОБАВИТЬ
    adjustments_applied=total_adjustments_applied,
    errors_count=len(errors)
)
```

**Изменение 4 - Обновить return (строка 469):**
```python
return {
    'success': True,
    'date': today.isoformat(),
    'entries_created': total_entries_created,
    'entries_updated': total_entries_updated,  # ← ДОБАВИТЬ
    'adjustments_applied': total_adjustments_applied,
    'errors': errors
}
```

### Шаг 4: Проверка синтаксиса
```bash
python3 -m py_compile core/celery/tasks/payroll_tasks.py
```

### Шаг 5: Проверка линтера
Использовать `read_lints` в Cursor

### Шаг 6: Перезапуск контейнеров DEV
```bash
docker compose -f docker-compose.dev.yml restart celery_worker celery_beat
```

### Шаг 7: Тестирование на DEV
```bash
docker compose -f docker-compose.dev.yml exec web python << 'PYTHON'
from core.celery.tasks.payroll_tasks import create_payroll_entries_by_schedule
result = create_payroll_entries_by_schedule(target_date="2025-12-02")
print(f"Result: {result}")
PYTHON
```

### Шаг 8: Проверка логов DEV
```bash
docker compose -f docker-compose.dev.yml logs celery_worker --tail 100 | grep -A 20 "Starting payroll"
```

### Шаг 9: Проверка функции get_payment_period_for_date
```bash
docker compose -f docker-compose.dev.yml exec web python << 'PYTHON'
import asyncio
from datetime import date
from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.payment_schedule import PaymentSchedule
from shared.services.payment_schedule_service import get_payment_period_for_date

async def test():
    async with get_async_session() as session:
        result = await session.execute(
            select(PaymentSchedule).where(PaymentSchedule.id == 2)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            period = await get_payment_period_for_date(schedule, date(2025, 12, 2))
            print(f"Schedule ID={schedule.id}, Name={schedule.name}")
            print(f"Period: {period}")
        else:
            print("Schedule not found!")

asyncio.run(test())
PYTHON
```

### Шаг 10: Коммит изменений
```bash
git add core/celery/tasks/payroll_tasks.py
git commit -m "Исправление: добавлен импорт get_payment_period_for_date и переменная total_entries_updated"
```

### Шаг 11: Деплой на PROD
**ТОЛЬКО после успешного тестирования на DEV!**
```bash
git push origin main
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git pull && docker compose -f docker-compose.prod.yml restart celery_worker celery_beat'
```

### Шаг 12: Мониторинг PROD (3 декабря после 04:05)
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml logs celery_beat --since 2h | grep payroll'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod -c "SELECT COUNT(*), period_start, period_end, created_by_id FROM payroll_entries WHERE created_at >= NOW() - INTERVAL '\''24 hours'\'' GROUP BY period_start, period_end, created_by_id ORDER BY period_start DESC;"'
```

---

## ⚠️ Риски и меры предосторожности

### Риск 1: Неправильный расчет периодов
**Митигация:** Протестировать на DEV с реальными данными

### Риск 2: Дублирование начислений
**Митигация:** В коде есть проверка `existing_entry_query` (строка 212-219)

### Риск 3: Ошибки в логике обновления
**Митигация:** Мы только добавляем переменную, не меняем бизнес-логику

### Риск 4: Несоответствие с ручными начислениями
**Митигация:** Автоматические с `created_by_id=NULL`, ручные с `created_by_id!=NULL`

---

## 📊 Критерии успеха

### DEV тестирование
- ✅ Код компилируется без ошибок
- ✅ Линтер не показывает критических ошибок
- ✅ Задача запускается вручную без ошибок
- ✅ Функция `get_payment_period_for_date` работает корректно
- ✅ Периоды рассчитываются правильно: 2.12.2025 → 10.11-16.11
- ✅ Логи содержат `entries_created` и `entries_updated`

### PROD мониторинг
- ✅ Задача запускается по расписанию (04:00 МСК)
- ✅ В логах нет ошибок `NameError`
- ✅ Начисления создаются с `created_by_id=NULL`
- ✅ Периоды соответствуют графикам

---

## 🔄 Откат (если что-то пойдет не так)

```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git log --oneline -5'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git reset --hard <PREVIOUS_COMMIT>'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml restart celery_worker celery_beat'
```

**Важно:** После отката начисления придется создавать вручную!

---

## 📝 Обновление документации

После успешного деплоя:

1. `doc/plans/roadmap.md` - добавить Итерацию 50
2. `doc/ANALYSIS_PAYROLL_BUG.md` - создать детальный анализ
3. Коммит документации

---

## ⏱️ Время выполнения

- Подготовка и изменения: ~10 минут
- Тестирование на DEV: ~15 минут
- Коммит и деплой: ~5 минут
- Мониторинг (следующий день): ~5 минут

**Итого:** ~35 минут + мониторинг

---

## ✅ Чеклист перед деплоем

- [ ] Все изменения внесены
- [ ] Код компилируется
- [ ] Линтер OK
- [ ] DEV тестирование OK
- [ ] Функция `get_payment_period_for_date` работает
- [ ] Периоды правильные
- [ ] Логи содержат нужную информацию
- [ ] Коммит создан
- [ ] План отката готов

