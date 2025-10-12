# Организационная структура (OrgStructureUnit)

## Описание

Древовидная структура подразделений для организации объектов и наследования финансовых настроек. Позволяет централизованно управлять системой оплаты, графиком выплат и настройками штрафов.

## Модель данных

**Таблица:** `org_structure_units`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `owner_id` | Integer | FK → users.id (владелец) |
| `parent_id` | Integer | FK → org_structure_units.id (родитель, nullable) |
| `name` | String(255) | Название подразделения |
| `description` | Text | Описание |
| `payment_system_id` | Integer | FK → payment_systems.id (nullable) |
| `payment_schedule_id` | Integer | FK → payment_schedules.id (nullable) |
| `inherit_late_settings` | Boolean | Наследовать настройки штрафов |
| `late_threshold_minutes` | Integer | Допустимое опоздание (мин) |
| `late_penalty_per_minute` | Numeric(10,2) | Стоимость минуты штрафа (₽) |
| `level` | Integer | Уровень в иерархии (0 = корень) |
| `is_active` | Boolean | Активность |
| `created_at` | DateTime | Дата создания |
| `updated_at` | DateTime | Дата обновления |

## Структура дерева

### Принципы
- **Self-referential:** `parent_id` указывает на другую запись в этой же таблице
- **Корневое подразделение:** `parent_id = NULL`, `level = 0`
- **Дочерние подразделения:** `parent_id != NULL`, `level = parent.level + 1`

### Пример структуры
```
Компания (level=0)
├── Отдел продаж (level=1)
│   ├── Московский офис (level=2)
│   └── СПБ офис (level=2)
└── Отдел доставки (level=1)
    └── Курьерская служба (level=2)
```

## Наследование настроек

### 1. Система оплаты труда
```python
# Если у подразделения указана своя система
if org_unit.payment_system_id is not None:
    return org_unit.payment_system_id

# Иначе наследуем от родителя (рекурсивно)
if org_unit.parent is not None:
    return org_unit.parent.get_inherited_payment_system_id()

# Иначе None (используется дефолт)
return None
```

### 2. График выплат
Аналогично системе оплаты - рекурсивное наследование от родителя.

### 3. Настройки штрафов за опоздание
```python
# Если inherit_late_settings = False и настройки указаны
if not org_unit.inherit_late_settings and org_unit.late_threshold_minutes is not None:
    return {
        'threshold_minutes': org_unit.late_threshold_minutes,
        'penalty_per_minute': org_unit.late_penalty_per_minute,
        'inherited_from': None
    }

# Иначе наследуем от родителя
if org_unit.parent is not None:
    return org_unit.parent.get_inherited_late_settings()

# Иначе None (используются константы)
return {'threshold_minutes': None, 'penalty_per_minute': None}
```

## Связь с объектами

```python
# У объекта
object.org_unit_id = 5  # Привязка к подразделению

# Объект наследует настройки
effective_payment_system = object.get_effective_payment_system_id()
# 1. Если object.payment_system_id != None → используем его
# 2. Иначе → org_unit.get_inherited_payment_system_id()
```

## Seed-данные

При создании владельца автоматически создается "Основное подразделение":
```sql
INSERT INTO org_structure_units (owner_id, name, level, is_active)
VALUES (owner_id, 'Основное подразделение', 0, true);
```

Все новые объекты по умолчанию привязываются к "Основному подразделению".

## CRUD операции

### Сервис: OrgStructureService

```python
from apps.web.services.org_structure_service import OrgStructureService

service = OrgStructureService(db)

# Создать подразделение
unit = await service.create_unit(
    owner_id=100,
    name="Отдел продаж",
    parent_id=1,  # Внутри "Основного"
    payment_system_id=3  # Повременно-премиальная
)

# Получить дерево
tree = await service.get_org_tree(owner_id=100)

# Переместить подразделение
await service.move_unit(
    unit_id=5,
    new_parent_id=2,  # Новый родитель
    owner_id=100
)

# Валидация циклов
is_valid = await service.validate_no_cycles(unit_id=5, parent_id=2)
```

## UI

### Страница `/owner/org-structure`
- Древовидный список подразделений
- Визуальные отступы по уровням
- Кнопки: "Добавить", "Редактировать", "Удалить"
- Индикация наследования (текст "Наследуется")

### Модальное окно создания
- Название, описание
- Родительское подразделение (dropdown с иерархией)
- Система оплаты (с опцией "Наследовать от родителя")
- График выплат (с опцией "Наследовать от родителя")
- Настройки штрафов (чекбокс "Наследовать")

### В формах объектов
Dropdown "Подразделение" на вкладке "Финансы":
```html
<select name="org_unit_id">
    <option value="1">Основное подразделение</option>
    <option value="2">├─ Отдел продаж</option>
    <option value="3">├─ ├─ Московский офис</option>
</select>
```

## Валидация

### Запрет циклических ссылок
```python
# Нельзя переместить подразделение в своего потомка
# unit_id=2, new_parent_id=5
# Если unit_id=2 является предком unit_id=5 → ошибка

descendants = await service._get_all_descendants(unit_id)
if new_parent_id in [d.id for d in descendants]:
    raise ValueError("Перемещение создаст циклическую ссылку")
```

### Удаление
- Нельзя удалить, если есть дочерние подразделения
- Нельзя удалить, если есть привязанные объекты
- Мягкое удаление: `is_active = False`

## Индексы

- `idx_org_units_owner_id` - для поиска по владельцу
- `idx_org_units_parent_id` - для построения дерева
- `idx_org_units_level` - для оптимизации запросов
- `idx_org_units_is_active` - для фильтрации активных

## Методы модели

```python
class OrgStructureUnit:
    def get_full_path(self) -> str:
        """Компания / Отдел продаж / Московский офис"""
        
    def is_root(self) -> bool:
        """Является ли корневым (parent_id = None)"""
        
    def calculate_level(self) -> int:
        """Рассчитать уровень в иерархии"""
        
    def get_inherited_payment_system_id(self) -> Optional[int]:
        """Получить систему оплаты с наследованием"""
        
    def get_inherited_payment_schedule_id(self) -> Optional[int]:
        """Получить график выплат с наследованием"""
        
    def get_inherited_late_settings(self) -> dict:
        """Получить настройки штрафов с наследованием"""
```

## См. также

- [Объекты](objects.md)
- [Системы оплаты](payment_system.md)
- [Начисления и выплаты](payroll.md)

