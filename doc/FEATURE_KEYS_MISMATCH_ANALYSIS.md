# Анализ: Несоответствие ключей фич между кодом и БД

**Дата:** 29.10.2025  
**Ветка:** feature/rules-tasks-incidents  
**Проблема:** Меню "Задачи" не отображается при включённой tasks_v2

---

## 🔍 Корневая причина

### В БД сохранены СТАРЫЕ ключи фич (main):
```sql
SELECT user_id, enabled_features FROM owner_profiles WHERE user_id = 7;

user_id | enabled_features
--------|----------------------------------------------------------
7       | ["telegram_bot", "notifications", "basic_reports", 
        |  "shared_calendar", "payroll", "bonuses_and_penalties", 
        |  "shift_tasks"]
```

### В коде используются НОВЫЕ ключи (feature/rules-tasks-incidents):
```python
# core/config/features.py
SYSTEM_FEATURES_REGISTRY = {
    'telegram_bot': {...},           # ✅ совпадает
    'notifications': {...},          # ✅ совпадает
    'basic_reports': {...},          # ✅ совпадает
    'shared_calendar': {...},        # ✅ совпадает
    'payroll': {...},                # ✅ совпадает
    'contract_templates': {...},     # ⚠️ новая
    'rules_engine': {...},           # ❌ было: bonuses_and_penalties
    'tasks_v2': {...},               # ❌ было: shift_tasks
    'incidents': {...},              # ⚠️ новая
    'analytics': {...}               # ⚠️ новая
}
```

---

## 🐛 Что сломалось

### 1. Меню "Задачи" не отображается
```html
<!-- apps/web/templates/owner/base_owner.html:286 -->
{% if enabled_features | is_menu_visible('tasks_menu') %}
    <!-- Задачи -->
{% endif %}
```

**Проверка:**
```python
# core/config/menu_config.py:45
'tasks_menu': ['tasks_v2'],  # Требует tasks_v2

# Но в БД:
enabled_features = ["shift_tasks"]  # ❌ Старый ключ

# Результат: tasks_menu не показывается
```

### 2. Меню "Штрафы и премии" не отображается
```html
<!-- apps/web/templates/owner/base_owner.html:252 -->
{% if enabled_features | is_menu_visible('penalties_menu') %}
    <!-- Премии и штрафы -->
{% endif %}
```

**Проверка:**
```python
# core/config/menu_config.py:39
'penalties_menu': ['rules_engine'],  # Требует rules_engine

# Но в БД:
enabled_features = ["bonuses_and_penalties"]  # ❌ Старый ключ

# Результат: penalties_menu не показывается
```

### 3. Уведомления (НЕ сломано, но требует уточнения)
```html
<!-- apps/web/templates/owner/base_owner.html:380 -->
{% if enabled_features | is_menu_visible('notifications_settings') %}
    <a href="/owner/notifications">Уведомления</a>
{% endif %}
```

**Проверка:**
```python
# core/config/menu_config.py:58
'notifications_settings': ['notifications'],  # Требует notifications

# В БД:
enabled_features = ["notifications"]  # ✅ Совпадает!

# Результат: notifications_settings ДОЛЖЕН показываться
```

---

## 📊 Маппинг старых → новых ключей

| Старый ключ (main)      | Новый ключ (feature)  | Статус         |
|-------------------------|-----------------------|----------------|
| telegram_bot            | telegram_bot          | ✅ Совпадает   |
| notifications           | notifications         | ✅ Совпадает   |
| basic_reports           | basic_reports         | ✅ Совпадает   |
| shared_calendar         | shared_calendar       | ✅ Совпадает   |
| payroll                 | payroll               | ✅ Совпадает   |
| bonuses_and_penalties   | rules_engine          | ❌ Переименован |
| shift_tasks             | tasks_v2              | ❌ Переименован |
| —                       | contract_templates    | ⚠️ Новая       |
| —                       | incidents             | ⚠️ Новая       |
| —                       | analytics             | ⚠️ Новая       |

---

## 💡 Решения

### ✅ Вариант 1: Миграция данных + Fallback (РЕКОМЕНДУЕТСЯ)

**Плюсы:** Чистое решение, поддержка обратной совместимости  
**Минусы:** Требует миграции БД и изменений кода

