# 🎯 Итерация 23: UI/UX улучшения и исправления

**Дата начала:** 09 октября 2025  
**Приоритет:** Medium  
**Оценка времени:** 2-3 дня  
**Ответственный:** Development Team  

---

## 📋 Обзор

Итерация сфокусирована на улучшении пользовательского опыта и исправлении мелких багов в интерфейсе:
- Добавление ссылки на бота на странице входа
- Уточнение терминологии для геолокации
- Исправление дублирования символа @ в username
- Улучшение placeholder для полей почасовой ставки

---

## 🎯 Задачи

### 1. Добавить ссылку на бота на странице входа
**Приоритет:** High  
**Оценка:** 1 час  
**Файлы:**
- `apps/web/templates/auth/login.html`

**Описание:**
Добавить кнопку/ссылку для открытия бота, которая:
- На десктопе открывает `https://t.me/StaffProBot` в браузере
- На мобильных устройствах открывает приложение Telegram, если установлено
- Использовать универсальную ссылку `tg://resolve?domain=StaffProBot`

**Acceptance Criteria:**
- [ ] Кнопка "Открыть бота" отображается под формой входа
- [ ] При клике на десктопе открывается веб-версия Telegram
- [ ] При клике на мобильном открывается приложение Telegram (если установлено)
- [ ] Кнопка имеет привлекательный дизайн с иконкой Telegram
- [ ] Добавлена подсказка "Не знаете свой Telegram ID? Откройте бота и используйте команду /start"

**Технические детали:**
```html
<a href="https://t.me/StaffProBot" 
   target="_blank" 
   class="btn btn-outline-light btn-lg w-100 mt-3">
    <i class="bi bi-telegram me-2"></i>
    Открыть бота в Telegram
</a>
```

---

### 2. Уточнить текст "Макс. расстояние" → "Макс. расстояние от объекта для геолокации"
**Приоритет:** Medium  
**Оценка:** 30 минут  
**Файлы:**
- `apps/web/templates/owner/timeslots/edit.html` (строка 179)
- `apps/web/templates/owner/timeslots/create.html` (строка 277)
- `apps/web/templates/owner/objects/list.html` (строка 114)
- `apps/web/templates/owner/objects/edit.html` (строка 118)
- `apps/web/templates/owner/objects/detail.html` (строка 62)
- `apps/web/templates/owner/objects/create.html` (строка 123)
- `apps/web/templates/manager/timeslots/list.html` (строка 38)
- `apps/web/templates/manager/timeslots/index.html` (строка 37)
- `apps/web/templates/manager/timeslots/create.html` (строка 50)
- `apps/web/templates/manager/objects/edit.html` (строка 119)
- `apps/web/templates/manager/objects/detail.html` (строка 60)
- `apps/web/templates/manager/objects.html` (строка 181)

**Описание:**
Заменить все упоминания "Макс. расстояние" и "Максимальное расстояние (м)" на более понятный текст.

**Варианты замены:**
- В формах (label): "Макс. расстояние от объекта для геолокации (м)"
- В таблицах (компактно): "Макс. расстояние для геолокации"
- В карточках (маленький текст): "Макс. расстояние от объекта"

**Acceptance Criteria:**
- [ ] Все упоминания "Макс. расстояние" заменены на уточненные версии
- [ ] В формах создания/редактирования полный текст с пояснением
- [ ] В таблицах и карточках компактная версия
- [ ] Текст согласован между owner и manager интерфейсами

---

### 3. Исправить баг с двойным символом @ в username
**Приоритет:** High  
**Оценка:** 45 минут  
**Файлы:**
- `apps/web/templates/owner/employees/list.html` (строка 79)
- `apps/web/templates/manager/timeslot_detail.html` (строки 108, 158)
- `apps/web/templates/manager/employees.html` (строка 160)
- `apps/web/templates/admin/users_report.html` (строка 226)
- `apps/web/templates/admin/users.html` (строка 145)
- `apps/web/templates/admin/user_subscriptions.html` (строка 119)
- `apps/web/templates/admin/dashboard.html` (строка 156)

