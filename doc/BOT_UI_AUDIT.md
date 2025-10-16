# 🤖 Полный аудит UI бота StaffProBot

**Дата**: 2025-10-16  
**Версия**: Production на коммите c59bbf0 + dev с fixes  
**Статус**: В разработке

---

## 📋 Содержание

1. [Основные сценарии](#основные-сценарии)
2. [Детальный анализ каждого экрана](#детальный-анализ-каждого-экрана)
3. [Матрица проблем](#матрица-проблем)
4. [Техническое видение](#техническое-видение)
5. [План работ](#план-работ)

---

## Основные сценарии

### 🟢 Основной flow пользователя:

```
/start (Главное меню)
  ├─ 🔄 Открыть объект → Закрыть объект
  ├─ 🔄 Открыть смену → Закрыть смену
  ├─ 📅 Запланировать смену
  ├─ 📋 Мои планы
  ├─ 📊 Отчет
  ├─ 📝 Мои задачи
  ├─ 📈 Статус
  └─ 🆔 Мой Telegram ID
```

---

## Детальный анализ каждого экрана

### 1️⃣ Главное меню (`/start`)

**Файл**: `apps/bot/handlers_div/core_handlers.py`  
**Функция**: `start_command()`

#### UI элементы
- Приветственное сообщение с описанием функций
- 7 кнопок в 2x1 матрице
- HTML форматирование

#### Данные в БД
- Создание/обновление User в user_manager
- Логирование входа

#### Логика
```python
if not user_manager.is_user_registered(user.id):
    # Новый пользователь - регистрация
    user_manager.register_user(...)
else:
    # Существующий - обновляем активность
    user_manager.update_user_activity(...)
```

#### Состояние UserState
- Очищается: `user_state_manager.clear_state(user_id)`

#### ✅ Работает
- Регистрация новых пользователей
- Отображение кнопок меню

#### ❌ Не работает
- Нет проверки статуса пользователя (может быть заблокирован?)

#### 🟠 Потенциальные улучшения
- Добавить проверку `is_active` перед показом меню
- Добавить логирование действий пользователя

---

### 2️⃣ Открыть объект

**Файл**: `apps/bot/handlers_div/object_state_handlers.py`  
**Функция**: `_handle_open_object()`, `_handle_select_object_to_open()`

#### UI элементы
- Список объектов (inline кнопки)
- Запрос геолокации (KeyboardButton с `request_location=True`)

#### Данные в БД
- Opening объекта
- Сохранение координат

#### Логика
1. Получить список объектов пользователя
2. Показать кнопки с `callback_data="open_object:{object_id}"`
3. При выборе объекта → `_handle_select_object_to_open()`
4. Запросить геопозицию
5. Проверить расстояние до объекта
6. Если OK → создать Opening и вернуться в меню

#### Состояние UserState
```python
UserState(
    action=UserAction.OPEN_OBJECT,
    step=UserStep.LOCATION_REQUEST,
    selected_object_id=object_id
)
```

#### ✅ Работает
- Показывает список объектов
- Запрашивает геолокацию
- Проверяет расстояние

#### ❌ Не работает
- Нет кнопки для отправки геолокации (нужно отправить с помощью скрепки)
- Нет проверки "объект уже открыт?"

#### 🟠 Проблемы, найденные сегодня
- Нет геолокации-кнопки при открытии объекта (можно исправить добавлением ReplyKeyboardMarkup)

---

### 3️⃣ Открыть смену

**Файл**: `apps/bot/handlers_div/shift_handlers.py`  
**Функции**: `_handle_open_shift()`, `_handle_open_planned_shift()`, `_handle_select_object_to_open()`

#### UI элементы
- "Мои смены" (кнопка)
- Список запланированных смен (inline кнопки)
- Выбор объекта для спонтанной смены
- Запрос геолокации
- Список задач с кнопками "Выполнено"/"Мои задачи"

#### Данные в БД
- Shift с `status='active'`, `actual_start=NOW()`
- Сохранение координат

#### Логика (упрощённо)
1. Показать "Мои смены" → запланированные + спонтанная
2. Для запланированной: загрузить shift по time_slot_id
3. Для спонтанной: показать выбор объекта
4. Запросить геопозицию
5. Проверить расстояние
6. Загрузить все задачи (из time_slot + object)
7. Показать задачи в сообщении
8. Вернуться в меню

#### Загрузка задач - КРИТИЧНО
```python
# Запланированная смена
if shift.time_slot_id and shift.time_slot:
    # Загрузить из TimeslotTaskTemplate
    timeslot_tasks = _load_timeslot_tasks(session, shift.time_slot)
    
    # Загрузить из object
    object_tasks = shift.object.shift_tasks
    
    # Объединить
    if not shift.time_slot.ignore_object_tasks:
        all_tasks = timeslot_tasks + object_tasks
    else:
        all_tasks = timeslot_tasks
else:
    # Спонтанная смена - только задачи объекта
    all_tasks = shift.object.shift_tasks
```

#### Состояние UserState
```python
UserState(
    action=UserAction.OPEN_SHIFT,
    step=UserStep.LOCATION_REQUEST,
    selected_shift_id=shift_id,
    selected_object_id=object_id,
    shift_tasks=[...]  # ← ВАЖНО!
)
```

#### ✅ Работает
- Загружает запланированные смены
- Загружает задачи из тайм-слота и объекта
- Отображает задачи с иконками (⚠️ обязательная, 📸 фото)
- Проверяет расстояние

#### ❌ Не работает
- Нет кнопки для отправки геолокации (нужна ReplyKeyboardMarkup)
- После отправки геолокации → молчит, нужна кнопка главного меню

#### 🔴 CRITICAL (найдено сегодня)
- Нет унифицированной функции `_collect_shift_tasks()` - код дублируется в разных местах

---

### 4️⃣ Мои задачи

**Файл**: `apps/bot/handlers_div/shift_handlers.py`  
**Функции**: `_handle_my_tasks()`, `_handle_complete_my_task()`

#### UI элементы
- Inline кнопки для каждой задачи: "✅ Выполнить"
- Кнопки "📸 Отправить фото" (если требуется медиа)
- Кнопка "Вернуться" (если в меню задач)

#### Данные в БД
- UserState.completed_tasks - индексы выполненных
- UserState.task_media - данные о фото

#### Логика
1. Загрузить все задачи смены (как при открытии)
2. Показать список с кнопками выполнения
3. При клике - отметить как выполненную
4. Если требуется фото - запросить
5. Сохранить в UserState.task_media

#### Загрузка задач
```python
# Та же логика, что при открытии смены!
# ← ДУБЛИРОВАНИЕ КОДА!
```

#### Состояние UserState
```python
UserState(
    action=UserAction.COMPLETE_MY_TASKS,
    step=UserStep.TASK_COMPLETION,
    completed_tasks=[0, 2],  # индексы выполненных
    task_media={'0': {'media_url': 'file_123.jpg', ...}}
)
```

#### ✅ Работает
- Показывает все задачи (из тайм-слота и объекта)
- Позволяет отметить как выполненные
- Запрашивает фото если требуется

#### ❌ Не работает
- Код загрузки задач дублируется (не DRY)
- Нет кнопки "Закрыть смену" в меню задач

#### 🟠 Проблемы
- `completed_tasks` сохраняется в UserState (in-memory), при перезапуске бота теряется

---

### 5️⃣ Закрыть объект

**Файл**: `apps/bot/handlers_div/object_state_handlers.py`  
**Функции**: `_handle_close_object()`

#### UI элементы
- Запрос геолокации
- Кнопка "Продолжить закрытие" (если задачи)

#### Данные в БД
- Closing объекта
- Сохранение координат
- Должны ли сохраняться выполненные задачи?

#### Логика
1. Получить активный shift на этом объекте
2. **ПРОБЛЕМА**: Загружаются только задачи объекта, не из тайм-слота!
3. Запросить геопозицию
4. После геопозиции → close_object() в shift_service
5. Если был shift → закрыть его и перейти к закрытию смены

#### Загрузка задач - ОШИБКА!
```python
# В object_state_handlers.py НЕ используется _load_timeslot_tasks()!
# Показываются только object.shift_tasks

# Правильно должно быть:
# if shift.time_slot_id:
#     timeslot_tasks = _load_timeslot_tasks(...)
#     all_tasks = timeslot_tasks + object_tasks
```

#### Состояние UserState
```python
UserState(
    action=UserAction.CLOSE_OBJECT,
    step=UserStep.LOCATION_REQUEST,
    selected_object_id=object_id,
    shift_id=shift_id,
    # ❌ Здесь НЕ сохраняются completed_tasks от time_slot!
)
```

#### ✅ Работает
- Закрывает объект
- Запрашивает геолокацию

#### ❌ Не работает (CRITICAL)
- **Задачи из тайм-слота НЕ показываются**
- **completed_tasks теряются при обновлении UserState**
- Нет проверки "объект уже закрыт?"

#### 🔴 CRITICAL (найдено сегодня)
- Нет унифицированной загрузки задач
- Потеря информации о выполненных задачах тайм-слота

---

### 6️⃣ Закрыть смену

**Файл**: `apps/bot/handlers_div/shift_handlers.py`  
**Функции**: `_handle_close_shift()`, `_handle_close_shift_with_tasks()`

#### UI элементы
- Запрос геолокации
- Кнопка "Продолжить закрытие"

#### Данные в БД
- Сохранение `shift.notes` с `completed_tasks` и `task_media`
- Закрытие shift с `status='completed'`

#### Логика
1. Загрузить все задачи смены
2. Показать список задач для выполнения
3. После выполнения всех → запрос геолокации
4. **ВАЖНО**: Перед вызовом `shift_service.close_shift()` сохранить в `shift.notes`
5. Celery задача прочитает из `shift.notes` и создаст корректировки

#### Сохранение в notes - КРИТИЧНО
```python
# core_handlers.py handle_location() для UserAction.CLOSE_SHIFT
if shift_tasks:
    completed_info = json.dumps({
        'completed_tasks': user_state.completed_tasks,
        'task_media': user_state.task_media
    }, ensure_ascii=False)
    shift.notes = f"...[TASKS]{completed_info}"
    await session.commit()  # ← ОБЯЗАТЕЛЬНО!
```

#### Состояние UserState
```python
UserState(
    action=UserAction.CLOSE_SHIFT,
    step=UserStep.LOCATION_REQUEST,
    selected_shift_id=shift_id,
    shift_tasks=[...],
    completed_tasks=[0, 2],  # индексы выполненных
    task_media={...}
)
```

#### ✅ Работает
- Загружает задачи
- Сохраняет completed_tasks в shift.notes
- Celery создаёт корректировки

#### ❌ Не работает
- Нет унифицированной загрузки задач (копипаста кода)

#### 🟠 Проблемы
- Нет проверки "смена уже закрыта?"
- Нет уведомления пользователю о успехе

---

## Матрица проблем

| # | Проблема | Экран | Файл | Статус | Приоритет | Root Cause |
|---|----------|-------|------|--------|-----------|-----------|
| 1 | Селективные корректировки | Celery | `adjustment_tasks.py:341` | ✅ FIXED | 🔴 | `if not is_completed:` пропускал выполненные задачи со штрафом |
| 2 | Задачи не показываются при "Закрыть объект" | Close Object | `object_state_handlers.py` | ❌ OPEN | 🔴 | Не вызывается `_load_timeslot_tasks()` |
| 3 | Код загрузки задач дублируется | Open Shift + My Tasks | `shift_handlers.py` | ❌ OPEN | 🟠 | Нет единой функции `_collect_shift_tasks()` |
| 4 | Потеря completed_tasks при обновлении UserState | Close Object | `object_state_handlers.py` | ❌ OPEN | 🟠 | UserState перезаписывается вместо обновления |
| 5 | Нет кнопки для отправки геолокации | Open Shift + Open Object | `core_handlers.py` | ❌ OPEN | 🟠 | ReplyKeyboardMarkup не добавляется |
| 6 | Молчание после отправки геолокации | Close Shift | `core_handlers.py:200-305` | ⚠️ PARTIAL | 🟠 | Нет немедленного ответа пользователю |

---

## Техническое видение

### Как должно быть

#### Унифицированная загрузка задач
```python
async def _collect_shift_tasks(
    session: AsyncSession,
    shift: Shift,
    timeslot: Optional[TimeSlot] = None,
    object_: Optional[Object] = None
) -> List[Dict]:
    """Собрать ВСЕ задачи смены из обоих источников."""
    
    all_tasks = []
    
    # 1. Задачи тайм-слота (если есть)
    if timeslot:
        timeslot_tasks = await _load_timeslot_tasks(session, timeslot)
        all_tasks.extend(timeslot_tasks)
    
    # 2. Задачи объекта (если не игнорируются)
    if object_ and not (timeslot and timeslot.ignore_object_tasks):
        if object_.shift_tasks:
            for task in object_.shift_tasks:
                task_copy = dict(task)
                task_copy['source'] = 'object'
                all_tasks.append(task_copy)
    
    return all_tasks
```

#### Использование везде
```python
# При открытии смены
all_tasks = await _collect_shift_tasks(session, shift, shift.time_slot, shift.object)

# При "Мои задачи"
all_tasks = await _collect_shift_tasks(session, shift, shift.time_slot, shift.object)

# При закрытии объекта
all_tasks = await _collect_shift_tasks(session, shift, shift.time_slot, shift.object)

# При Celery обработке
all_tasks = await _collect_shift_tasks(session, shift, shift.time_slot, shift.object)
```

### Структура UserState
```python
@dataclass
class UserState:
    user_id: int
    action: UserAction
    step: UserStep
    
    # Текущая смена/объект
    selected_shift_id: Optional[int]
    selected_object_id: Optional[int]
    
    # Задачи и их выполнение
    shift_tasks: List[Dict] = field(default_factory=list)
    completed_tasks: List[int] = field(default_factory=list)
    task_media: Dict[str, Dict] = field(default_factory=dict)
    
    # Временные данные
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=...)
    
    # Методы
    def mark_task_completed(self, task_idx: int, media: Optional[Dict] = None):
        """Отметить задачу как выполненную."""
        if task_idx not in self.completed_tasks:
            self.completed_tasks.append(task_idx)
        if media:
            self.task_media[str(task_idx)] = media
        self.expires_at = datetime.now() + timedelta(minutes=5)
    
    def save_to_shift_notes(self) -> str:
        """Сохранить в формат shift.notes."""
        return json.dumps({
            'completed_tasks': self.completed_tasks,
            'task_media': self.task_media
        }, ensure_ascii=False)
```

---

## План работ

### Фаза 1: EMERGENCY FIX (DONE ✅)
- [x] Исправить селективные корректировки в `adjustment_tasks.py`
- [x] Тестирование на dev
- [x] Коммит `482629e`

### Фаза 2: Унификация загрузки задач (TODO)
- [ ] Создать функцию `_collect_shift_tasks()` в `shift_handlers.py`
- [ ] Заменить все вызовы в:
  - [ ] `_handle_open_planned_shift()`
  - [ ] `_handle_my_tasks()`
  - [ ] `_handle_close_object()`
  - [ ] `core_handlers.py` при location_request
  - [ ] `adjustment_tasks.py`

### Фаза 3: Исправление закрытия объекта (TODO)
- [ ] Использовать `_collect_shift_tasks()` при закрытии объекта
- [ ] Сохранять completed_tasks при обновлении UserState
- [ ] Тестирование на dev

### Фаза 4: UX улучшения (TODO)
- [ ] Добавить ReplyKeyboardMarkup для запроса геолокации
- [ ] Добавить кнопку "Главное меню" после успешного закрытия
- [ ] Добавить проверки "уже открыто?", "уже закрыто?"

### Фаза 5: Документирование и запуск на prod (TODO)
- [ ] Обновить этот документ с результатами
- [ ] Коммит всех changes
- [ ] Deploy на prod с подтверждением

---

## Статистика

- **Всего файлов**: 8 основных
- **Всего проблем найдено**: 6
- **CRITICAL**: 2
- **HIGH**: 2
- **MEDIUM**: 2
- **Статус**: 1 fixed, 5 open

