# 🔧 Техническое руководство: Итерация 23

Подробные инструкции по выполнению каждой задачи итерации 23.

---

## Задача 1: Ссылка на бота на странице входа

### Файл: `apps/web/templates/auth/login.html`

### Место вставки
После закрывающего тега `</form>` (после строки 83), перед `<hr>` (строка 85).

### Код для вставки

```html
<!-- Кнопка открытия бота -->
<div class="text-center mt-4">
    <p class="text-white-75 mb-2">
        <i class="bi bi-info-circle me-1"></i>
        Не знаете свой Telegram ID?
    </p>
    <a href="https://t.me/StaffProBot" 
       target="_blank" 
       class="btn btn-outline-light btn-lg w-100"
       style="border-radius: 15px; border: 2px solid rgba(255,255,255,0.5); background: rgba(255,255,255,0.1);">
        <i class="bi bi-telegram me-2"></i>
        Открыть бота в Telegram
    </a>
    <small class="text-white-50 d-block mt-2">
        Используйте команду /start для получения вашего ID
    </small>
</div>
```

### Альтернативный вариант (с универсальной ссылкой)

Если нужно, чтобы на мобильных открывалось приложение:

```html
<a href="tg://resolve?domain=StaffProBot" 
   onclick="window.open('https://t.me/StaffProBot', '_blank'); return false;"
   class="btn btn-outline-light btn-lg w-100"
   style="border-radius: 15px; border: 2px solid rgba(255,255,255,0.5); background: rgba(255,255,255,0.1);">
```

---

## Задача 2: Уточнение текста "Макс. расстояние"

### Стратегия замены

**Тип 1: Labels в формах (полный текст)**
```html
<!-- Было -->
<label for="max_distance" class="form-label">Максимальное расстояние (м)</label>

<!-- Стало -->
<label for="max_distance" class="form-label">Макс. расстояние от объекта для геолокации (м)</label>
```

**Тип 2: Компактный текст в карточках**
```html
<!-- Было -->
<small class="text-muted">Макс. расстояние</small>

<!-- Стало -->
<small class="text-muted">Макс. расстояние от объекта</small>
```

**Тип 3: Текст в таблицах**
```html
<!-- Было -->
<small class="text-muted">Макс. расстояние:</small><br>

<!-- Стало -->
<small class="text-muted">Макс. расстояние для геолокации:</small><br>
```

**Тип 4: Заголовки колонок**
```html
<!-- Было -->
<dt class="col-sm-4">Макс. расстояние:</dt>

<!-- Стало -->
<dt class="col-sm-4">Макс. расстояние от объекта:</dt>
```

### Список файлов для изменения

#### Owner интерфейс

1. **apps/web/templates/owner/timeslots/edit.html**
   - Строка 179: `<small class="text-muted">Макс. расстояние</small>`
   - Заменить на: `<small class="text-muted">Макс. расстояние от объекта</small>`

2. **apps/web/templates/owner/timeslots/create.html**
   - Строка 277: `<small class="text-muted">Макс. расстояние</small>`
   - Заменить на: `<small class="text-muted">Макс. расстояние от объекта</small>`

3. **apps/web/templates/owner/objects/list.html**
   - Строка 114: `<small class="text-muted">Макс. расстояние:</small><br>`
   - Заменить на: `<small class="text-muted">Макс. расстояние для геолокации:</small><br>`

4. **apps/web/templates/owner/objects/edit.html**
   - Строка 118: `<label for="max_distance" class="form-label">Максимальное расстояние (м)</label>`
   - Заменить на: `<label for="max_distance" class="form-label">Макс. расстояние от объекта для геолокации (м)</label>`

5. **apps/web/templates/owner/objects/detail.html**
   - Строка 62: `<dt class="col-sm-4">Макс. расстояние:</dt>`
   - Заменить на: `<dt class="col-sm-4">Макс. расстояние от объекта:</dt>`

6. **apps/web/templates/owner/objects/create.html**
   - Строка 123: `<label for="max_distance" class="form-label">Максимальное расстояние (м)</label>`
   - Заменить на: `<label for="max_distance" class="form-label">Макс. расстояние от объекта для геолокации (м)</label>`

#### Manager интерфейс

7. **apps/web/templates/manager/timeslots/list.html**
   - Строка 38: `<small class="text-muted">Макс. расстояние</small>`
   - Заменить на: `<small class="text-muted">Макс. расстояние от объекта</small>`

8. **apps/web/templates/manager/timeslots/index.html**
   - Строка 37: `<small class="text-muted">Макс. расстояние</small>`
   - Заменить на: `<small class="text-muted">Макс. расстояние от объекта</small>`

9. **apps/web/templates/manager/timeslots/create.html**
   - Строка 50: `<small class="text-muted">Макс. расстояние</small>`
   - Заменить на: `<small class="text-muted">Макс. расстояние от объекта</small>`

