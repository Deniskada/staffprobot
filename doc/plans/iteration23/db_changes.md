# Проектирование изменений в существующих таблицах

**Дата:** 2025-10-09  
**Статус:** Завершен  
**Задача:** 0.3. Проектирование изменений в существующих таблицах

## Оглавление

1. [Таблица contracts](#1-таблица-contracts)
2. [Таблица objects](#2-таблица-objects)
3. [Миграции данных](#3-миграции-данных)
4. [Rollback план](#4-rollback-план)

---

## 1. Таблица contracts

### 1.1. Текущая структура (релевантные поля)

```sql
CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    employee_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    hourly_rate INTEGER,  -- КОПЕЙКИ! Проблема!
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    is_manager BOOLEAN DEFAULT FALSE NOT NULL,
    manager_permissions JSON,
    ...
);
```

### 1.2. Требуемые изменения

#### Изменение 1: Унификация типа hourly_rate

**Проблема:** `hourly_rate` имеет тип Integer (копейки), тогда как во всех других таблицах используется Numeric(10,2) (рубли)

**Решение:**
```sql
-- Шаг 1: Преобразование данных (копейки → рубли)
UPDATE contracts 
SET hourly_rate = hourly_rate / 100.0 
WHERE hourly_rate IS NOT NULL;

-- Шаг 2: Изменение типа
ALTER TABLE contracts 
ALTER COLUMN hourly_rate TYPE NUMERIC(10, 2) 
USING (hourly_rate::NUMERIC(10, 2));

-- Шаг 3: Обновление комментария
COMMENT ON COLUMN contracts.hourly_rate IS 'Почасовая ставка в рублях';
```

**SQLAlchemy изменение:**
```python
# Было:
hourly_rate = Column(Integer, nullable=True)  # Почасовая ставка в копейках

# Стало:
hourly_rate = Column(Numeric(10, 2), nullable=True)  # Почасовая ставка в рублях
```

#### Изменение 2: Добавление use_contract_rate

**Назначение:** Флаг приоритета ставки договора над ставками объекта/тайм-слота

**SQL:**
```sql
ALTER TABLE contracts 
ADD COLUMN use_contract_rate BOOLEAN DEFAULT FALSE NOT NULL;

CREATE INDEX idx_contracts_use_contract_rate ON contracts(use_contract_rate);

COMMENT ON COLUMN contracts.use_contract_rate IS 'Использовать ставку из договора (приоритет над объектом/тайм-слотом)';
```

**SQLAlchemy:**
```python
use_contract_rate = Column(Boolean, default=False, nullable=False, index=True)
```

#### Изменение 3: Добавление payment_system_id

**Назначение:** Связь с системой оплаты труда

**SQL:**
```sql
ALTER TABLE contracts 
ADD COLUMN payment_system_id INTEGER REFERENCES payment_systems(id) ON DELETE SET NULL;

CREATE INDEX idx_contracts_payment_system_id ON contracts(payment_system_id);

COMMENT ON COLUMN contracts.payment_system_id IS 'Система оплаты труда (по умолчанию simple_hourly)';
```

**SQLAlchemy:**
```python
payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)

# Relationship
payment_system = relationship("PaymentSystem", back_populates="contracts")
```

#### Изменение 4: Добавление payment_schedule_id

**Назначение:** Связь с графиком выплат

**SQL:**
```sql
ALTER TABLE contracts 
ADD COLUMN payment_schedule_id INTEGER REFERENCES payment_schedules(id) ON DELETE SET NULL;

CREATE INDEX idx_contracts_payment_schedule_id ON contracts(payment_schedule_id);

COMMENT ON COLUMN contracts.payment_schedule_id IS 'График выплат для сотрудника';
```

**SQLAlchemy:**
```python
payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)

# Relationship
payment_schedule = relationship("PaymentSchedule", back_populates="contracts")
```

#### Изменение 5: Обновление manager_permissions

**Назначение:** Добавить право управляющего на работу с начислениями

**Текущая структура manager_permissions (JSON):**
```json
{
  "can_create_objects": false,
  "can_manage_contracts": false,
  "can_view_all_reports": false,
  "can_manage_managers": false
}
```

**Новая структура:**
```json
{
  "can_create_objects": false,
  "can_manage_contracts": false,
  "can_view_all_reports": false,
  "can_manage_managers": false,
  "can_manage_payroll": false  // НОВОЕ ПОЛЕ
}
```

**Миграция данных:**
```sql
-- Добавить can_manage_payroll = false ко всем существующим записям
UPDATE contracts 
SET manager_permissions = jsonb_set(
    COALESCE(manager_permissions::jsonb, '{}'::jsonb),
    '{can_manage_payroll}',
    'false'::jsonb
)
WHERE is_manager = TRUE;
```

### 1.3. Итоговая структура contracts (новые/измененные поля)

```python
class Contract(Base):
    """Договор с сотрудником."""
    
    __tablename__ = "contracts"
    
    # ... существующие поля ...
    
    # ИЗМЕНЕНО: тип данных
    hourly_rate = Column(Numeric(10, 2), nullable=True)  # Было: Integer
    
    # НОВЫЕ ПОЛЯ:
    use_contract_rate = Column(Boolean, default=False, nullable=False, index=True)
    payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # ОБНОВЛЕНО: manager_permissions теперь содержит can_manage_payroll
    manager_permissions = Column(JSON, nullable=True)
    
    # ... остальные поля ...
    
    # Новые relationships
    payment_system = relationship("PaymentSystem", back_populates="contracts")
    payment_schedule = relationship("PaymentSchedule", back_populates="contracts")
```

---

## 2. Таблица objects

### 2.1. Текущая структура (релевантные поля)

```sql
CREATE TABLE objects (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    hourly_rate NUMERIC(10, 2) NOT NULL,
    shift_tasks JSONB,  -- Текущая структура не детальная
    ...
);
```

**Текущая структура shift_tasks (JSONB):**
```json
[
  "Задача 1",
  "Задача 2",
  "Задача 3"
]
```

### 2.2. Требуемые изменения

#### Изменение 1: Добавление payment_system_id

**Назначение:** Система оплаты для объекта (наследуется от org_unit или задается напрямую)

**SQL:**
```sql
ALTER TABLE objects 
ADD COLUMN payment_system_id INTEGER REFERENCES payment_systems(id) ON DELETE SET NULL;

CREATE INDEX idx_objects_payment_system_id ON objects(payment_system_id);

COMMENT ON COLUMN objects.payment_system_id IS 'Система оплаты для объекта (переопределяет org_unit)';
```

**SQLAlchemy:**
```python
payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)

# Relationship
payment_system = relationship("PaymentSystem", back_populates="objects")
```

#### Изменение 2: Добавление payment_schedule_id

**Назначение:** График выплат для объекта

**SQL:**
```sql
ALTER TABLE objects 
ADD COLUMN payment_schedule_id INTEGER REFERENCES payment_schedules(id) ON DELETE SET NULL;

CREATE INDEX idx_objects_payment_schedule_id ON objects(payment_schedule_id);

COMMENT ON COLUMN objects.payment_schedule_id IS 'График выплат для объекта (переопределяет org_unit)';
```

**SQLAlchemy:**
```python
payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)

# Relationship
payment_schedule = relationship("PaymentSchedule", back_populates="objects")
```

#### Изменение 3: Добавление org_unit_id

**Назначение:** Привязка объекта к единице организационной структуры

**SQL:**
```sql
ALTER TABLE objects 
ADD COLUMN org_unit_id INTEGER REFERENCES org_structure_units(id) ON DELETE SET NULL;

CREATE INDEX idx_objects_org_unit_id ON objects(org_unit_id);

COMMENT ON COLUMN objects.org_unit_id IS 'Единица организационной структуры (наследует payment_system_id и payment_schedule_id)';
```

**SQLAlchemy:**
```python
org_unit_id = Column(Integer, ForeignKey("org_structure_units.id", ondelete="SET NULL"), nullable=True, index=True)

# Relationship
org_unit = relationship("OrgStructureUnit", back_populates="objects")
```

#### Изменение 4: Обновление shift_tasks (JSONB)

**Проблема:** Текущая структура - простой массив строк, не содержит информацию об обязательности и удержаниях

**Новая структура shift_tasks (JSONB):**
```json
[
  {
    "task": "Проверить оборудование",
    "is_mandatory": true,
    "deduction_amount": 500
  },
  {
    "task": "Убрать помещение",
    "is_mandatory": true,
    "deduction_amount": 300
  },
  {
    "task": "Заполнить отчет",
    "is_mandatory": false,
    "deduction_amount": null
  }
]
```

**Миграция данных:**
```sql
-- Преобразование старого формата в новый
UPDATE objects 
SET shift_tasks = (
    SELECT jsonb_agg(
        jsonb_build_object(
            'task', task_text,
            'is_mandatory', false,
            'deduction_amount', null
        )
    )
    FROM jsonb_array_elements_text(shift_tasks) AS task_text
)
WHERE shift_tasks IS NOT NULL 
  AND jsonb_typeof(shift_tasks) = 'array';
```

**SQLAlchemy (без изменений типа, только комментарий):**
```python
shift_tasks = Column(JSONB, nullable=True)  # Структура: [{task, is_mandatory, deduction_amount}]
```

**Python Pydantic модель для валидации:**
```python
from pydantic import BaseModel
from typing import Optional

class ShiftTaskSchema(BaseModel):
    task: str
    is_mandatory: bool = False
    deduction_amount: Optional[float] = None
```

### 2.3. Итоговая структура objects (новые/измененные поля)

```python
class Object(Base):
    """Модель объекта."""
    
    __tablename__ = "objects"
    
    # ... существующие поля ...
    
    # ОБНОВЛЕНО: новая структура данных
    shift_tasks = Column(JSONB, nullable=True)  # [{task, is_mandatory, deduction_amount}]
    
    # НОВЫЕ ПОЛЯ:
    payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    org_unit_id = Column(Integer, ForeignKey("org_structure_units.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # ... остальные поля ...
    
    # Новые relationships
    payment_system = relationship("PaymentSystem", back_populates="objects")
    payment_schedule = relationship("PaymentSchedule", back_populates="objects")
    org_unit = relationship("OrgStructureUnit", back_populates="objects")
```

---

## 3. Миграции данных

### 3.1. Миграция contracts.hourly_rate (копейки → рубли)

**Файл:** `migrations/versions/XXXX_convert_contract_hourly_rate.py`

```python
"""Convert contracts.hourly_rate from kopecks to rubles

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-10-09

"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Шаг 1: Создать временный столбец
    op.add_column('contracts', sa.Column('hourly_rate_temp', sa.Numeric(10, 2), nullable=True))
    
    # Шаг 2: Преобразовать данные (копейки → рубли)
    op.execute("""
        UPDATE contracts 
        SET hourly_rate_temp = CAST(hourly_rate AS NUMERIC) / 100.0
        WHERE hourly_rate IS NOT NULL
    """)
    
    # Шаг 3: Удалить старый столбец
    op.drop_column('contracts', 'hourly_rate')
    
    # Шаг 4: Переименовать временный столбец
    op.alter_column('contracts', 'hourly_rate_temp', new_column_name='hourly_rate')
    
    # Шаг 5: Добавить комментарий
    op.execute("COMMENT ON COLUMN contracts.hourly_rate IS 'Почасовая ставка в рублях'")

def downgrade() -> None:
    # Обратное преобразование (рубли → копейки)
    op.add_column('contracts', sa.Column('hourly_rate_temp', sa.Integer, nullable=True))
    
    op.execute("""
        UPDATE contracts 
        SET hourly_rate_temp = CAST(hourly_rate * 100 AS INTEGER)
        WHERE hourly_rate IS NOT NULL
    """)
    
    op.drop_column('contracts', 'hourly_rate')
    op.alter_column('contracts', 'hourly_rate_temp', new_column_name='hourly_rate')
```

### 3.2. Добавление новых полей в contracts

**Файл:** `migrations/versions/XXXX_add_contract_payment_fields.py`

```python
"""Add payment fields to contracts

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-10-09

"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # use_contract_rate
    op.add_column('contracts', 
        sa.Column('use_contract_rate', sa.Boolean(), server_default='false', nullable=False)
    )
    op.create_index('idx_contracts_use_contract_rate', 'contracts', ['use_contract_rate'])
    
    # payment_system_id
    op.add_column('contracts', 
        sa.Column('payment_system_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_contracts_payment_system_id', 
        'contracts', 'payment_systems',
        ['payment_system_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_contracts_payment_system_id', 'contracts', ['payment_system_id'])
    
    # payment_schedule_id
    op.add_column('contracts', 
        sa.Column('payment_schedule_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_contracts_payment_schedule_id', 
        'contracts', 'payment_schedules',
        ['payment_schedule_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_contracts_payment_schedule_id', 'contracts', ['payment_schedule_id'])
    
    # Обновить manager_permissions для существующих управляющих
    op.execute("""
        UPDATE contracts 
        SET manager_permissions = jsonb_set(
            COALESCE(manager_permissions::jsonb, '{}'::jsonb),
            '{can_manage_payroll}',
            'false'::jsonb
        )
        WHERE is_manager = TRUE
    """)

def downgrade() -> None:
    op.drop_index('idx_contracts_payment_schedule_id')
    op.drop_constraint('fk_contracts_payment_schedule_id', 'contracts')
    op.drop_column('contracts', 'payment_schedule_id')
    
    op.drop_index('idx_contracts_payment_system_id')
    op.drop_constraint('fk_contracts_payment_system_id', 'contracts')
    op.drop_column('contracts', 'payment_system_id')
    
    op.drop_index('idx_contracts_use_contract_rate')
    op.drop_column('contracts', 'use_contract_rate')
```

### 3.3. Добавление новых полей в objects

**Файл:** `migrations/versions/XXXX_add_object_payment_fields.py`

```python
"""Add payment and org structure fields to objects

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-10-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade() -> None:
    # payment_system_id
    op.add_column('objects', 
        sa.Column('payment_system_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_objects_payment_system_id', 
        'objects', 'payment_systems',
        ['payment_system_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_objects_payment_system_id', 'objects', ['payment_system_id'])
    
    # payment_schedule_id
    op.add_column('objects', 
        sa.Column('payment_schedule_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_objects_payment_schedule_id', 
        'objects', 'payment_schedules',
        ['payment_schedule_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_objects_payment_schedule_id', 'objects', ['payment_schedule_id'])
    
    # org_unit_id
    op.add_column('objects', 
        sa.Column('org_unit_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_objects_org_unit_id', 
        'objects', 'org_structure_units',
        ['org_unit_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_objects_org_unit_id', 'objects', ['org_unit_id'])

def downgrade() -> None:
    op.drop_index('idx_objects_org_unit_id')
    op.drop_constraint('fk_objects_org_unit_id', 'objects')
    op.drop_column('objects', 'org_unit_id')
    
    op.drop_index('idx_objects_payment_schedule_id')
    op.drop_constraint('fk_objects_payment_schedule_id', 'objects')
    op.drop_column('objects', 'payment_schedule_id')
    
    op.drop_index('idx_objects_payment_system_id')
    op.drop_constraint('fk_objects_payment_system_id', 'objects')
    op.drop_column('objects', 'payment_system_id')
```

### 3.4. Миграция objects.shift_tasks

**Файл:** `migrations/versions/XXXX_update_shift_tasks_structure.py`

```python
"""Update shift_tasks structure in objects

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-10-09

"""
from alembic import op

def upgrade() -> None:
    # Преобразование старого формата в новый
    op.execute("""
        UPDATE objects 
        SET shift_tasks = (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'task', task_text::text,
                    'is_mandatory', false,
                    'deduction_amount', null
                )
            )
            FROM jsonb_array_elements_text(shift_tasks) AS task_text
        )
        WHERE shift_tasks IS NOT NULL 
          AND jsonb_typeof(shift_tasks) = 'array'
          AND (
              SELECT COUNT(*) 
              FROM jsonb_array_elements(shift_tasks) AS elem
              WHERE jsonb_typeof(elem) = 'string'
          ) > 0
    """)

def downgrade() -> None:
    # Обратное преобразование (новый формат → старый)
    op.execute("""
        UPDATE objects 
        SET shift_tasks = (
            SELECT jsonb_agg(elem->>'task')
            FROM jsonb_array_elements(shift_tasks) AS elem
        )
        WHERE shift_tasks IS NOT NULL 
          AND jsonb_typeof(shift_tasks) = 'array'
    """)
```

### 3.5. Создание "Основного подразделения" для всех владельцев

**Файл:** `scripts/create_default_org_units.py`

```python
"""
Скрипт для создания "Основного подразделения" для всех существующих владельцев.
Запускается после создания таблицы org_structure_units.
"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_async_session
from domain.entities.user import User
from domain.entities.org_structure import OrgStructureUnit
from shared.services.role_service import RoleService
from core.logging.logger import logger


async def create_default_org_units():
    """Создать основное подразделение для всех владельцев."""
    async with get_async_session() as session:
        # Получить всех пользователей с ролью owner
        role_service = RoleService(session)
        owners = await role_service.get_users_by_role("owner")
        
        created_count = 0
        
        for owner in owners:
            # Проверить, есть ли уже подразделения у владельца
            existing = await session.execute(
                select(OrgStructureUnit).where(OrgStructureUnit.owner_id == owner.id)
            )
            if existing.scalar_one_or_none():
                logger.info(f"Owner {owner.id} already has org units, skipping")
                continue
            
            # Создать основное подразделение
            default_unit = OrgStructureUnit(
                owner_id=owner.id,
                parent_id=None,
                name="Основное подразделение",
                description="Автоматически созданное подразделение по умолчанию",
                level=0,
                is_active=True
            )
            session.add(default_unit)
            created_count += 1
            logger.info(f"Created default org unit for owner {owner.id}")
        
        await session.commit()
        logger.info(f"Created {created_count} default org units")
        
        return created_count


if __name__ == "__main__":
    result = asyncio.run(create_default_org_units())
    print(f"Created {result} default org units")
```

### 3.6. Назначение payment_system_id для существующих договоров

**Файл:** `scripts/assign_default_payment_systems.py`

```python
"""
Скрипт для назначения системы оплаты "simple_hourly" всем существующим договорам.
"""
import asyncio
from sqlalchemy import select, update
from core.database.session import get_async_session
from domain.entities.contract import Contract
from domain.entities.payment_system import PaymentSystem
from core.logging.logger import logger


async def assign_default_payment_systems():
    """Назначить систему оплаты по умолчанию всем договорам."""
    async with get_async_session() as session:
        # Получить ID системы "simple_hourly"
        result = await session.execute(
            select(PaymentSystem).where(PaymentSystem.code == "simple_hourly")
        )
        simple_hourly = result.scalar_one_or_none()
        
        if not simple_hourly:
            logger.error("Payment system 'simple_hourly' not found!")
            return 0
        
        # Обновить все договоры без payment_system_id
        stmt = (
            update(Contract)
            .where(Contract.payment_system_id.is_(None))
            .values(payment_system_id=simple_hourly.id)
        )
        result = await session.execute(stmt)
        await session.commit()
        
        updated_count = result.rowcount
        logger.info(f"Assigned simple_hourly to {updated_count} contracts")
        
        return updated_count


if __name__ == "__main__":
    result = asyncio.run(assign_default_payment_systems())
    print(f"Updated {result} contracts")
```

---

## 4. Rollback план

### 4.1. Последовательность отката

**В обратном порядке применения:**

1. Откат `assign_default_payment_systems.py` - установить `payment_system_id = NULL`
2. Откат `create_default_org_units.py` - удалить созданные org_structure_units
3. Откат миграции `update_shift_tasks_structure` - вернуть старый формат shift_tasks
4. Откат миграции `add_object_payment_fields` - удалить новые поля из objects
5. Откат миграции `add_contract_payment_fields` - удалить новые поля из contracts
6. Откат миграции `convert_contract_hourly_rate` - вернуть Integer (рубли → копейки)

### 4.2. Команды отката

```bash
# Откат миграций (в обратном порядке)
alembic downgrade -1  # Откатить последнюю миграцию
alembic downgrade -1  # Откатить еще одну
# ... и так далее

# Полный откат до определенной версии
alembic downgrade <revision_before_changes>
```

### 4.3. Скрипты отката данных

**Файл:** `scripts/rollback_payment_systems.py`

```python
"""Откат данных: удалить созданные org_units и очистить payment_system_id."""
import asyncio
from sqlalchemy import update, delete
from core.database.session import get_async_session
from domain.entities.contract import Contract
from domain.entities.object import Object
from domain.entities.org_structure import OrgStructureUnit
from core.logging.logger import logger


async def rollback_payment_data():
    """Откатить данные о системах оплаты."""
    async with get_async_session() as session:
        # Очистить payment_system_id в contracts
        await session.execute(
            update(Contract).values(payment_system_id=None, payment_schedule_id=None)
        )
        logger.info("Cleared payment fields in contracts")
        
        # Очистить payment fields в objects
        await session.execute(
            update(Object).values(
                payment_system_id=None, 
                payment_schedule_id=None,
                org_unit_id=None
            )
        )
        logger.info("Cleared payment fields in objects")
        
        # Удалить созданные org_units (только с именем "Основное подразделение")
        result = await session.execute(
            delete(OrgStructureUnit).where(
                OrgStructureUnit.name == "Основное подразделение"
            )
        )
        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} default org units")
        
        await session.commit()
        
        return deleted_count


if __name__ == "__main__":
    result = asyncio.run(rollback_payment_data())
    print(f"Rollback completed. Deleted {result} org units")
```

---

## 5. Проверочные запросы

### 5.1. Проверка преобразования hourly_rate

```sql
-- До миграции
SELECT id, hourly_rate, 'kopecks' as unit FROM contracts WHERE hourly_rate IS NOT NULL LIMIT 5;

-- После миграции
SELECT id, hourly_rate, 'rubles' as unit FROM contracts WHERE hourly_rate IS NOT NULL LIMIT 5;

-- Проверка корректности преобразования (должны быть в 100 раз меньше)
```

### 5.2. Проверка новых полей

```sql
-- Проверить, что новые поля созданы
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'contracts' 
  AND column_name IN ('use_contract_rate', 'payment_system_id', 'payment_schedule_id');

SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'objects' 
  AND column_name IN ('payment_system_id', 'payment_schedule_id', 'org_unit_id');
```

### 5.3. Проверка индексов

```sql
-- Проверить созданные индексы
SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename IN ('contracts', 'objects')
  AND indexname LIKE '%payment%';
```

### 5.4. Проверка shift_tasks

```sql
-- Проверить структуру shift_tasks (должен быть объект с полями task, is_mandatory, deduction_amount)
SELECT 
    id,
    name,
    shift_tasks
FROM objects
WHERE shift_tasks IS NOT NULL
LIMIT 3;

-- Проверить, что старый формат преобразован
SELECT COUNT(*) 
FROM objects 
WHERE shift_tasks IS NOT NULL 
  AND jsonb_typeof(shift_tasks) = 'array'
  AND (
      SELECT COUNT(*) 
      FROM jsonb_array_elements(shift_tasks) AS elem
      WHERE NOT (elem ? 'task' AND elem ? 'is_mandatory')
  ) > 0;
-- Должно быть 0
```

---

## 6. Итоговая статистика изменений

### 6.1. Contracts

- **Изменено типов:** 1 (hourly_rate)
- **Добавлено полей:** 3 (use_contract_rate, payment_system_id, payment_schedule_id)
- **Добавлено индексов:** 3
- **Добавлено FK:** 2
- **Обновлено JSON полей:** 1 (manager_permissions)

### 6.2. Objects

- **Добавлено полей:** 3 (payment_system_id, payment_schedule_id, org_unit_id)
- **Обновлено JSONB полей:** 1 (shift_tasks)
- **Добавлено индексов:** 3
- **Добавлено FK:** 3

### 6.3. Миграции

- **Alembic миграций:** 4
- **Python скриптов миграции данных:** 2
- **Rollback скриптов:** 1

### 6.4. Затронутые записи (оценка)

- **Contracts:** ~100-500 записей (зависит от БД)
- **Objects:** ~50-200 записей
- **Время выполнения миграций:** ~5-10 минут

---

**Следующая задача:** 0.4. Анализ front-end (страницы для изменения)

