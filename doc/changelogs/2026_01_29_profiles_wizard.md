# Changelog: Мастер профилей для управляющего и сотрудника (29.01.2026)

## Обзор
Унификация мастерa «Мои профили» для ролей управляющего и сотрудника: общий shared-компонент, кнопки редактирования/удаления в карточках профиля, исправления 500 и JS, выравнивание выпадающего меню профиля.

## Изменения

### 1. Таблица «Мои профили» на страницах профиля
- **Управляющий** (`/manager/profile`): в блоке «Мои профили» для каждой записи добавлены кнопки «Редактировать» (переход на `/manager/profiles?profile_id={id}`) и «Удалить» (DELETE `/api/profiles/{id}`, перезагрузка списка). Функция `spDeleteProfile` в inline-скрипте.
- **Сотрудник** (`/employee/profile`): аналогично — кнопки редактирования (`/employee/profiles?profile_id={id}`) и удаления через `spDeleteEmployeeProfile`, перезагрузка списка без перезагрузки страницы.

### 2. Мастер профилей (страницы `/manager/profiles` и `/employee/profiles`)
- Общий HTML: `shared/profiles_wizard.html` (подключается с `back_url` и `close_redirect_url` в зависимости от роли).
- Общий JS: `js/shared/profiles_wizard.js` (все функции `sp*`: открытие мастера, создание/редактирование/сохранение, KYC, адреса, вкладки).
- Контекст: роуты передают `yandex_maps_api_key`, `selected_profile_id`; в шаблоне задаются `back_url` и `close_redirect_url`.
- **Управляющий**: `manager/profile/profiles.html` — только контейнер + include wizard, блок `manager_extra_js` с Yandex Maps API, `address_map.js`, `profiles_wizard.js`. Дублирующий блок заголовка и кнопок типов профиля удалён.
- **Сотрудник**: `employee/profile/profiles.html` — контейнер + include wizard, блок `extra_js` с `{{ super() }}`, Yandex Maps API, `address_map.js`, `profiles_wizard.js`. Дублирующий блок заголовка и кнопок удалён.

### 3. Исправление 500 на `/employee/profiles`
- **Причина:** в `employee_profiles_page` использовался `os.getenv("YANDEX_MAPS_API_KEY", "")` без глобального импорта `os`.
- **Решение:** в `apps/web/routes/employee.py` добавлен глобальный `import os` в начало файла; локальный `import os` внутри обработчика `/employee/objects` удалён (единый стиль с `manager_profiles.py`).

### 4. Исправление «spCreateNewProfileFromList is not defined» на `/employee/profiles`
- На странице сотрудника не подключался `profiles_wizard.js`. В `employee/profile/profiles.html` добавлен блок `{% block extra_js %}` с подключением Yandex Maps API, `js/shared/address_map.js`, `js/shared/profiles_wizard.js` (и `{{ super() }}`).

### 5. Выравнивание выпадающего меню профиля
- В навбаре при клике по иконке пользователя (Профиль / Настройки у управляющего, Профиль у сотрудника) меню уезжало правым краем за экран.
- **Решение:** для выпадающего меню профиля добавлен класс `dropdown-menu-end` (Bootstrap 5): правый край меню совпадает с правым краем триггера.
- **Файлы:** `apps/web/templates/manager/base_manager.html`, `apps/web/templates/employee/base_employee.html` — у `<ul class="dropdown-menu">` профиля добавлен класс `dropdown-menu-end`.

## Файлы
- `apps/web/templates/manager/profile.html` — кнопки редактирования/удаления в таблице профилей, `spDeleteProfile`.
- `apps/web/templates/employee/profile.html` — кнопки редактирования/удаления, `spDeleteEmployeeProfile`.
- `apps/web/templates/manager/profile/profiles.html` — убран дубль заголовка, блок `manager_extra_js` со скриптами.
- `apps/web/templates/employee/profile/profiles.html` — убран дубль заголовка, блок `extra_js` со скриптами.
- `apps/web/routes/employee.py` — глобальный `import os`, удалён локальный импорт в обработчике objects.
- `apps/web/templates/manager/base_manager.html` — `dropdown-menu dropdown-menu-end` для меню профиля.
- `apps/web/templates/employee/base_employee.html` — `dropdown-menu dropdown-menu-end` для меню профиля.
- Общие компоненты (без изменений в этом чейндже): `shared/profiles_wizard.html`, `js/shared/profiles_wizard.js`, `js/shared/address_map.js`; API `/api/profiles/`, `/api/profiles/{id}` (DELETE).

## Документация
- В `doc/vision_v1/roles/manager.md` и `doc/vision_v1/roles/employee.md` добавлены роуты и шаблоны мастера профилей.
- В `doc/DOCUMENTATION_RULES.md` добавлена запись в «Недавние изменения».