10. **apps/web/templates/manager/objects/edit.html**
    - Строка 119: `<label for="max_distance" class="form-label">Максимальное расстояние (м)</label>`
    - Заменить на: `<label for="max_distance" class="form-label">Макс. расстояние от объекта для геолокации (м)</label>`

11. **apps/web/templates/manager/objects/detail.html**
    - Строка 60: `<dt class="col-sm-4">Макс. расстояние:</dt>`
    - Заменить на: `<dt class="col-sm-4">Макс. расстояние от объекта:</dt>`

12. **apps/web/templates/manager/objects.html**
    - Строка 181: `Макс. расстояние: {{ object.max_distance_meters }}м`
    - Заменить на: `Макс. расстояние для геолокации: {{ object.max_distance_meters }}м`

---

## Задача 3: Исправление бага с двойным @

### Стандартный паттерн для всех шаблонов

```html
{% if employee.username %}
    {% if employee.username.startswith('@') %}
        {{ employee.username }}
    {% else %}
        @{{ employee.username }}
    {% endif %}
{% else %}
    без username
{% endif %}
```

### Список файлов для изменения

#### 1. apps/web/templates/owner/employees/list.html

**Строка 79** (режим карточек):
```html
<!-- Было -->
<small class="text-muted">@{{ employee.username or 'без username' }}</small>

<!-- Стало -->
<small class="text-muted">
    {% if employee.username %}
        {% if employee.username.startswith('@') %}
            {{ employee.username }}
        {% else %}
            @{{ employee.username }}
        {% endif %}
    {% else %}
        без username
    {% endif %}
</small>
```

**Примечание:** В режиме таблицы (строки 222-227) уже правильная реализация!

#### 2. apps/web/templates/manager/timeslot_detail.html

**Строка 108:**
```html
<!-- Было -->
<br><small class="text-muted">@{{ shift.user.username }}</small>

<!-- Стало -->
<br><small class="text-muted">
    {% if shift.user.username %}
        {% if shift.user.username.startswith('@') %}
            {{ shift.user.username }}
        {% else %}
            @{{ shift.user.username }}
        {% endif %}
    {% else %}
        без username
    {% endif %}
</small>
```

**Строка 158:** Аналогичное исправление.

#### 3. apps/web/templates/manager/employees.html

**Строка 160:**
```html
<!-- Было -->
<br><small class="text-muted">@{{ employee.username }}</small>

<!-- Стало -->
<br><small class="text-muted">
    {% if employee.username %}
        {% if employee.username.startswith('@') %}
            {{ employee.username }}
        {% else %}
            @{{ employee.username }}
        {% endif %}
    {% else %}
        без username
    {% endif %}
</small>
```

#### 4. apps/web/templates/admin/users_report.html

**Строка 226:**
```html
<!-- Было -->
<strong>@{{ user.username or 'не указан' }}</strong>

<!-- Стало -->
<strong>
    {% if user.username %}
        {% if user.username.startswith('@') %}
            {{ user.username }}
        {% else %}
            @{{ user.username }}
        {% endif %}
    {% else %}
        не указан
    {% endif %}
</strong>
```

#### 5. apps/web/templates/admin/users.html

**Строка 145:**
```html
<!-- Было -->
@{{ user.username or 'N/A' }}

<!-- Стало -->
{% if user.username %}
    {% if user.username.startswith('@') %}
        {{ user.username }}
    {% else %}
        @{{ user.username }}
    {% endif %}
{% else %}
    N/A
{% endif %}
```

#### 6. apps/web/templates/admin/user_subscriptions.html

**Строка 119:**
```html
<!-- Было -->
<p class="mb-1"><strong>Telegram:</strong> @{{ subscription.user.username or 'не указан' }}</p>

<!-- Стало -->
<p class="mb-1"><strong>Telegram:</strong> 
    {% if subscription.user.username %}
        {% if subscription.user.username.startswith('@') %}
            {{ subscription.user.username }}
        {% else %}
            @{{ subscription.user.username }}
        {% endif %}
    {% else %}
        не указан
    {% endif %}
</p>
```

#### 7. apps/web/templates/admin/dashboard.html

**Строка 156:**
```html
<!-- Было -->
<small class="text-muted">@{{ user.username or 'N/A' }}</small>

<!-- Стало -->
<small class="text-muted">
    {% if user.username %}
        {% if user.username.startswith('@') %}
            {{ user.username }}
        {% else %}
            @{{ user.username }}
        {% endif %}
    {% else %}
        N/A
    {% endif %}
</small>
```

---

## Задача 4: Изменение placeholder "500" → "Введите сумму"

### Список файлов для изменения

#### 1. apps/web/templates/owner/timeslots/edit.html

**Строка 62:**
```html
<!-- Было -->
placeholder="500">

<!-- Стало -->
placeholder="Введите сумму">
```

#### 2. apps/web/templates/owner/templates/planning/edit.html

