# Статус реализации расширения профиля владельца

## Ветка: feature/owner-profile-extension

## ✅ Завершено

### 1. База данных и миграции
- ✅ Создана таблица `organization_profiles` для хранения реквизитов ИП/ЮЛ
- ✅ Создана таблица `system_features` для справочника функций системы
- ✅ Расширена таблица `owner_profiles` новыми полями:
  - `about_company` - О компании
  - `values` - Ценности
  - `photos` - Фотографии (JSON, до 5 шт)
  - `contact_phone` - Телефон для связи
  - `contact_messengers` - Активные мессенджеры (JSON)
  - `enabled_features` - Включенные функции (JSON)
- ✅ Добавлено поле `organization_profile_id` в `org_structure_units`
- ✅ Миграции применены: `a266c36de460`, `da5277f32d13`

### 2. Конфигурация и справочники
- ✅ Создан `core/config/features.py` с реестром функций системы
- ✅ Seed-скрипт `scripts/seed_system_features.py` - заполнение функций
- ✅ Seed-скрипт `scripts/seed_organization_tags.py` - добавление тегов реквизитов
- ✅ Добавлено 26 тегов реквизитов (11 для ИП, 15 для ЮЛ)
- ✅ Создано 10 системных функций в БД

### 3. Модели
- ✅ `domain/entities/organization_profile.py` - профиль организации
- ✅ `domain/entities/system_feature.py` - функция системы
- ✅ Расширены `OwnerProfile` и `OrgStructureUnit`

### 4. Сервисы
- ✅ `shared/services/organization_profile_service.py` - управление профилями организаций
  - Создание/обновление/удаление профилей
  - Установка профиля по умолчанию
  - Получение тегов для шаблонов
- ✅ `shared/services/system_features_service.py` - управление функциями
  - Получение статуса функций для пользователя
  - Включение/выключение функций
  - Проверка доступности в тарифе

### 5. API Роуты
- ✅ `apps/web/routes/organization_profiles.py` - базовые endpoint'ы для профилей

## 🔄 В процессе / TODO

### 6. API Роуты (требуется доработка)
- ⏸ Роуты для функций в профиле владельца
- ⏸ Расширение `/owner/profile` для новых секций
- ⏸ API для загрузки фотографий
- ⏸ Полная реализация создания/редактирования профилей организаций

### 7. Frontend (основная работа)
- ⏸ Реорганизация `/owner/profile/index.html`:
  - Переместить справку по тегам в левую колонку (компактный список)
  - Добавить в левую колонку управление профилями организаций
  - Заменить правую колонку на новые секции:
    - А) О компании (textarea)
    - Б) Ценности (textarea)
    - В) Фотографии (галерея + загрузка)
    - Г) Для связи (телефон + чекбоксы мессенджеров)
    - Д) Управление функциями (список с toggle)

- ⏸ Модальное окно для профиля организации:
  - Переключатель ИП/ЮЛ
  - Динамическая форма с полями из `org_data.md`
  - Валидация реквизитов

- ⏸ JavaScript модули:
  - `profile-manager.js` - управление профилем
  - `organization-profiles.js` - CRUD профилей организаций
  - `features-manager.js` - управление функциями

### 8. Реорганизация меню
- ⏸ Обновление `apps/web/templates/owner/base_owner.html`
- ⏸ Новая структура согласно `menu_structure.md`:
  - Календарь - только для функции #5
  - Планирование (submenu) - функция #6
  - Зарплаты и премии (submenu) - функции #8, #9
- ⏸ Template фильтр `has_feature` для Jinja2
- ⏸ Middleware для проверки доступа к функциям

### 9. Элементы форм
- ⏸ Анализ и документирование в `form_elements_visibility.md`:
  - Какие поля в формах объектов зависят от функций
  - Какие поля в формах сотрудников зависят от функций
  - Скрытие элементов на основе `enabled_features`

### 10. Регистрация и тарифы
- ⏸ Обновить процесс регистрации:
  - Назначение максимального тарифа по умолчанию
  - Создание профиля с включенными всеми функциями
  - Создание пустого профиля организации

### 11. Тестирование
- ⏸ Локальное тестирование функционала
- ⏸ Проверка видимости меню
- ⏸ Проверка CRUD профилей организаций
- ⏸ Тестирование загрузки фото

### 12. Документация
- ⏸ Создать `form_elements_visibility.md`
- ⏸ Обновить после деплоя

## 📋 Функции системы (реализовано в БД)

1. **recruitment_and_reviews** - Найм сотрудников, отзывы и рейтинги
   - menu_items: applications, reviews
   
2. **telegram_bot** - Telegram-бот

3. **notifications** - Уведомления

4. **basic_reports** - Базовые отчёты
   - menu_items: reports
   
5. **shared_calendar** - Общий календарь
   - menu_items: calendar
   
6. **payroll** - Штатное расписание, начисления, выплаты
   - menu_items: planning_shifts, planning_departments, planning_schedule
   - form_elements: employee_time_slot
   
7. **contract_templates** - Шаблоны договоров
   - menu_items: planning_contracts
   - form_elements: object_contract_template
   
8. **bonuses_and_penalties** - Начисления премий и штрафов
   - menu_items: payroll_payouts, payroll_accruals
   - form_elements: employee_bonus_penalty
   
9. **shift_tasks** - Задачи сотрудникам на смену
   - menu_items: moderation_cancellations, analytics_cancellations
   - form_elements: shift_tasks_section
   
10. **analytics** - Аналитика
    - menu_items: analytics

## 🔑 Теги реквизитов (добавлены в БД)

### Для ИП (individual):
- owner_fullname, owner_ogrnip, owner_inn, owner_okved
- owner_phone, owner_email
- owner_registration_address, owner_postal_address
- owner_account_number, owner_bik, owner_correspondent_account

### Для ЮЛ (legal):
- company_full_name, company_short_name, company_ogrn, company_inn, company_kpp
- company_legal_address, company_postal_address
- company_okpo, company_okved
- company_account_number, company_bik, company_correspondent_account
- company_director_position, company_director_fullname, company_basis

## 🚀 Дальнейшие шаги

1. **Frontend реализация** - основной объём работы:
   - Реорганизация страницы профиля
   - Модальное окно для профилей организаций
   - JavaScript для управления

2. **Реорганизация меню** с условной видимостью

3. **Middleware и фильтры** для проверки функций

4. **Анализ и скрытие элементов форм**

5. **Обновление процесса регистрации**

6. **Тестирование** всего функционала

7. **Документация** и деплой

## 💡 Примечания

- Все изменения БД применены локально
- Seed-скрипты успешно выполнены
- Базовая backend инфраструктура готова
- Frontend требует значительной доработки
- Тестирование не проводилось
- Деплой на прод НЕ выполнен

## 📝 Команды для продолжения

```bash
# Переключиться на ветку
git checkout feature/owner-profile-extension

# Запустить dev окружение
docker compose -f docker-compose.dev.yml up -d

# Просмотреть статус БД
docker compose -f docker-compose.dev.yml exec web python -c "
from scripts.seed_system_features import *
import asyncio
asyncio.run(seed_system_features())
"

# При необходимости пересоздать seed данные
docker compose -f docker-compose.dev.yml exec web python scripts/seed_system_features.py
docker compose -f docker-compose.dev.yml exec web python scripts/seed_organization_tags.py
```

## ⚠️ Важно

- **НЕ мерджить в main** без завершения frontend части
- **НЕ деплоить** без полного тестирования
- **НЕ удалять** файлы документации из `docs/owner_profile/`

