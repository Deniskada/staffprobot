# Правила переноса кода в StaffProBot

## 🎯 Основной принцип

**При переносе рабочего кода изменяй ТОЛЬКО пути и импорты. НЕ ТРОГАЙ логику!**

## 📋 Обязательные правила переноса

### ✅ ЧТО НУЖНО МЕНЯТЬ

1. **Пути в роутах**
   ```python
   # ❌ Старый путь
   return templates.TemplateResponse("shifts/list.html", {...})
   
   # ✅ Новый путь
   return templates.TemplateResponse("owner/shifts/list.html", {...})
   ```

2. **Импорты и зависимости**
   ```python
   # ❌ Старые импорты
   from apps.web.middleware.auth_middleware import require_owner_or_superadmin
   
   # ✅ Новые импорты  
   from apps.web.dependencies import get_current_user_dependency, require_role
   ```

3. **Ссылки в шаблонах**
   ```html
   <!-- ❌ Старые ссылки -->
   <a href="/shifts/{{ shift.id }}">Детали</a>
   
   <!-- ✅ Новые ссылки -->
   <a href="/owner/shifts/{{ shift.id }}">Детали</a>
   ```

4. **Базовые шаблоны**
   ```html
   <!-- ❌ Старый базовый шаблон -->
   {% extends "base.html" %}
   
   <!-- ✅ Новый базовый шаблон -->
   {% extends "owner/base_owner.html" %}
   ```

### ❌ ЧТО НЕ НУЖНО МЕНЯТЬ

1. **Структуру данных**
   ```python
   # ✅ ПРАВИЛЬНО - оставляем как есть
   all_shifts.append({
       'id': shift.id,
       'user': shift.user,           # Объект, не строка!
       'object': shift.object,       # Объект, не строка!
       'start_time': shift.start_time, # datetime, не строка!
       'status': shift.status
   })
   
   # ❌ НЕПРАВИЛЬНО - не форматируем в Python
   all_shifts.append({
       'id': shift.id,
       'user_name': f"{shift.user.first_name} {shift.user.last_name}",
       'object_name': shift.object.name,
       'start_time': shift.start_time.strftime('%Y-%m-%d %H:%M')
   })
   ```

2. **Логику работы с данными**
   ```python
   # ✅ ПРАВИЛЬНО - копируем точно
   for schedule in schedules:
       all_shifts.append({
           'start_time': schedule.planned_start,  # Как в оригинале
           'end_time': schedule.planned_end       # Как в оригинале
       })
   ```

3. **Имена полей модели**
   ```python
   # ✅ ПРАВИЛЬНО - используем реальные поля модели
   'start_time': schedule.planned_start,  # Поле модели ShiftSchedule
   'end_time': schedule.planned_end       # Поле модели ShiftSchedule
   ```

4. **Алгоритмы и вычисления**
   ```python
   # ✅ ПРАВИЛЬНО - копируем алгоритм точно
   stats = {
       'total': total_shifts,
       'active': len([s for s in all_shifts if s['status'] == 'active']),
       'planned': len([s for s in all_shifts if s['type'] == 'schedule']),  # Как в оригинале
       'completed': len([s for s in all_shifts if s['status'] == 'completed'])
   }
   ```

## 🔄 Процедура переноса

### Шаг 1: Копирование файлов
```bash
cp apps/web/routes/original.py apps/web/routes/owner_original.py
cp -r apps/web/templates/original/* apps/web/templates/owner/original/
```

### Шаг 2: Изменение путей в роутах
- Заменить пути к шаблонам: `"original/"` → `"owner/original/"`
- НЕ МЕНЯТЬ структуру данных, передаваемых в шаблон

### Шаг 3: Обновление шаблонов
- Заменить базовый шаблон: `"base.html"` → `"owner/base_owner.html"`
- Заменить все ссылки: `/original/` → `/owner/original/`
- НЕ МЕНЯТЬ логику отображения данных в шаблонах

### Шаг 4: Интеграция в основной роут
- Скопировать роуты в `apps/web/routes/owner.py`
- Обновить импорты и dependencies
- НЕ МЕНЯТЬ логику роутов

### Шаг 5: Тестирование
- Проверить, что страницы загружаются
- Убедиться, что данные отображаются корректно
- НЕ ИСПРАВЛЯТЬ "работающий" код

## 🚨 Критические ошибки

### ❌ Ошибка 1: Изменение структуры данных
```python
# НЕПРАВИЛЬНО - форматирование в Python
'start_time': shift.start_time.strftime('%Y-%m-%d %H:%M')

# ПРАВИЛЬНО - передача объекта в шаблон
'start_time': shift.start_time
```

### ❌ Ошибка 2: Изменение имен полей
```python
# НЕПРАВИЛЬНО - придумывание новых имен
'user_name': f"{user.first_name} {user.last_name}"

# ПРАВИЛЬНО - использование оригинальной структуры
'user': user
```

### ❌ Ошибка 3: "Улучшение" логики
```python
# НЕПРАВИЛЬНО - изменение алгоритма
'planned': len([s for s in all_shifts if s['status'] == 'planned'])

# ПРАВИЛЬНО - копирование оригинала
'planned': len([s for s in all_shifts if s['type'] == 'schedule'])
```

## 💡 Принцип "Не сломай работающее"

> **"If it ain't broke, don't fix it"**

- Рабочий код уже протестирован
- Шаблоны знают, как обрабатывать данные
- Форматирование происходит на уровне представления
- Изменение логики = риск поломки

## 🎯 Контрольные вопросы

Перед коммитом спроси себя:

1. **Изменил ли я структуру данных?** → Если да, откати изменения
2. **Форматирую ли я данные в Python?** → Если да, убери форматирование
3. **Использую ли я оригинальные имена полей?** → Если нет, исправь
4. **Копирую ли я логику точно?** → Если нет, перепроверь оригинал

## 📚 Связанные документы

- [Правила разработки](conventions.mdc) - общие принципы кодирования
- [Техническое видение](vision.md) - архитектура проекта
- [Правила миграций](migrations.mdc) - работа с БД и Docker

---

**Помни**: При переносе кода твоя задача - **переместить**, а не **переписать**!
