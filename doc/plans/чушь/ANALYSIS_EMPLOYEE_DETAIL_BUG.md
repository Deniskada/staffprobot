# Анализ проблемы: "У вас нет договоров с этим сотрудником"

## Проблема
При переходе на `/owner/employees/35` владелец получает ошибку `{"detail":"У вас нет договоров с этим сотрудником"}`, хотя договор существует.

## Корневая причина

### Рассинхрон между шаблонами и роутами

**В шаблонах используются РАЗНЫЕ ID:**
1. `list.html`, `contract_detail.html` → `employee.id` (внутренний user_id)
2. `detail.html`, `edit.html` → `employee.telegram_id`

**В роутах ожидается:**
- Параметр `employee_id` интерпретируется как `telegram_id`
- Параметр `owner_telegram_id` передается как `telegram_id` владельца

**В методе `get_employee_by_telegram_id`:**
```python
# Строка 899-900
employee_query = select(User).where(User.telegram_id == employee_id)
```
Метод ищет сотрудника по telegram_id, но получает внутренний ID!

### История изменений

**Коммит `42d253e` (Sep 7, 2025):** Создан метод `get_employee_by_telegram_id`
- Изначально работал с **внутренним ID** (`Contract.employee_id == employee_id`)
- Название было misleading

**Позже (между 42d253e и 4a30556):** Метод переделан
- Добавлен поиск по telegram_id (строки 899-900)
- Но шаблоны и вызовы не обновлены

**Коммит `4a30556` (Nov 28, 2025):** Попытка исправления
- Заменен `current_user["id"]` на `user_id` (внутренний ID владельца)
- НО метод все еще ищет owner по telegram_id!

## Примеры данных

### Сотрудник в БД:
```sql
id | telegram_id | first_name | last_name | contract_id | owner_id | employee_id 
35 |  1354496974 | Павел      | Абакумов  |          15 |        7 |          35
```

### Проблемный сценарий:
1. URL: `/owner/employees/35` → `employee_id = 35` (внутренний ID)
2. Метод ищет: `User.telegram_id == 35` → **НЕ НАЙДЕН** (telegram_id = 1354496974)
3. Результат: "У вас нет договоров с этим сотрудником"

## План исправления

### Этап 1: Аудит использования employee ID
- [ ] Найти все места, где создаются ссылки на `/owner/employees/{id}`
- [ ] Найти все места, где создаются ссылки на `/manager/employees/{id}`
- [ ] Определить единый подход: использовать **внутренний user_id**

### Этап 2: Переименование и исправление метода
- [ ] Переименовать `get_employee_by_telegram_id` → `get_employee_by_id`
- [ ] Изменить параметры:
  - `employee_id: int` → внутренний user_id сотрудника
  - `owner_id: int` → внутренний user_id владельца (НЕ telegram_id)
- [ ] Убрать поиск по telegram_id (строки 891-904)
- [ ] Сразу использовать переданные внутренние IDs

### Этап 3: Обновление роутов
- [ ] `/owner/employees/{employee_id}` → использовать внутренний ID
- [ ] `/owner/employees/{employee_id}/edit` → использовать внутренний ID
- [ ] `/manager/employees/{employee_id}` → проверить и исправить
- [ ] Обновить вызовы метода: передавать `user_id`, а не `current_user["id"]`

### Этап 4: Унификация шаблонов
- [ ] Везде использовать `employee.id` (внутренний)
- [ ] Исправить `detail.html`: `employee.telegram_id` → `employee.id`
- [ ] Исправить `edit.html`: `employee.telegram_id` → `employee.id`
- [ ] Проверить шаблоны manager

### Этап 5: Проверка затронутых процессов
- [ ] Просмотр карточки сотрудника (owner, manager)
- [ ] Редактирование сотрудника (owner, manager)
- [ ] Список сотрудников (ссылки на детали)
- [ ] Карточка договора (ссылки на сотрудника)
- [ ] Календарь (если есть ссылки на сотрудников)
- [ ] Смены (если есть ссылки на сотрудников)
- [ ] Расчетные листы (если есть ссылки на сотрудников)

### Этап 6: Тестирование
- [ ] Dev: просмотр карточки сотрудника
- [ ] Dev: редактирование сотрудника
- [ ] Dev: переходы из списка, договоров, календаря
- [ ] Prod: smoke test всех сценариев

### Этап 7: Документирование
- [ ] Обновить `DOCUMENTATION_RULES.md`
- [ ] Обновить `roadmap.md` (добавить как фикс-итерацию)
- [ ] Создать правило: "Все ссылки на сотрудников используют внутренний user_id"

## Затронутые файлы

### Сервисы:
- `apps/web/services/contract_service.py` → метод `get_employee_by_telegram_id`

### Роуты:
- `apps/web/routes/owner.py` → `/employees/{employee_id}`, `/employees/{employee_id}/edit`
- `apps/web/routes/manager.py` → проверить аналогичные роуты

### Шаблоны:
- `apps/web/templates/owner/employees/list.html` → `employee.id` ✅
- `apps/web/templates/owner/employees/detail.html` → `employee.telegram_id` ❌
- `apps/web/templates/owner/employees/edit.html` → `employee.telegram_id` ❌
- `apps/web/templates/owner/employees/contract_detail.html` → `employee.id` ✅
- `apps/web/templates/manager/employees/*` → проверить все

## Рекомендации

1. **ВСЕГДА использовать внутренний user_id** для ссылок на сотрудников
2. **НИКОГДА не использовать telegram_id** в URL
3. **Соблюдать правила `user_id_handling.mdc`** во всех сервисах
4. **Добавить проверку** в CI/CD: искать `current_user["id"]` в передаче параметров

## Следующие шаги

1. Дождаться подтверждения пользователя
2. Реализовать план поэтапно
3. Тестировать каждый этап на dev
4. Деплой на prod только после полного тестирования

