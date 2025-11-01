# Анализ проблемы: "Раннее закрытие" для всех объектов

**Дата:** 2025-11-01  
**Проблема:** На проде все объекты закрыты, но для всех в дашборде владельца показывается статус "Раннее закрытие ХХ мин"

## 🔍 АНАЛИЗ КОДА

### Логика расчёта раннего закрытия

**Файл:** `apps/web/routes/owner.py`  
**Строки:** 331-343

```python
# Проверка закрытия (как было)
if last_shift.end_time and last_shift.status == 'completed' and not active_shifts_on_object:
    naive_expected_close = datetime.combine(today_local, obj.closing_time)
    expected_close = timezone_helper.local_tz.localize(naive_expected_close)
    actual_close_local = timezone_helper.utc_to_local(last_shift.end_time)
    early_minutes = int((expected_close - actual_close_local).total_seconds() / 60)
    if early_minutes > 5:
        work_status = 'early_closing'
        work_early = early_minutes
        work_employee = f"{last_shift.user.first_name} {last_shift.user.last_name}" if last_shift.user else "Неизвестный"
    else:
        work_status = 'closed'
        work_employee = f"{last_shift.user.first_name} {last_shift.user.last_name}" if last_shift.user else "Неизвестный"
```

### Определение переменных

**Строка 146:**
```python
today_local = timezone_helper.utc_to_local(datetime.now(timezone.utc)).date()
```
- `today_local` = **сегодняшняя дата** (например, 2025-11-01)

**Строка 287:**
```python
last_shift = max(shifts_today, key=lambda s: s.end_time or s.start_time)
```
- `last_shift` = последняя смена из `shifts_today` (смены на сегодня)
- `shifts_today` фильтруются по строкам 179-207

**Строка 333:**
```python
naive_expected_close = datetime.combine(today_local, obj.closing_time)
```
- `expected_close` = ожидаемое время закрытия для **СЕГОДНЯШНЕГО дня**

**Строка 335:**
```python
actual_close_local = timezone_helper.utc_to_local(last_shift.end_time)
```
- `actual_close_local` = фактическое время закрытия последней смены (может быть вчера)

## 🐛 ПРОБЛЕМА

### Сценарий возникновения бага:

1. **Объект закрылся вчера (31.10.2025) в 22:00**
2. **Сегодня (01.11.2025) нет смен** - `shifts_today = []`
3. **НО:** код пытается обработать смены на сегодня, а если их нет, то `shifts_today` пустой
4. **НО:** если есть смены на сегодня, которые уже закрыты, то `last_shift` = последняя закрытая смена
5. **НО:** если `last_shift.end_time` относится к **вчерашнему дню**, а `expected_close` вычисляется для **сегодняшнего дня**, то:
   - `expected_close` = 2025-11-01 22:00 (сегодня)
   - `actual_close_local` = 2025-10-31 22:00 (вчера)
   - `early_minutes = (2025-11-01 22:00 - 2025-10-31 22:00) = 24 часа = 1440 минут` ❌

### Второй сценарий:

1. **Объект закрылся сегодня утром (01.11.2025) в 10:00**
2. **Ожидаемое закрытие** = 01.11.2025 22:00 (сегодня вечером)
3. **Фактическое закрытие** = 01.11.2025 10:00 (сегодня утром)
4. **early_minutes = (22:00 - 10:00) = 12 часов = 720 минут** ✅ (правильно, но объект закрылся слишком рано)

### Третий сценарий (ГЛАВНАЯ ПРОБЛЕМА):

1. **Объект закрылся вчера в 22:00**
2. **Сегодня нет смен** - `shifts_today = []`
3. **НО:** запрос `shifts_query` (строки 179-207) фильтрует смены по:
   - `Shift.planned_start >= start_of_day_utc` (начало сегодняшнего дня)
   - `Shift.planned_start < end_of_day_utc` (конец сегодняшнего дня)
4. **Если вчерашняя смена НЕ попадает в этот фильтр**, то `shifts_today = []`, и проверка раннего закрытия **не выполняется**
5. **НО:** если `last_shift` всё-таки найдена (из вчерашних смен), то сравнение идёт с **сегодняшним `expected_close`** → огромная разница

## 🔎 ДЕТАЛЬНЫЙ АНАЛИЗ

### Проблема в логике:

**Строка 287:**
```python
last_shift = max(shifts_today, key=lambda s: s.end_time or s.start_time)
```

Если `shifts_today = []` (нет смен на сегодня), то:
- `last_shift` **не определена** → код не дойдёт до проверки закрытия (строка 332)
- **НО:** если есть смены на сегодня, которые уже закрыты, то `last_shift` может быть сменой, которая закрылась **раньше ожидаемого времени закрытия для сегодняшнего дня**

### Главная проблема:

**Строка 333:**
```python
naive_expected_close = datetime.combine(today_local, obj.closing_time)
```

**Используется `today_local` (сегодняшняя дата) для всех случаев!**

Если `last_shift.end_time` относится к **вчерашнему дню**, то:
- `expected_close` = сегодня 22:00
- `actual_close_local` = вчера 22:00
- Разница = **24 часа** ❌

## ✅ ПРАВИЛЬНАЯ ЛОГИКА

### Вариант 1: Использовать дату закрытия смены

```python
if last_shift.end_time and last_shift.status == 'completed' and not active_shifts_on_object:
    actual_close_local = timezone_helper.utc_to_local(last_shift.end_time)
    close_date_local = actual_close_local.date()  # Дата закрытия смены
    naive_expected_close = datetime.combine(close_date_local, obj.closing_time)
    expected_close = timezone_helper.local_tz.localize(naive_expected_close)
    early_minutes = int((expected_close - actual_close_local).total_seconds() / 60)
    if early_minutes > 5:
        work_status = 'early_closing'
```

### Вариант 2: Проверять, что смена относится к сегодняшнему дню

```python
if last_shift.end_time and last_shift.status == 'completed' and not active_shifts_on_object:
    actual_close_local = timezone_helper.utc_to_local(last_shift.end_time)
    close_date_local = actual_close_local.date()
    
    # Проверяем только для сегодняшних смен
    if close_date_local == today_local:
        naive_expected_close = datetime.combine(today_local, obj.closing_time)
        expected_close = timezone_helper.local_tz.localize(naive_expected_close)
        early_minutes = int((expected_close - actual_close_local).total_seconds() / 60)
        if early_minutes > 5:
            work_status = 'early_closing'
        else:
            work_status = 'closed'
    else:
        # Для вчерашних смен не показываем статус работы (или показываем "Закрыт")
        work_status = 'closed'
```

## 📊 ВЫВОД

**Проблема:** Используется `today_local` (сегодняшняя дата) для вычисления `expected_close`, даже если `last_shift.end_time` относится к вчерашнему дню.

**Результат:** Для объектов, которые закрылись вчера, показывается "Раннее закрытие" с огромным количеством минут (почти 24 часа), т.к.:
- `expected_close` = сегодня 22:00
- `actual_close_local` = вчера 22:00
- Разница = 1440 минут (24 часа)

**Решение:** Использовать дату закрытия смены (`actual_close_local.date()`) вместо `today_local` для вычисления `expected_close`, либо проверять, что смена относится к сегодняшнему дню перед расчётом раннего закрытия.

---

**Статус:** ✅ **ПРОБЛЕМА ОПРЕДЕЛЕНА**

