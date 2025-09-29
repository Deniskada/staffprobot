# Система часовых поясов в StaffProBot

## 🌍 Обзор

StaffProBot поддерживает работу с различными часовыми поясами для корректного отображения времени смен и автоматических задач. Каждый объект может иметь свой часовой пояс, что позволяет работать с объектами в разных временных зонах.

## 🎯 Основные возможности

- **Часовой пояс объекта** - каждый объект может иметь свой часовой пояс
- **Автоматическая конвертация** - время автоматически конвертируется в локальный часовой пояс объекта
- **Поддержка популярных зон** - Москва, Лондон, Нью-Йорк, Лос-Анджелес, Токио, Шанхай, Сидней
- **Fallback на UTC** - если часовой пояс не указан, используется UTC
- **Консистентность** - время всегда отображается в правильном часовом поясе

## 🛠️ Техническая реализация

### Модель данных

```python
class Object(Base):
    # ... другие поля ...
    timezone = Column(String(50), nullable=True, default="Europe/Moscow")
```

### Утилиты

#### WebTimezoneHelper
```python
# apps/web/utils/timezone_utils.py
class WebTimezoneHelper:
    @staticmethod
    def format_datetime_with_timezone(utc_datetime, timezone_str, format_str):
        """Форматирует UTC время в локальное время объекта"""
        
    @staticmethod
    def format_time_with_timezone(utc_datetime, timezone_str, format_str):
        """Форматирует только время (без даты) в локальном часовом поясе"""
```

#### TimezoneHelper
```python
# core/utils/timezone_helper.py
class TimezoneHelper:
    def utc_to_local(self, utc_datetime, timezone_str):
        """Конвертирует UTC время в локальное время"""
        
    def local_to_utc(self, local_datetime, timezone_str):
        """Конвертирует локальное время в UTC"""
        
    def format_local_time(self, utc_datetime, timezone_str, format_str):
        """Форматирует UTC время как локальное время"""
```

## 📋 Поддерживаемые часовые пояса

| Часовой пояс | Описание | UTC смещение | Летнее время |
|--------------|----------|--------------|--------------|
| Europe/Moscow | Москва | UTC+3 | Нет |
| Europe/London | Лондон | UTC+0/+1 | Да |
| America/New_York | Нью-Йорк | UTC-5/-4 | Да |
| America/Los_Angeles | Лос-Анджелес | UTC-8/-7 | Да |
| Asia/Tokyo | Токио | UTC+9 | Нет |
| Asia/Shanghai | Шанхай | UTC+8 | Нет |
| Australia/Sydney | Сидней | UTC+10/+11 | Да |

## 🔧 Настройка часового пояса

### 1. При создании объекта

В интерфейсе создания объекта выберите часовой пояс из выпадающего списка:

```html
<select class="form-select" id="timezone" name="timezone" required>
    <option value="Europe/Moscow">Москва (UTC+3)</option>
    <option value="Europe/London">Лондон (UTC+0/+1)</option>
    <option value="America/New_York">Нью-Йорк (UTC-5/-4)</option>
    <!-- ... другие опции ... -->
</select>
```

### 2. При редактировании объекта

В интерфейсе редактирования объекта измените часовой пояс:

1. Перейдите в "Объекты" → выберите объект → "Редактировать"
2. В разделе "Часовой пояс" выберите нужную временную зону
3. Сохраните изменения

### 3. По умолчанию

Если часовой пояс не указан, используется `Europe/Moscow` (UTC+3).

## 📊 Отображение времени

### В веб-интерфейсе

Время автоматически конвертируется в часовой пояс объекта:

```python
# В роутах
"start_time": web_timezone_helper.format_datetime_with_timezone(
    shift.start_time, 
    shift.object.timezone if shift.object else 'Europe/Moscow'
)
```

### В боте

Время конвертируется в часовой пояс пользователя:

```python
# В обработчиках бота
user_timezone = timezone_helper.get_user_timezone(user_id)
local_start_time = timezone_helper.format_local_time(start_time_utc, user_timezone)
```

### В автоматических задачах

Автоматические задачи учитывают часовой пояс объекта:

```python
# В auto_close_shifts
if hasattr(shift.object, 'timezone') and shift.object.timezone:
    object_tz = pytz.timezone(shift.object.timezone)
    end_time = object_tz.localize(end_time).astimezone(pytz.UTC)
```

## 🔄 Миграция данных

### Добавление поля timezone

```sql
-- Миграция 9e47662cd158
ALTER TABLE objects ADD COLUMN timezone VARCHAR(50) DEFAULT 'Europe/Moscow';
```

### Обновление существующих объектов

```python
# Обновить все объекты без часового пояса
UPDATE objects SET timezone = 'Europe/Moscow' WHERE timezone IS NULL;
```

## 🧪 Тестирование

### Unit тесты

```python
def test_timezone_conversion():
    """Тест конвертации часовых поясов"""
    helper = WebTimezoneHelper()
    
    # UTC время
    utc_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
    
    # Конвертация в московское время
    moscow_time = helper.format_datetime_with_timezone(
        utc_time, 'Europe/Moscow', '%Y-%m-%d %H:%M'
    )
    
    assert moscow_time == "2024-01-01 15:00"  # UTC+3
```

### Интеграционные тесты

```python
def test_object_timezone_display():
    """Тест отображения времени с учетом часового пояса объекта"""
    # Создать объект с часовым поясом
    object = create_object(timezone='America/New_York')
    
    # Создать смену
    shift = create_shift(object_id=object.id, start_time=utc_time)
    
    # Проверить отображение времени
    response = client.get(f"/owner/shifts/{shift.id}")
    assert "2024-01-01 07:00" in response.text  # UTC-5
```

## 🚨 Устранение неполадок

### Проблема: Время отображается в UTC

**Причина**: Не указан часовой пояс объекта или ошибка в конвертации

**Решение**:
1. Проверить поле `timezone` в объекте
2. Убедиться, что используется `WebTimezoneHelper`
3. Проверить логи на ошибки конвертации

### Проблема: Ошибка "Unknown timezone"

**Причина**: Неверный часовой пояс в базе данных

**Решение**:
1. Проверить корректность часового пояса в БД
2. Использовать только поддерживаемые часовые пояса
3. Добавить fallback на часовой пояс по умолчанию

### Проблема: Время не конвертируется

**Причина**: Передается строка вместо datetime объекта

**Решение**:
1. Проверить тип данных в `WebTimezoneHelper`
2. Убедиться, что время в UTC формате
3. Добавить проверку типа данных

## 📚 Дополнительные ресурсы

- [pytz документация](https://pythonhosted.org/pytz/)
- [Список часовых поясов](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
- [UTC конвертер](https://www.timeanddate.com/worldclock/converter.html)

## 🔄 Обновления

### v1.0.0 (2024-09-14)
- ✅ Добавлена поддержка часовых поясов для объектов
- ✅ Создан WebTimezoneHelper для веб-интерфейса
- ✅ Обновлен TimezoneHelper для бота
- ✅ Добавлено поле timezone в модель Object
- ✅ Реализована автоматическая конвертация времени
- ✅ Добавлен интерфейс выбора часового пояса

### Планируемые улучшения
- 🔄 Поддержка пользовательских часовых поясов
- 🔄 Автоматическое определение часового пояса по координатам
- 🔄 Уведомления о смене часового пояса
- 🔄 История изменений часового пояса объекта
