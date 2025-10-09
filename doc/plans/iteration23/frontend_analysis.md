# Анализ front-end для Итерации 23

**Дата:** 2025-10-09  
**Статус:** Завершен  
**Задача:** 0.4. Анализ front-end (страницы для изменения)

## Оглавление

1. [Страницы Владельца (Owner)](#1-страницы-владельца-owner)
2. [Страницы Управляющего (Manager)](#2-страницы-управляющего-manager)
3. [Страницы Сотрудника (Employee)](#3-страницы-сотрудника-employee)
4. [Новые страницы](#4-новые-страницы)
5. [Общие компоненты](#5-общие-компоненты)
6. [JavaScript компоненты](#6-javascript-компоненты)

---

## 1. Страницы Владельца (Owner)

### 1.1. Работа с договорами

#### 1.1.1. `/owner/employees/create` - Создание договора
**Файл:** `apps/web/templates/owner/employees/create.html`

**Текущее состояние:**
- Форма создания договора с полями: название, дата начала, дата окончания, почасовая ставка
- Выбор объектов для доступа
- Чекбокс "Назначить управляющим"

**Требуемые изменения:**
1. **Добавить чекбокс "Использовать ставку из договора"**
   - ID: `use_contract_rate`
   - Label: "Использовать ставку из договора (приоритет над объектом/тайм-слотом)"
   - Tooltip: "Если включено, при открытии смены будет использоваться ставка из этого договора, а не из объекта или тайм-слота"
   - При включении: поле "Почасовая ставка" становится обязательным (добавить `required`)

2. **Добавить dropdown "Система оплаты труда"**
   - ID: `payment_system_id`
   - Label: "Система оплаты труда"
   - Опции: из API `/api/payment-systems/active`
   - По умолчанию: "Простая повременная"
   - С tooltip для каждой опции с описанием системы

3. **Добавить dropdown "График выплат"**
   - ID: `payment_schedule_id`
   - Label: "График выплат"
   - Опции: из API `/api/payment-schedules/active`
   - Nullable (можно не выбирать)
   - С описанием периода расчета

4. **Обновить секцию "Права управляющего"** (видна только если `is_manager=true`)
   - Добавить чекбокс "Может управлять начислениями и выплатами"
   - ID: `can_manage_payroll`
   - Label: "Может управлять начислениями и выплатами (добавлять удержания/доплаты, одобрять начисления)"

**Пример HTML:**
```html
<div class="form-group">
    <label for="use_contract_rate">
        <input type="checkbox" id="use_contract_rate" name="use_contract_rate">
        Использовать ставку из договора
        <i class="fas fa-info-circle" data-toggle="tooltip" 
           title="Приоритет над ставками объекта и тайм-слота"></i>
    </label>
</div>

<div class="form-group">
    <label for="payment_system_id">Система оплаты труда</label>
    <select class="form-control" id="payment_system_id" name="payment_system_id">
        <option value="">-- Выберите систему --</option>
        <!-- Заполняется из API -->
    </select>
</div>

<div class="form-group">
    <label for="payment_schedule_id">График выплат (необязательно)</label>
    <select class="form-control" id="payment_schedule_id" name="payment_schedule_id">
        <option value="">-- Не указан --</option>
        <!-- Заполняется из API -->
    </select>
</div>
```

---

#### 1.1.2. `/owner/employees/edit_contract/{id}` - Редактирование договора
**Файл:** `apps/web/templates/owner/employees/edit_contract.html`

**Требуемые изменения:**
- Аналогичные изменениям в форме создания
- Предзаполнение значений из БД
- Возможность изменить все новые поля

---

#### 1.1.3. `/owner/employees/{id}` - Детализация сотрудника
**Файл:** `apps/web/templates/owner/employees/detail.html`

**Требуемые изменения:**
1. **В секции "Активные договоры"** добавить отображение:
   - Флаг "Использует ставку договора" (badge)
   - Система оплаты труда
   - График выплат
   - Для управляющих: флаг "Может управлять начислениями"

**Пример HTML:**
```html
<div class="contract-info">
    {% if contract.use_contract_rate %}
        <span class="badge badge-info">
            <i class="fas fa-star"></i> Использует ставку договора
        </span>
    {% endif %}
    
    <div class="info-row">
        <span class="label">Система оплаты:</span>
        <span class="value">{{ contract.payment_system.name }}</span>
    </div>
    
    {% if contract.payment_schedule %}
    <div class="info-row">
        <span class="label">График выплат:</span>
        <span class="value">{{ contract.payment_schedule.name }}</span>
    </div>
    {% endif %}
</div>
```

---

### 1.2. Работа с объектами

#### 1.2.1. `/owner/objects/create` - Создание объекта
**Файл:** `apps/web/templates/owner/objects/create.html`

**Требуемые изменения:**
1. **Добавить dropdown "Подразделение"**
   - ID: `org_unit_id`
   - Label: "Подразделение организационной структуры"
   - Опции: древовидная структура подразделений владельца
   - По умолчанию: "Основное подразделение"
   - С отображением унаследованных настроек

2. **Добавить dropdown "Система оплаты труда"**
   - ID: `payment_system_id`
   - Label: "Система оплаты труда"
   - Nullable (наследуется от подразделения)
   - Текст: "Если не указано, наследуется от подразделения: [название]"

3. **Добавить dropdown "График выплат"**
   - ID: `payment_schedule_id`
   - Label: "График выплат"
   - Nullable (наследуется от подразделения)

4. **Обновить секцию "Задачи на смене"**
   - Текущее состояние: JSONB поле `shift_tasks` как textarea
   - Новое состояние: Динамический список задач
   - Каждая задача:
     - Текст задачи (input text)
     - Чекбокс "Обязательная"
     - Поле "Сумма удержания за невыполнение" (number, рубли)
   - Кнопки: "Добавить задачу", "Удалить"

**Пример HTML:**
```html
<div class="form-group">
    <label for="org_unit_id">Подразделение</label>
    <select class="form-control" id="org_unit_id" name="org_unit_id" required>
        <!-- Заполняется из API, древовидная структура -->
    </select>
    <small class="form-text text-muted">
        Унаследованные настройки: Система оплаты - <span id="inherited_payment_system">...</span>
    </small>
</div>

<div class="form-group">
    <label>Задачи на смене по умолчанию</label>
    <div id="shift-tasks-container">
        <!-- Динамически добавляемые задачи -->
    </div>
    <button type="button" class="btn btn-sm btn-secondary" onclick="addShiftTask()">
        <i class="fas fa-plus"></i> Добавить задачу
    </button>
</div>

<!-- Шаблон задачи -->
<template id="shift-task-template">
    <div class="shift-task-item border p-3 mb-2">
        <div class="row">
            <div class="col-md-6">
                <input type="text" class="form-control" name="task_description[]" placeholder="Описание задачи" required>
            </div>
            <div class="col-md-2">
                <label>
                    <input type="checkbox" name="task_is_mandatory[]" value="1">
                    Обязательная
                </label>
            </div>
            <div class="col-md-3">
                <input type="number" class="form-control" name="task_deduction[]" placeholder="Удержание (₽)" min="0" step="10">
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-sm btn-danger" onclick="removeShiftTask(this)">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    </div>
</template>
```

---

#### 1.2.2. `/owner/objects/edit/{id}` - Редактирование объекта
**Файл:** `apps/web/templates/owner/objects/edit.html`

**Требуемые изменения:**
- Аналогичные изменениям в форме создания
- Предзаполнение задач из БД
- Возможность редактировать, добавлять, удалять задачи

---

#### 1.2.3. `/owner/objects/{id}` - Детализация объекта
**Файл:** `apps/web/templates/owner/objects/detail.html`

**Требуемые изменения:**
1. **Добавить секцию "Настройки оплаты"**
   - Подразделение
   - Система оплаты (с указанием источника: собственная/унаследованная)
   - График выплат (с указанием источника)

2. **Обновить секцию "Задачи на смене"**
   - Отображать задачи в виде таблицы
   - Колонки: Задача, Обязательная, Удержание
   - Значки для обязательных задач

**Пример HTML:**
```html
<div class="card">
    <div class="card-header">Настройки оплаты</div>
    <div class="card-body">
        <div class="info-row">
            <span class="label">Подразделение:</span>
            <span class="value">{{ object.org_unit.name }}</span>
        </div>
        <div class="info-row">
            <span class="label">Система оплаты:</span>
            <span class="value">
                {{ object.payment_system.name if object.payment_system else object.org_unit.payment_system.name }}
                {% if not object.payment_system %}
                    <span class="badge badge-secondary">Унаследовано</span>
                {% endif %}
            </span>
        </div>
    </div>
</div>

<div class="card mt-3">
    <div class="card-header">Задачи на смене (по умолчанию)</div>
    <div class="card-body">
        <table class="table">
            <thead>
                <tr>
                    <th>Задача</th>
                    <th>Обязательная</th>
                    <th>Удержание</th>
                </tr>
            </thead>
            <tbody>
                {% for task in object.shift_tasks_parsed %}
                <tr>
                    <td>
                        {% if task.is_mandatory %}
                            <i class="fas fa-exclamation-circle text-danger"></i>
                        {% endif %}
                        {{ task.task }}
                    </td>
                    <td>
                        {% if task.is_mandatory %}
                            <span class="badge badge-warning">Да</span>
                        {% else %}
                            <span class="badge badge-secondary">Нет</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if task.deduction_amount %}
                            {{ task.deduction_amount }}₽
                        {% else %}
                            -
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
```

---

### 1.3. Работа с тайм-слотами

#### 1.3.1. `/owner/timeslots/edit/{id}` - Редактирование тайм-слота
**Файл:** `apps/web/templates/owner/timeslots/edit.html`

**Требуемые изменения:**
1. **Добавить секцию "Задачи для этого тайм-слота"**
   - Аналогично задачам объекта
   - Чекбокс "Использовать задачи объекта по умолчанию"
   - При снятии чекбокса - показать форму для добавления задач
   - Можно переопределить задачи объекта

**Пример HTML:**
```html
<div class="form-group">
    <label>
        <input type="checkbox" id="use_object_tasks" name="use_object_tasks" checked>
        Использовать задачи объекта по умолчанию
    </label>
</div>

<div id="custom-tasks-section" style="display: none;">
    <label>Задачи для этого тайм-слота</label>
    <div id="timeslot-tasks-container">
        <!-- Аналогично shift-tasks-container -->
    </div>
    <button type="button" class="btn btn-sm btn-secondary" onclick="addTimeslotTask()">
        <i class="fas fa-plus"></i> Добавить задачу
    </button>
</div>

<script>
document.getElementById('use_object_tasks').addEventListener('change', function() {
    document.getElementById('custom-tasks-section').style.display = 
        this.checked ? 'none' : 'block';
});
</script>
```

---

## 2. Страницы Управляющего (Manager)

### 2.1. Работа с договорами

#### 2.1.1. `/manager/employees/add` - Создание договора
**Файл:** `apps/web/templates/manager/employees/add.html`

**Требуемые изменения:**
- Аналогичные изменениям в `/owner/employees/create`
- Дополнительно: чекбокс "Может управлять начислениями" (если сам управляющий имеет право `can_manage_payroll`)
- Ограничение: не может назначать других управляющими (если нет права `can_manage_managers`)

---

#### 2.1.2. `/manager/employees/edit/{id}` - Редактирование сотрудника
**Файл:** `apps/web/templates/manager/employees/edit.html`

**Требуемые изменения:**
- Аналогичные изменениям в редактировании договора владельца
- С учетом прав доступа управляющего

---

### 2.2. Работа с объектами

#### 2.2.1. `/manager/objects/edit/{id}` - Редактирование объекта
**Файл:** `apps/web/templates/manager/objects/edit.html`

**Требуемые изменения:**
- Аналогичные изменениям владельца
- Только для объектов, к которым есть доступ
- Без выбора подразделения (read-only, если указано)

---

### 2.3. Работа с тайм-слотами

#### 2.3.1. `/manager/timeslots/edit/{id}` - Редактирование тайм-слота
**Файл:** `apps/web/templates/manager/timeslots/edit.html`

**Требуемые изменения:**
- Аналогичные изменениям владельца
- Секция задач для тайм-слота

---

## 3. Страницы Сотрудника (Employee)

### 3.1. Просмотр информации о договоре

#### 3.1.1. `/employee/profile` или `/employee/contract` - Профиль/Договор
**Файл:** `apps/web/templates/employee/*` (предположительно)

**Требуемые изменения:**
1. **Добавить отображение:**
   - Система оплаты труда (название и описание)
   - График выплат (частота и даты)
   - Ставка (если указана в договоре)

**Пример HTML:**
```html
<div class="card">
    <div class="card-header">Мой договор</div>
    <div class="card-body">
        <div class="info-row">
            <span class="label">Система оплаты:</span>
            <span class="value">{{ contract.payment_system.name }}</span>
            <small class="text-muted">{{ contract.payment_system.description }}</small>
        </div>
        
        {% if contract.payment_schedule %}
        <div class="info-row">
            <span class="label">График выплат:</span>
            <span class="value">{{ contract.payment_schedule.name }}</span>
            <small class="text-muted">{{ contract.payment_schedule.description }}</small>
        </div>
        {% endif %}
        
        {% if contract.hourly_rate and contract.use_contract_rate %}
        <div class="info-row">
            <span class="label">Почасовая ставка:</span>
            <span class="value">{{ contract.hourly_rate }}₽/час</span>
            <span class="badge badge-primary">Приоритетная</span>
        </div>
        {% endif %}
    </div>
</div>
```

---

## 4. Новые страницы

### 4.1. Справочник систем оплаты труда (Owner)

**URL:** `/owner/payment-systems`  
**Файл:** `apps/web/templates/owner/payment_systems/list.html` (СОЗДАТЬ)

**Содержание:**
- Таблица систем оплаты
- Колонки: Название, Описание, Тип расчета, Активна
- Только просмотр (на данном этапе, редактирование - для суперадмина)

---

### 4.2. Управление начислениями (Owner)

**URL:** `/owner/payroll`  
**Файл:** `apps/web/templates/owner/payroll/list.html` (СОЗДАТЬ)

**Содержание:**
- Список сотрудников с начислениями
- Фильтры: период, статус (draft/approved/paid), объект
- Колонки: Сотрудник, Период, Часы, Начислено, Удержано, К выплате, Статус
- Кнопка "Рассчитать начисления" → модальное окно с выбором сотрудника и периода
- Ссылка на детализацию

---

**URL:** `/owner/payroll/{entry_id}`  
**Файл:** `apps/web/templates/owner/payroll/detail.html` (СОЗДАТЬ)

**Содержание:**
- Информация о сотруднике и периоде
- Таблица смен за период
- Секция "Начисления": базовая оплата, доплаты
- Секция "Удержания": автоматические и ручные
- Итоговая сумма к выплате
- Кнопки:
  - "Добавить удержание" → модальное окно
  - "Добавить доплату" → модальное окно
  - "Одобрить" (draft → approved)
  - "Записать выплату" (approved → paid) → модальное окно с полями: дата, сумма, способ

---

### 4.3. Организационная структура (Owner)

**URL:** `/owner/org-structure`  
**Файл:** `apps/web/templates/owner/org_structure/index.html` (СОЗДАТЬ)

**Содержание:**
- Древовидное представление подразделений
- Для каждого узла: название, система оплаты, график выплат, кол-во объектов
- Значки наследования (цепочка)
- Кнопки: "Добавить подразделение", "Редактировать", "Удалить"
- Возможность перемещения (drag-and-drop или кнопки)

---

### 4.4. Управление начислениями (Manager)

**URL:** `/manager/payroll`  
**Файл:** `apps/web/templates/manager/payroll/list.html` (СОЗДАТЬ)

**Содержание:**
- Аналогично `/owner/payroll`
- Только сотрудники по доступным объектам
- Доступно только если `can_manage_payroll = true`

---

**URL:** `/manager/payroll/{entry_id}`  
**Файл:** `apps/web/templates/manager/payroll/detail.html` (СОЗДАТЬ)

**Содержание:**
- Аналогично `/owner/payroll/{entry_id}`
- Кнопка "Записать выплату" НЕ доступна (только владельцу)

---

### 4.5. История выплат (Employee)

**URL:** `/employee/payroll`  
**Файл:** `apps/web/templates/employee/payroll/index.html` (СОЗДАТЬ)

**Содержание:**
- Таблица выплат сотрудника
- Колонки: Период, Часы, Начислено, Удержано, Выплачено, Статус, Дата выплаты
- Ссылка на детализацию
- Секция "Предстоящие выплаты" (по графику)

---

## 5. Общие компоненты

### 5.1. Модальное окно добавления удержания

**Файл:** `apps/web/templates/shared/modals/add_deduction.html` (СОЗДАТЬ)

**Поля:**
- Сумма (number, required)
- Описание (textarea, required)
- Связь со сменой (select, nullable)

---

### 5.2. Модальное окно добавления доплаты

**Файл:** `apps/web/templates/shared/modals/add_bonus.html` (СОЗДАТЬ)

**Поля:**
- Сумма (number, required)
- Описание (textarea, required)
- Связь со сменой (select, nullable)

---

### 5.3. Модальное окно записи выплаты

**Файл:** `apps/web/templates/shared/modals/record_payment.html` (СОЗДАТЬ)

**Поля:**
- Дата выплаты (date, required, по умолчанию сегодня)
- Сумма (number, readonly, предзаполнено из начисления)
- Способ выплаты (select: карта, наличные, банк, required)
- Примечания (textarea, nullable)

---

## 6. JavaScript компоненты

### 6.1. Управление задачами на смене

**Файл:** `apps/web/static/js/shift_tasks_manager.js` (СОЗДАТЬ)

**Функции:**
- `addShiftTask()` - добавить задачу
- `removeShiftTask(element)` - удалить задачу
- `serializeShiftTasks()` - сериализовать задачи в JSON
- `loadShiftTasks(tasks)` - загрузить задачи из JSON

---

### 6.2. Выбор системы оплаты с tooltip

**Файл:** `apps/web/static/js/payment_system_selector.js` (СОЗДАТЬ)

**Функции:**
- `loadPaymentSystems(containerId)` - загрузить системы из API
- `showPaymentSystemInfo(systemId)` - показать детальную информацию в tooltip

---

### 6.3. Отображение унаследованных настроек

**Файл:** `apps/web/static/js/org_unit_inheritance.js` (СОЗДАТЬ)

**Функции:**
- `loadOrgUnitTree(ownerId)` - загрузить дерево подразделений
- `showInheritedSettings(unitId)` - показать унаследованные настройки
- `onOrgUnitChange(unitId)` - обработчик смены подразделения

---

## 7. Календарь с фильтром по подразделениям

### 7.1. Страницы календаря

#### 7.1.1. `/owner/calendar` - Календарь владельца
**Файл:** `apps/web/templates/owner/calendar.html` (существующий)

**Требуемые изменения:**
1. **Добавить фильтр по подразделениям** (слева от фильтра по объектам)
   - Dropdown "Подразделение"
   - ID: `org_unit_filter`
   - Опции: 
     - "Все подразделения" (по умолчанию)
     - Список подразделений владельца (древовидная структура с отступами)
   - При выборе подразделения: фильтруются объекты (показываются только объекты выбранного подразделения и дочерних подразделений)
   - Сохранение выбора в localStorage

2. **Обновить логику фильтра объектов**
   - Фильтр объектов зависит от выбранного подразделения
   - При смене подразделения: автоматически обновить список объектов в фильтре
   - Если выбраны объекты, которых нет в новом подразделении: очистить выбор

**Пример HTML:**
```html
<div class="calendar-filters d-flex align-items-center mb-3">
    <!-- Фильтр по подразделениям (НОВЫЙ) -->
    <div class="filter-group mr-3">
        <label for="org_unit_filter" class="mr-2">Подразделение:</label>
        <select class="form-control" id="org_unit_filter" style="min-width: 200px;">
            <option value="">Все подразделения</option>
            <option value="1">Основное подразделение</option>
            <option value="2">&nbsp;&nbsp;Филиал А</option>
            <option value="3">&nbsp;&nbsp;&nbsp;&nbsp;Отдел продаж</option>
            <option value="4">&nbsp;&nbsp;Филиал Б</option>
        </select>
    </div>
    
    <!-- Существующий фильтр по объектам -->
    <div class="filter-group mr-3">
        <label for="object_filter" class="mr-2">Объекты:</label>
        <select class="form-control" id="object_filter" multiple style="min-width: 250px;">
            <!-- Загружается из API, зависит от org_unit_filter -->
        </select>
    </div>
    
    <!-- Остальные фильтры... -->
</div>
```

**JavaScript обновления:**
```javascript
// В shared/services/calendar_filter_service.js или в шаблоне

// Загрузка подразделений
async function loadOrgUnits() {
    const response = await fetch('/api/org-units/tree');
    const units = await response.json();
    populateOrgUnitFilter(units);
}

// Обработчик смены подразделения
document.getElementById('org_unit_filter').addEventListener('change', function() {
    const orgUnitId = this.value;
    
    // Сохранить в localStorage
    localStorage.setItem('calendar_org_unit_filter', orgUnitId);
    
    // Обновить список объектов
    loadObjectsForOrgUnit(orgUnitId);
    
    // Перезагрузить календарь
    calendar.refetchEvents();
});

// Загрузка объектов для подразделения
async function loadObjectsForOrgUnit(orgUnitId) {
    const url = orgUnitId 
        ? `/api/objects?org_unit_id=${orgUnitId}&include_children=true`
        : '/api/objects';
    
    const response = await fetch(url);
    const objects = await response.json();
    
    populateObjectFilter(objects);
}

// Фильтрация событий календаря
function getCalendarEvents(fetchInfo, successCallback, failureCallback) {
    const orgUnitId = document.getElementById('org_unit_filter').value;
    const objectIds = Array.from(document.getElementById('object_filter').selectedOptions)
        .map(opt => opt.value);
    
    const params = new URLSearchParams({
        start: fetchInfo.startStr,
        end: fetchInfo.endStr,
        ...(orgUnitId && { org_unit_id: orgUnitId }),
        ...(objectIds.length && { object_ids: objectIds.join(',') })
    });
    
    fetch(`/api/calendar/events?${params}`)
        .then(response => response.json())
        .then(data => successCallback(data))
        .catch(error => failureCallback(error));
}
```

---

#### 7.1.2. `/manager/calendar` - Календарь управляющего
**Файл:** `apps/web/templates/manager/calendar.html` (существующий)

**Требуемые изменения:**
- Аналогичные изменениям владельца
- Ограничение: показывать только подразделения, в которых есть доступные объекты
- Фильтр объектов: только объекты, к которым есть доступ

---

### 7.2. API endpoints для фильтра

#### 7.2.1. GET `/api/org-units/tree` - Дерево подразделений
**Файл:** `apps/web/routes/shared/org_structure_api.py` (СОЗДАТЬ)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Основное подразделение",
    "level": 0,
    "parent_id": null,
    "object_count": 15,
    "children": [
      {
        "id": 2,
        "name": "Филиал А",
        "level": 1,
        "parent_id": 1,
        "object_count": 8,
        "children": [...]
      }
    ]
  }
]
```

---

#### 7.2.2. GET `/api/objects?org_unit_id={id}&include_children={bool}` - Объекты подразделения
**Файл:** `apps/web/routes/owner.py` или `apps/api/routers/objects.py` (обновить)

**Query params:**
- `org_unit_id` (int, optional) - ID подразделения
- `include_children` (bool, default=true) - Включать ли объекты дочерних подразделений

**Response:**
```json
[
  {
    "id": 1,
    "name": "Объект 1",
    "org_unit_id": 2,
    "org_unit_name": "Филиал А"
  }
]
```

---

### 7.3. CSS стили для фильтра

**Файл:** `apps/web/static/css/shared/calendar.css` (обновить)

```css
/* Фильтр подразделений */
.calendar-filters {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 20px;
}

.filter-group {
    display: flex;
    align-items: center;
}

.filter-group label {
    font-weight: 500;
    margin-bottom: 0;
    white-space: nowrap;
}

#org_unit_filter {
    min-width: 200px;
}

/* Древовидная структура в dropdown */
#org_unit_filter option[data-level="1"] {
    padding-left: 20px;
}

#org_unit_filter option[data-level="2"] {
    padding-left: 40px;
}

#org_unit_filter option[data-level="3"] {
    padding-left: 60px;
}