**Описание:**
Исправить отображение username - если username уже начинается с @, не добавлять второй.

**Было:**
```html
<small class="text-muted">@{{ employee.username or 'без username' }}</small>
```

**Должно быть:**
```html
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

**Acceptance Criteria:**
- [ ] Во всех местах где отображается username, проверяется наличие @ в начале
- [ ] Если username начинается с @, символ не дублируется
- [ ] Если username не начинается с @, символ добавляется
- [ ] Если username отсутствует, показывается "без username"
- [ ] Единообразие во всех интерфейсах (owner, manager, admin)

---

### 4. Изменить placeholder "500" → "Введите сумму" в полях "Почасовая ставка"
**Приоритет:** Low  
**Оценка:** 30 минут  
**Файлы:**
- `apps/web/templates/owner/timeslots/edit.html` (строка 62)
- `apps/web/templates/owner/templates/planning/edit.html` (строка 68)
- `apps/web/templates/owner/templates/planning/create.html` (строка 64)
- `apps/web/templates/owner/objects/create.html` (строки 72, 129, 130)
- `apps/web/templates/owner/employees/edit_contract.html` (строка 76)
- `apps/web/templates/owner/employees/create.html` (строка 152)

**Описание:**
Заменить конкретное значение "500" на нейтральный placeholder "Введите сумму".

**Acceptance Criteria:**
- [ ] Все поля с почасовой ставкой имеют placeholder "Введите сумму"
- [ ] Убрано фиксированное значение "500" из placeholder
- [ ] Сохранены все атрибуты валидации (min, step, required)
- [ ] Единообразие во всех формах

---

## 📊 Метрики успеха

- **UX улучшение:** Проще войти в систему через бота
- **Ясность интерфейса:** Понятнее назначение поля "Макс. расстояние"
- **Качество:** Нет дублирования @ в username
- **Гибкость:** Пользователи не ожидают конкретную ставку 500₽

---

## 🔄 План выполнения

### День 1
- [x] Создание плана итерации
- [ ] Задача 1: Добавление ссылки на бота (1 час)
- [ ] Задача 3: Исправление бага с @ (45 минут)
- [ ] Тестирование задач 1 и 3

### День 2
- [ ] Задача 2: Уточнение текста "Макс. расстояние" (30 минут)
- [ ] Задача 4: Изменение placeholder (30 минут)
- [ ] Комплексное тестирование
- [ ] Code review

### День 3 (резерв)
- [ ] Исправление замечаний
- [ ] Финальное тестирование
- [ ] Деплой на production
- [ ] Создание финального отчета

---

## ⚠️ Риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Ссылка на бота не открывается на iOS | Medium | Medium | Использовать универсальную ссылку t.me |
| Забыли какой-то шаблон с username | Low | Low | Поиск по всем шаблонам через grep |
| Пропущены файлы с "500" | Low | Low | Комплексный поиск по кодовой базе |

---

## 📝 Чек-лист перед деплоем

- [ ] Все задачи выполнены
- [ ] Код прошел review
- [ ] Тесты пройдены локально
- [ ] Тесты пройдены на dev окружении
- [ ] Нет linter ошибок
- [ ] Обновлена документация (если требуется)
- [ ] Создан финальный отчет
- [ ] Обновлен roadmap.md

---

## 🔗 Связанные документы

- [Roadmap](../roadmap.md)
- [Итерация 22: Финальный отчет](../iteration22/ITERATION_22_FINAL_REPORT.md)
- [Vision: UI/UX Guidelines](../../vision.md)

---

## 📌 Примечания

- Все изменения касаются только UI/UX, бэкенд логика не затрагивается
- Изменения обратно совместимы
- Не требуются миграции базы данных
- Минимальное влияние на производительность

