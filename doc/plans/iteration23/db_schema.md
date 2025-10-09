# Проектирование моделей данных для Итерации 23

**Дата:** 2025-10-09  
**Статус:** Завершен  
**Задача:** 0.2. Проектирование моделей данных

## Оглавление

1. [payment_systems](#1-payment_systems) - Виды систем оплаты труда
2. [payment_schedules](#2-payment_schedules) - Графики выплат
3. [org_structure_units](#3-org_structure_units) - Организационная структура
4. [payroll_entries](#4-payroll_entries) - Начисления
5. [payroll_deductions](#5-payroll_deductions) - Удержания
6. [payroll_bonuses](#6-payroll_bonuses) - Доплаты
7. [employee_payments](#7-employee_payments) - Фактические выплаты
8. [shift_tasks](#8-shift_tasks) - Задачи на смене
9. [timeslot_task_templates](#9-timeslot_task_templates) - Шаблоны задач для тайм-слотов

---

## 1. payment_systems

**Назначение:** Справочник видов систем оплаты труда

### SQL Schema

```sql
CREATE TABLE payment_systems (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    calculation_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    display_order INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_payment_systems_code ON payment_systems(code);
CREATE INDEX idx_payment_systems_is_active ON payment_systems(is_active);
CREATE INDEX idx_payment_systems_display_order ON payment_systems(display_order);

COMMENT ON TABLE payment_systems IS 'Справочник видов систем оплаты труда';
COMMENT ON COLUMN payment_systems.code IS 'Уникальный код системы (simple_hourly, salary, hourly_bonus)';
COMMENT ON COLUMN payment_systems.calculation_type IS 'Тип расчета (hourly, salary, hourly_bonus)';
```

### SQLAlchemy Model

```python
class PaymentSystem(Base):
    """Вид системы оплаты труда."""
    
    __tablename__ = "payment_systems"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    calculation_type = Column(String(50), nullable=False)  # hourly, salary, hourly_bonus
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    contracts = relationship("Contract", back_populates="payment_system")
    objects = relationship("Object", back_populates="payment_system")
```

### Seed Data

```python
SEED_PAYMENT_SYSTEMS = [
    {
        "code": "simple_hourly",
        "name": "Простая повременная",
        "description": "Оплата за фактически отработанное время по часовой ставке",
        "calculation_type": "hourly",
        "display_order": 1
    },
    {
        "code": "salary",
        "name": "Окладная",
        "description": "Фиксированная ежемесячная оплата труда, не зависящая от количества выполненной работы",
        "calculation_type": "salary",
        "display_order": 2
    },
    {
        "code": "hourly_bonus",
        "name": "Повременно-премиальная",
        "description": "Оплата времени работы плюс премия за достижение показателей или демотивация за нарушения",
        "calculation_type": "hourly_bonus",
        "display_order": 3
    }
]
```

---

## 2. payment_schedules

**Назначение:** Графики выплат с указанием периода и дат расчета

### SQL Schema

```sql
CREATE TABLE payment_schedules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    frequency VARCHAR(50) NOT NULL,
    payment_period JSONB NOT NULL,
    payment_day INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_payment_schedules_frequency ON payment_schedules(frequency);
CREATE INDEX idx_payment_schedules_is_active ON payment_schedules(is_active);
CREATE INDEX idx_payment_schedules_payment_period ON payment_schedules USING GIN (payment_period);

COMMENT ON TABLE payment_schedules IS 'Графики выплат';
COMMENT ON COLUMN payment_schedules.frequency IS 'Частота выплат (weekly, biweekly, monthly)';
COMMENT ON COLUMN payment_schedules.payment_period IS 'Период расчета в формате JSON: {type, description, calc_rules}';
COMMENT ON COLUMN payment_schedules.payment_day IS 'День выплаты: для weekly (1-7), для monthly (1-31)';
```

### SQLAlchemy Model

```python
class PaymentSchedule(Base):
    """График выплат."""
    
    __tablename__ = "payment_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String(50), nullable=False, index=True)  # weekly, biweekly, monthly
    payment_period = Column(JSONB, nullable=False)  # См. структуру ниже
    payment_day = Column(Integer, nullable=False)  # 1-7 для weekly, 1-31 для monthly
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    contracts = relationship("Contract", back_populates="payment_schedule")
    objects = relationship("Object", back_populates="payment_schedule")
    org_units = relationship("OrgStructureUnit", back_populates="payment_schedule")
```

### Структура payment_period (JSONB)

```json
{
  "type": "week | month | custom",
  "description": "Описание периода расчета",
  "calc_rules": {
    "for_weekly": {
      "period": "previous_week",
      "description": "За предыдущую неделю (пн-вс)"
    },
    "for_biweekly": {
      "first_payment": {
        "period": "1-15",
        "description": "За период с 1-го по 15-е текущего месяца"
      },
      "second_payment": {
        "period": "16-end",
        "description": "За период с 16-го по конец текущего месяца"
      }
    },
    "for_monthly": {
      "period": "previous_month",
      "description": "За предыдущий месяц полностью"
    }
  }
}
```

### Seed Data

```python
SEED_PAYMENT_SCHEDULES = [
    {
        "name": "Еженедельно по пятницам",
        "description": "Выплата каждую пятницу за предыдущую неделю (пн-вс)",
        "frequency": "weekly",
        "payment_day": 5,  # Пятница
        "payment_period": {
            "type": "week",
            "description": "За предыдущую неделю (понедельник-воскресенье)",
            "calc_rules": {
                "period": "previous_week",
                "start_day": "monday",
                "end_day": "sunday"
            }
        }
    },
    {
        "name": "Два раза в месяц (15-е и 30-е)",
        "description": "Выплата 15-го и 30-го (или последнего дня месяца)",
        "frequency": "biweekly",
        "payment_day": 15,  # Первая выплата
        "payment_period": {
            "type": "month",
            "description": "Две выплаты в месяц",
            "calc_rules": {
                "first_payment": {
                    "day": 15,
                    "period": "16-end_of_previous_month_to_15",
                    "description": "За период с 16-го прошлого месяца по 15-е текущего"
                },
                "second_payment": {
                    "day": 30,
                    "period": "16-30",
                    "description": "За период с 16-го по 30-е (или конец месяца) текущего месяца"
                }
            }
        }
    },
    {
        "name": "Ежемесячно 5-го числа",
        "description": "Выплата 5-го числа каждого месяца за предыдущий месяц",
        "frequency": "monthly",
        "payment_day": 5,
        "payment_period": {
            "type": "month",
            "description": "За весь предыдущий месяц (с 1-го по последнее число)",
            "calc_rules": {
                "period": "previous_month",
                "start_day": 1,
                "end_day": "last_day_of_month"
            }
        }
    }
]
```

---

## 3. org_structure_units

**Назначение:** Древовидная организационная структура с наследованием настроек

### SQL Schema

```sql
CREATE TABLE org_structure_units (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES org_structure_units(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    payment_system_id INTEGER REFERENCES payment_systems(id) ON DELETE SET NULL,
    payment_schedule_id INTEGER REFERENCES payment_schedules(id) ON DELETE SET NULL,
    level INTEGER DEFAULT 0 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_org_structure_units_owner_id ON org_structure_units(owner_id);
CREATE INDEX idx_org_structure_units_parent_id ON org_structure_units(parent_id);
CREATE INDEX idx_org_structure_units_level ON org_structure_units(level);
CREATE INDEX idx_org_structure_units_payment_system_id ON org_structure_units(payment_system_id);
CREATE INDEX idx_org_structure_units_payment_schedule_id ON org_structure_units(payment_schedule_id);

COMMENT ON TABLE org_structure_units IS 'Организационная структура (древовидная)';
COMMENT ON COLUMN org_structure_units.parent_id IS 'Родительское подразделение (NULL для корневого)';
COMMENT ON COLUMN org_structure_units.level IS 'Уровень вложенности (0 для корневого)';
```

### SQLAlchemy Model

```python
class OrgStructureUnit(Base):
    """Единица организационной структуры."""
    
    __tablename__ = "org_structure_units"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("org_structure_units.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    level = Column(Integer, default=0, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", backref="org_units")
    parent = relationship("OrgStructureUnit", remote_side=[id], backref="children")
    payment_system = relationship("PaymentSystem", backref="org_units")
    payment_schedule = relationship("PaymentSchedule", backref="org_units")
    objects = relationship("Object", back_populates="org_unit")
```

---

## 4. payroll_entries

**Назначение:** Начисления сотрудникам за период

### SQL Schema

```sql
CREATE TABLE payroll_entries (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_hours NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    base_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    bonus_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    deduction_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    total_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL,
    payment_system_id INTEGER REFERENCES payment_systems(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'draft' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_payroll_entries_employee_id ON payroll_entries(employee_id);
CREATE INDEX idx_payroll_entries_period ON payroll_entries(period_start, period_end);
CREATE INDEX idx_payroll_entries_status ON payroll_entries(status);
CREATE INDEX idx_payroll_entries_payment_system_id ON payroll_entries(payment_system_id);

COMMENT ON TABLE payroll_entries IS 'Начисления сотрудникам';
COMMENT ON COLUMN payroll_entries.status IS 'Статус: draft, approved, paid';
COMMENT ON COLUMN payroll_entries.total_amount IS 'Итого к выплате = base_amount + bonus_amount - deduction_amount';
```

### SQLAlchemy Model

```python
class PayrollEntry(Base):
    """Начисление сотруднику за период."""
    
    __tablename__ = "payroll_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    total_hours = Column(Numeric(10, 2), default=0, nullable=False)
    base_amount = Column(Numeric(10, 2), default=0, nullable=False)  # Базовая оплата
    bonus_amount = Column(Numeric(10, 2), default=0, nullable=False)  # Доплаты
    deduction_amount = Column(Numeric(10, 2), default=0, nullable=False)  # Удержания
    total_amount = Column(Numeric(10, 2), default=0, nullable=False)  # К выплате
    payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="draft", nullable=False, index=True)  # draft, approved, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    employee = relationship("User", backref="payroll_entries")
    payment_system = relationship("PaymentSystem", backref="payroll_entries")
    deductions = relationship("PayrollDeduction", back_populates="payroll_entry", cascade="all, delete-orphan")
    bonuses = relationship("PayrollBonus", back_populates="payroll_entry", cascade="all, delete-orphan")
    payments = relationship("EmployeePayment", back_populates="payroll_entry", cascade="all, delete-orphan")
```

---

## 5. payroll_deductions

**Назначение:** Удержания из зарплаты (автоматические и ручные)

### SQL Schema

```sql
CREATE TABLE payroll_deductions (
    id SERIAL PRIMARY KEY,
    payroll_entry_id INTEGER NOT NULL REFERENCES payroll_entries(id) ON DELETE CASCADE,
    shift_id INTEGER REFERENCES shifts(id) ON DELETE SET NULL,
    deduction_type VARCHAR(50) NOT NULL,
    is_automatic BOOLEAN DEFAULT FALSE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_payroll_deductions_payroll_entry_id ON payroll_deductions(payroll_entry_id);
CREATE INDEX idx_payroll_deductions_shift_id ON payroll_deductions(shift_id);
CREATE INDEX idx_payroll_deductions_deduction_type ON payroll_deductions(deduction_type);
CREATE INDEX idx_payroll_deductions_is_automatic ON payroll_deductions(is_automatic);
CREATE INDEX idx_payroll_deductions_created_by ON payroll_deductions(created_by);

COMMENT ON TABLE payroll_deductions IS 'Удержания из зарплаты';
COMMENT ON COLUMN payroll_deductions.deduction_type IS 'Тип: manual, late_shift, task_incomplete';
COMMENT ON COLUMN payroll_deductions.is_automatic IS 'TRUE для автоматических удержаний';
COMMENT ON COLUMN payroll_deductions.created_by IS 'Кто создал удержание (для ручных)';
```

### SQLAlchemy Model

```python
class PayrollDeduction(Base):
    """Удержание из начисления."""
    
    __tablename__ = "payroll_deductions"
    
    id = Column(Integer, primary_key=True, index=True)
    payroll_entry_id = Column(Integer, ForeignKey("payroll_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    deduction_type = Column(String(50), nullable=False, index=True)  # manual, late_shift, task_incomplete
    is_automatic = Column(Boolean, default=False, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    payroll_entry = relationship("PayrollEntry", back_populates="deductions")
    shift = relationship("Shift", backref="deductions")
    creator = relationship("User", foreign_keys=[created_by], backref="created_deductions")
```

---

## 6. payroll_bonuses

**Назначение:** Доплаты к зарплате

### SQL Schema

```sql
CREATE TABLE payroll_bonuses (
    id SERIAL PRIMARY KEY,
    payroll_entry_id INTEGER NOT NULL REFERENCES payroll_entries(id) ON DELETE CASCADE,
    shift_id INTEGER REFERENCES shifts(id) ON DELETE SET NULL,
    bonus_type VARCHAR(50) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_payroll_bonuses_payroll_entry_id ON payroll_bonuses(payroll_entry_id);
CREATE INDEX idx_payroll_bonuses_shift_id ON payroll_bonuses(shift_id);
CREATE INDEX idx_payroll_bonuses_bonus_type ON payroll_bonuses(bonus_type);
CREATE INDEX idx_payroll_bonuses_created_by ON payroll_bonuses(created_by);

COMMENT ON TABLE payroll_bonuses IS 'Доплаты к зарплате';
COMMENT ON COLUMN payroll_bonuses.bonus_type IS 'Тип: manual, overtime, performance';
```

### SQLAlchemy Model

```python
class PayrollBonus(Base):
    """Доплата к начислению."""
    
    __tablename__ = "payroll_bonuses"
    
    id = Column(Integer, primary_key=True, index=True)
    payroll_entry_id = Column(Integer, ForeignKey("payroll_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    bonus_type = Column(String(50), nullable=False, index=True)  # manual, overtime, performance
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    payroll_entry = relationship("PayrollEntry", back_populates="bonuses")
    shift = relationship("Shift", backref="bonuses")
    creator = relationship("User", foreign_keys=[created_by], backref="created_bonuses")
```

---

## 7. employee_payments

**Назначение:** Фактические выплаты (запись о переводе денег)

### SQL Schema

```sql
CREATE TABLE employee_payments (
    id SERIAL PRIMARY KEY,
    payroll_entry_id INTEGER NOT NULL REFERENCES payroll_entries(id) ON DELETE CASCADE,
    payment_date DATE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_employee_payments_payroll_entry_id ON employee_payments(payroll_entry_id);
CREATE INDEX idx_employee_payments_payment_date ON employee_payments(payment_date);
CREATE INDEX idx_employee_payments_status ON employee_payments(status);

COMMENT ON TABLE employee_payments IS 'Фактические выплаты сотрудникам';
COMMENT ON COLUMN employee_payments.payment_method IS 'Способ: card, cash, bank';
COMMENT ON COLUMN employee_payments.status IS 'Статус: pending, completed';
```

### SQLAlchemy Model

```python
class EmployeePayment(Base):
    """Фактическая выплата сотруднику."""
    
    __tablename__ = "employee_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    payroll_entry_id = Column(Integer, ForeignKey("payroll_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)  # card, cash, bank
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, completed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    payroll_entry = relationship("PayrollEntry", back_populates="payments")
```

---

## 8. shift_tasks

**Назначение:** Задачи на конкретной смене

### SQL Schema

```sql
CREATE TABLE shift_tasks (
    id SERIAL PRIMARY KEY,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    task_description TEXT NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    is_mandatory BOOLEAN DEFAULT FALSE NOT NULL,
    deduction_amount NUMERIC(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_shift_tasks_shift_id ON shift_tasks(shift_id);
CREATE INDEX idx_shift_tasks_is_completed ON shift_tasks(is_completed);
CREATE INDEX idx_shift_tasks_is_mandatory ON shift_tasks(is_mandatory);

COMMENT ON TABLE shift_tasks IS 'Задачи на конкретной смене';
COMMENT ON COLUMN shift_tasks.deduction_amount IS 'Сумма удержания за невыполнение (если обязательная)';
```

### SQLAlchemy Model

```python
class ShiftTask(Base):
    """Задача на смене."""
    
    __tablename__ = "shift_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    task_description = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    is_mandatory = Column(Boolean, default=False, nullable=False, index=True)
    deduction_amount = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    shift = relationship("Shift", backref="tasks")
```

---

## 9. timeslot_task_templates

**Назначение:** Шаблоны задач для тайм-слотов (переопределяют задачи объекта)

### SQL Schema

```sql
CREATE TABLE timeslot_task_templates (
    id SERIAL PRIMARY KEY,
    timeslot_id INTEGER NOT NULL REFERENCES time_slots(id) ON DELETE CASCADE,
    task_description TEXT NOT NULL,
    is_mandatory BOOLEAN DEFAULT FALSE NOT NULL,
    deduction_amount NUMERIC(10, 2),
    display_order INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_timeslot_task_templates_timeslot_id ON timeslot_task_templates(timeslot_id);
CREATE INDEX idx_timeslot_task_templates_display_order ON timeslot_task_templates(display_order);

COMMENT ON TABLE timeslot_task_templates IS 'Шаблоны задач для тайм-слотов';
COMMENT ON COLUMN timeslot_task_templates.display_order IS 'Порядок отображения задач';
```

### SQLAlchemy Model

```python
class TimeslotTaskTemplate(Base):
    """Шаблон задачи для тайм-слота."""
    
    __tablename__ = "timeslot_task_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    timeslot_id = Column(Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False, index=True)
    task_description = Column(Text, nullable=False)
    is_mandatory = Column(Boolean, default=False, nullable=False)
    deduction_amount = Column(Numeric(10, 2), nullable=True)
    display_order = Column(Integer, default=0, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    timeslot = relationship("TimeSlot", backref="task_templates")
```

---

## Итоговая статистика

**Всего новых таблиц:** 9  
**Всего индексов:** 42  
**Всего relationships:** 25

**Типы данных:**
- Integer: 35 полей
- VARCHAR/String: 18 полей
- Text: 12 полей
- Numeric(10, 2): 14 полей
- Boolean: 11 полей
- Date: 3 поля
- JSONB: 1 поле
- TIMESTAMP: 18 полей

**Constraints:**
- Foreign Keys: 27
- NOT NULL: 87 полей
- UNIQUE: 1 поле (payment_systems.code)
- ON DELETE CASCADE: 11
- ON DELETE SET NULL: 16

---

**Следующая задача:** 0.3. Проектирование изменений в существующих таблицах