/* Индикатор количества объектов */
.org-unit-object-count {
    color: #6c757d;
    font-size: 0.9em;
}
```

---

### 7.4. Обновление shared calendar API

**Файл:** `routes/shared/calendar_api.py` (обновить)

**Добавить поддержку фильтрации по org_unit_id:**

```python
@router.get("/api/calendar/events")
async def get_calendar_events(
    start: str,
    end: str,
    org_unit_id: Optional[int] = None,
    object_ids: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Получить события календаря.
    
    Args:
        org_unit_id: Фильтр по подразделению (включая дочерние)
        object_ids: Фильтр по конкретным объектам
    """
    # Если указан org_unit_id, получить все объекты подразделения и дочерних
    if org_unit_id:
        objects = await get_objects_for_org_unit(
            org_unit_id, 
            include_children=True, 
            session=session
        )
        object_ids_list = [obj.id for obj in objects]
    elif object_ids:
        object_ids_list = [int(id) for id in object_ids.split(',')]
    else:
        # Все доступные объекты пользователя
        object_ids_list = await get_accessible_object_ids(current_user, session)
    
    # Загрузить события для объектов
    events = await calendar_service.get_events(
        start_date=start,
        end_date=end,
        object_ids=object_ids_list,
        session=session
    )
    
    return events
```

---

## 8. Итоговая статистика

### 8.1. Изменения в существующих страницах

**Owner:**
- Создание договора: +4 поля
- Редактирование договора: +4 поля
- Детализация сотрудника: +3 секции отображения
- Создание объекта: +3 поля + секция задач
- Редактирование объекта: +3 поля + секция задач
- Детализация объекта: +2 секции
- Редактирование тайм-слота: +1 секция

**Manager:**
- Создание договора: +4 поля
- Редактирование сотрудника: +4 поля
- Редактирование объекта: +2 поля + секция задач
- Редактирование тайм-слота: +1 секция

**Employee:**
- Профиль/Договор: +1 секция отображения

**Календарь:**
- Календарь владельца: +1 фильтр (подразделения)
- Календарь управляющего: +1 фильтр (подразделения)

**Всего страниц для изменения:** 15

### 8.2. Новые страницы

- Справочник систем оплаты: 1
- Управление начислениями (Owner): 2
- Организационная структура: 1
- Управление начислениями (Manager): 2
- История выплат (Employee): 1

**Всего новых страниц:** 7

### 8.3. Новые компоненты и API

- Модальные окна: 3
- JavaScript компоненты: 3
- HTML шаблоны задач: 2
- **API endpoints:** 2 (org-units/tree, objects с фильтром)
- **CSS обновления:** 1 (calendar.css)

**Всего новых компонентов:** 11

### 8.4. Оценка трудозатрат

- Изменение существующих страниц: ~3-4 дня
- **Календарь с фильтром подразделений:** ~1-2 дня
- Создание новых страниц: ~5-6 дней
- Создание компонентов и JS: ~2-3 дня
- **API endpoints для фильтра:** ~0.5-1 день
- Тестирование UI: ~2 дня

**Итого на front-end:** ~14-18 дней

---

**Следующая задача:** 0.5. Анализ middleware и сервисов

