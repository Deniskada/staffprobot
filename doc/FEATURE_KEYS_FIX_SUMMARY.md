# Исправление: Несоответствие ключей фич (29.10.2025)

## ✅ Проблема решена

**Исходная проблема:**
- Меню "Задачи" не отображалось при включённой фиче
- Меню "Штрафы и премии" не отображалось при включённой фиче
- Причина: в БД хранились старые ключи (`bonuses_and_penalties`, `shift_tasks`), а код проверял новые (`rules_engine`, `tasks_v2`)

**Решение:**
1. ✅ Добавлен fallback в `MenuConfig.normalize_features()` для автоматического преобразования старых ключей в новые
2. ✅ Применена SQL миграция на dev БД для обновления ключей
3. ✅ Создан SQL скрипт для прода: `doc/MIGRATE_FEATURE_KEYS.sql`

---

## 📋 Что было сделано

### 1. Обновлён `core/config/menu_config.py`

**Добавлено:**
```python
# Маппинг старых ключей фич на новые (для обратной совместимости)
LEGACY_FEATURE_MAPPING = {
    'bonuses_and_penalties': 'rules_engine',
    'shift_tasks': 'tasks_v2',
}

@classmethod
def normalize_features(cls, features: List[str]) -> List[str]:
    """Преобразовать старые ключи фич в новые."""
    # Автоматически заменяет старые ключи на новые
```

**Изменено:**
```python
@classmethod
def is_menu_item_visible(cls, menu_item_key: str, enabled_features: List[str]) -> bool:
    # Теперь сначала нормализует ключи
    normalized_features = cls.normalize_features(enabled_features)
    # Затем проверяет видимость
```

**Результат:** Меню работает как со старыми, так и с новыми ключами!

### 2. SQL миграция на dev

**До миграции:**
```json
{
  "user_id": 7,
  "enabled_features": [
    "telegram_bot", "payroll", 
    "bonuses_and_penalties",  // ❌ старый
    "shift_tasks"             // ❌ старый
  ]
}
```

**После миграции:**
```json
{
  "user_id": 7,
  "enabled_features": [
    "telegram_bot", "payroll",
    "rules_engine",  // ✅ новый
    "tasks_v2"       // ✅ новый
  ]
}
```

**Затронуто:** 3 owner_profiles на dev

### 3. Документация

Созданы файлы:
- `doc/FEATURE_KEYS_MISMATCH_ANALYSIS.md` - подробный анализ проблемы
- `doc/MIGRATE_FEATURE_KEYS.sql` - SQL скрипт для миграции на проде
- `doc/FEATURE_KEYS_FIX_SUMMARY.md` - этот файл (резюме)

Обновлены:
- `docs/owner_profile/menu_structure.md` - актуальная таблица фич и меню

---

## 🚀 Применение на проде (при деплое)

### Шаг 1: Деплой кода с fallback (безопасно)
```bash
# Обычный деплой - fallback уже в коде
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git pull origin main'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml restart web'
```

**После этого шага:** Меню уже будет работать со старыми ключами благодаря fallback!

### Шаг 2: Применить SQL миграцию (опционально, но рекомендуется)
```bash
# Применить миграцию для обновления ключей в БД
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod < doc/MIGRATE_FEATURE_KEYS.sql'
```

### Шаг 3: Очистить кэш Redis (после миграции)
```bash
# Очистить кэш enabled_features
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec redis redis-cli --scan --pattern "enabled_features:*" | xargs docker compose -f docker-compose.prod.yml exec redis redis-cli DEL'
```

---

## 🔍 Проверка на dev

### Проверка 1: Fallback работает
```python
# Тест в Python
from core.config.menu_config import MenuConfig

old_features = ["telegram_bot", "bonuses_and_penalties", "shift_tasks"]
normalized = MenuConfig.normalize_features(old_features)
print(normalized)
# Ожидается: ["telegram_bot", "rules_engine", "tasks_v2"]

# Проверка видимости меню
is_visible = MenuConfig.is_menu_item_visible('tasks_menu', old_features)
print(is_visible)  # Ожидается: True
```

### Проверка 2: Меню отображается
1. Зайти на http://localhost:8001 под владельцем
2. Проверить наличие пунктов меню:
   - ✅ "Задачи" (tasks_menu)
   - ✅ "Штрафы и премии" (penalties_menu)
   - ✅ Настройки → Уведомления (notifications_settings)

### Проверка 3: БД обновлена
```bash
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "
  SELECT user_id, enabled_features 
  FROM owner_profiles 
  WHERE enabled_features::text LIKE '%rules_engine%' 
     OR enabled_features::text LIKE '%tasks_v2%';
"
```

Должны быть новые ключи: `rules_engine`, `tasks_v2`

---

## 📊 Маппинг всех ключей фич

| Старый ключ (main)      | Новый ключ (feature)  | Совместимость  |
|-------------------------|-----------------------|----------------|
| telegram_bot            | telegram_bot          | ✅ Совпадает   |
| notifications           | notifications         | ✅ Совпадает   |
| basic_reports           | basic_reports         | ✅ Совпадает   |
| shared_calendar         | shared_calendar       | ✅ Совпадает   |
| payroll                 | payroll               | ✅ Совпадает   |
| bonuses_and_penalties   | rules_engine          | ✅ Fallback    |
| shift_tasks             | tasks_v2              | ✅ Fallback    |
| —                       | contract_templates    | ⚠️ Новая       |
| —                       | incidents             | ⚠️ Новая       |
| —                       | analytics             | ⚠️ Новая       |

---

## ✅ Результат

**Что работает сейчас на dev:**
- ✅ Меню "Задачи" отображается
- ✅ Меню "Штрафы и премии" отображается
- ✅ Уведомления есть в Настройках
- ✅ Fallback автоматически преобразует старые ключи
- ✅ БД обновлена на новые ключи

**Что будет на проде после деплоя:**
- ✅ Код с fallback работает со старыми ключами (не ломает прод)
- ✅ После применения миграции БД обновится на новые ключи
- ✅ Старые владельцы продолжат работать без проблем

---

## 🎯 Итоговые коммиты

```
b82f45e - Исправление: fallback для старых ключей фич + SQL миграция
1361fd5 - Документация: уточнена таблица соответствия фич и меню
```

**Изменённые файлы:**
- `core/config/menu_config.py` - добавлен fallback
- `doc/MIGRATE_FEATURE_KEYS.sql` - SQL для прода
- `doc/FEATURE_KEYS_MISMATCH_ANALYSIS.md` - подробный анализ
- `docs/owner_profile/menu_structure.md` - обновлена таблица

---

**Автор:** AI Assistant  
**Дата:** 29.10.2025  
**Статус:** ✅ Готово на dev, готово к деплою на prod