**Строка 68:**
```html
<!-- Было -->
required min="0" value="{{ template.hourly_rate }}" placeholder="500">

<!-- Стало -->
required min="0" value="{{ template.hourly_rate }}" placeholder="Введите сумму">
```

#### 3. apps/web/templates/owner/templates/planning/create.html

**Строка 64:**
```html
<!-- Было -->
required min="0" placeholder="500">

<!-- Стало -->
required min="0" placeholder="Введите сумму">
```

#### 4. apps/web/templates/owner/objects/create.html

**Строка 72:**
```html
<!-- Было -->
placeholder="500"

<!-- Стало -->
placeholder="Введите сумму"
```

**Строки 129-130:**
```html
<!-- Было -->
value="500"
placeholder="500">

<!-- Стало -->
value=""
placeholder="Введите сумму">
```

**Примечание:** Убрать также `value="500"` если оно задает значение по умолчанию.

#### 5. apps/web/templates/owner/employees/edit_contract.html

**Строка 76:**
```html
<!-- Было -->
placeholder="500">

<!-- Стало -->
placeholder="Введите сумму">
```

#### 6. apps/web/templates/owner/employees/create.html

**Строка 152:**
```html
<!-- Было -->
placeholder="500 (или выберите объект с установленной ставкой)">

<!-- Стало -->
placeholder="Введите сумму (или выберите объект с установленной ставкой)">
```

---

## 🧪 Тестирование

### Чек-лист для задачи 1 (Ссылка на бота)

- [ ] Кнопка отображается на странице входа
- [ ] При клике открывается новая вкладка
- [ ] На десктопе открывается https://t.me/StaffProBot
- [ ] На мобильном (iOS) открывается приложение Telegram
- [ ] На мобильном (Android) открывается приложение Telegram
- [ ] Стили кнопки соответствуют общему дизайну страницы
- [ ] Текст подсказки читабелен и понятен

### Чек-лист для задачи 2 (Макс. расстояние)

- [ ] Проверены все 12 файлов
- [ ] В формах полный текст "Макс. расстояние от объекта для геолокации (м)"
- [ ] В карточках компактный текст "Макс. расстояние от объекта"
- [ ] В таблицах "Макс. расстояние для геолокации"
- [ ] Единообразие между owner и manager интерфейсами

### Чек-лист для задачи 3 (Двойной @)

- [ ] Проверены все 7 файлов
- [ ] Username без @ отображается с @
- [ ] Username с @ отображается без дублирования
- [ ] Отсутствие username показывает корректный fallback
- [ ] Проверено в owner интерфейсе
- [ ] Проверено в manager интерфейсе
- [ ] Проверено в admin интерфейсе

### Чек-лист для задачи 4 (Placeholder)

- [ ] Проверены все 6 файлов
- [ ] Placeholder изменен на "Введите сумму"
- [ ] Удалены значения по умолчанию "500" где необходимо
- [ ] Сохранены атрибуты валидации (min, step, required)
- [ ] Поле остается обязательным где требуется

---

## 📋 Скрипты для автоматизации

### Поиск всех упоминаний для проверки

```bash
# Найти все упоминания "Макс. расстояние"
grep -rn "Макс. расстояние\|Максимальное расстояние" apps/web/templates/

# Найти все упоминания "@{{ " (потенциальные баги)
grep -rn "@{{ .*username" apps/web/templates/

# Найти все placeholder="500"
grep -rn 'placeholder="500"' apps/web/templates/
```

### Массовая замена (использовать с осторожностью!)

```bash
# Пример для задачи 4 (после проверки каждого файла вручную!)
sed -i 's/placeholder="500"/placeholder="Введите сумму"/g' apps/web/templates/owner/templates/planning/create.html
```

---

## ✅ Финальная проверка

После выполнения всех задач:

1. Запустить проект локально
2. Протестировать каждую измененную страницу
3. Проверить адаптивность на мобильных
4. Убедиться в отсутствии linter ошибок
5. Создать коммиты с понятными сообщениями
6. Обновить roadmap.md
7. Создать финальный отчет

---

## 📝 Шаблон коммитов

```bash
git add apps/web/templates/auth/login.html
git commit -m "Добавление: ссылка на бота на странице входа (итерация 23, задача 1)"

git add apps/web/templates/owner/objects/*.html apps/web/templates/manager/objects/*.html
git commit -m "Улучшение: уточнение текста 'Макс. расстояние' (итерация 23, задача 2)"

git add apps/web/templates/*/employees/*.html apps/web/templates/admin/*.html
git commit -m "Исправление: баг с двойным @ в username (итерация 23, задача 3)"

git add apps/web/templates/owner/timeslots/*.html apps/web/templates/owner/templates/**/*.html
git commit -m "Улучшение: placeholder 'Введите сумму' для почасовой ставки (итерация 23, задача 4)"
```