#### 1.1. SQL миграция для обновления БД:
```sql
-- Обновить все owner_profiles
UPDATE owner_profiles 
SET enabled_features = (
    SELECT jsonb_agg(
        CASE 
            WHEN elem::text = '"bonuses_and_penalties"' THEN '"rules_engine"'::jsonb
            WHEN elem::text = '"shift_tasks"' THEN '"tasks_v2"'::jsonb
            ELSE elem
        END
    )
    FROM jsonb_array_elements(enabled_features::jsonb) elem
)::json
WHERE enabled_features::text LIKE '%bonuses_and_penalties%' 
   OR enabled_features::text LIKE '%shift_tasks%';
```

#### 1.2. Добавить fallback в MenuConfig:
```python
# core/config/menu_config.py

# Маппинг старых ключей на новые (для обратной совместимости)
LEGACY_FEATURE_MAPPING = {
    'bonuses_and_penalties': 'rules_engine',
    'shift_tasks': 'tasks_v2',
}

@classmethod
def normalize_features(cls, features: List[str]) -> List[str]:
    """Преобразовать старые ключи в новые."""
    normalized = []
    for feature in features:
        # Если есть маппинг - заменяем
        normalized_key = cls.LEGACY_FEATURE_MAPPING.get(feature, feature)
        normalized.append(normalized_key)
    return normalized

@classmethod
def is_menu_item_visible(cls, menu_item_key: str, enabled_features: List[str]) -> bool:
    # Нормализуем фичи (преобразуем старые ключи)
    normalized_features = cls.normalize_features(enabled_features)
    
    # Дальше существующая логика...
```

---

### ⚠️ Вариант 2: Откатить переименование (быстро, но грязно)

**Плюсы:** Не требует миграции БД  
**Минусы:** Откат изменений, несогласованность с документацией

Вернуть в `features.py` и `menu_config.py`:
```python
'bonuses_and_penalties': {...},  # вместо rules_engine
'shift_tasks': {...},            # вместо tasks_v2
```

---

### ❌ Вариант 3: Только миграция БД (неполное)

**Плюсы:** Чистое решение  
**Минусы:** Сломает существующие установки без обновления БД

Только SQL миграция без fallback - опасно для прода!

---

## 🎯 Рекомендуемый план действий

### Этап 1: Добавить fallback (безопасно, быстро)
1. Обновить `MenuConfig.is_menu_item_visible` с нормализацией
2. Протестировать на dev
3. Меню заработает с любыми ключами

### Этап 2: Миграция БД на dev
1. Применить SQL UPDATE для owner_profiles
2. Проверить что меню продолжает работать
3. Проверить что старые ключи автоматически преобразуются

### Этап 3: Документация
1. Обновить `menu_structure.md` с правильными ключами
2. Добавить примечание о fallback для совместимости

### Этап 4: Деплой на prod
1. Сначала деплой кода с fallback (безопасно)
2. Затем применить миграцию БД
3. Мониторинг меню на проде

---

## 🔧 Скрипт миграции для dev

```bash
# Применить на dev БД
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev << 'EOF'
BEGIN;

-- Показать текущее состояние
SELECT user_id, enabled_features FROM owner_profiles;

-- Обновить ключи
UPDATE owner_profiles 
SET enabled_features = (
    SELECT jsonb_agg(
        CASE 
            WHEN elem::text = '"bonuses_and_penalties"' THEN '"rules_engine"'::jsonb
            WHEN elem::text = '"shift_tasks"' THEN '"tasks_v2"'::jsonb
            ELSE elem
        END
    )
    FROM jsonb_array_elements(enabled_features::jsonb) elem
)::json
WHERE enabled_features::text LIKE '%bonuses_and_penalties%' 
   OR enabled_features::text LIKE '%shift_tasks%';

-- Показать обновлённое состояние
SELECT user_id, enabled_features FROM owner_profiles;

COMMIT;
EOF
```

---

## ✅ Критерии готовности

- [ ] Fallback добавлен в MenuConfig
- [ ] SQL миграция протестирована на dev
- [ ] Меню "Задачи" отображается при shift_tasks или tasks_v2
- [ ] Меню "Штрафы и премии" отображается при bonuses_and_penalties или rules_engine
- [ ] Уведомления отображаются в Настройках (уже работает)
- [ ] Документация обновлена
- [ ] Код готов к деплою на prod

---

**Автор:** AI Assistant  
**Статус:** Требуется решение пользователя

