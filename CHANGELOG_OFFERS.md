# Changelog: Оферты, подписание договоров, уведомления

**Дата:** 1 марта 2026  
**Ветка:** `main`

---

## Обзор

Реализована процедура подписания любого договора сотрудником (ПЭП), упрощена форма создания/редактирования договора, исправлена система Telegram-уведомлений.

---

## Новые возможности

### Подписание договоров сотрудником
- Все договоры создаются со статусом `pending_acceptance` — сотрудник обязан подписать
- Подписание через простую электронную подпись (ПЭП): OTP-код в Telegram
- Генерация PDF подписанного договора с метаданными ПЭП
- Загрузка документов сотрудником (паспорт, СНИЛС и т.д.) через MinIO/S3
- Страница `/employee/offers` — список всех договоров сотрудника
- Страница `/employee/offers/{id}` — просмотр и подписание договора

### Уведомления при создании и изменении договоров
- При создании договора → Telegram-уведомление сотруднику
- При смене шаблона договора → сброс подписи, уведомление сотруднику о переподписании
- При подписании оферты → Telegram-уведомление владельцу
- При отклонении оферты → Telegram-уведомление владельцу

### Упрощение формы создания договора
- Убраны поля: Имя, Фамилия, Телефон, Email, Дата рождения (сотрудник заполняет сам при подписании)
- Убрано поле «Название договора» — автогенерация: `Договор {номер}`
- Убрано поле «Система оплаты труда» — наследуется от объекта

### Упрощение формы редактирования договора
- Убраны поля: Название договора, Система оплаты труда
- При смене шаблона: контент перегенерируется из нового шаблона

### Роли и доступ
- `APPLICANT` получил доступ к отзывам (`/employee/reviews`, API)
- `APPLICANT` получил доступ к профилям (API)

---

## Исправления

### Уведомления
- Исправлен `NotificationService` — убраны `CAST` к несуществующим PostgreSQL enum-типам
- Исправлен вызов `NotificationService()` — класс не принимает аргументов
- Исправлены параметры `create_notification()`: `type` вместо `notification_type`, добавлены `channel`, `title`, `message`
- Исправлен фильтр `scheduled_at <= now` — добавлена обработка `NULL` (уведомления отправлялись без `scheduled_at`)
- Исправлен `TelegramNotificationSender` — убран глобальный синглтон, решена проблема Pool timeout в Celery

### Отображение
- Время подписания оферты: конвертация UTC → Europe/Moscow через фильтр `format_datetime_local`
- Текст оферты: HTML-форматирование вместо plain text

### Прочее
- Автогенерация `title` при пустом значении (создание и редактирование)
- Миграция: таблица `profile_documents`, поле `rejection_reason` в `contracts`

---

## Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `apps/web/services/contract_service.py` | Подписание всех договоров, автогенерация title, уведомления, сброс при смене шаблона |
| `apps/web/routes/employee_offers.py` | Роуты подписания, OTP, список оферт, отклонение |
| `apps/web/routes/owner.py` | Упрощение форм создания/редактирования |
| `apps/web/templates/employee/offers/accept.html` | UI подписания с ПЭП |
| `apps/web/templates/employee/offers/list.html` | Список договоров сотрудника |
| `apps/web/templates/owner/employees/create.html` | Убраны лишние поля |
| `apps/web/templates/owner/employees/edit_contract.html` | Убраны лишние поля |
| `shared/services/notification_service.py` | Убраны CAST, исправлены SQL |
| `shared/services/offer_service.py` | Логика подписания, проверка профиля |
| `shared/services/senders/telegram_sender.py` | Убран синглтон, fix pool timeout |
| `core/celery/tasks/notification_tasks.py` | Обработка NULL scheduled_at |
| `apps/web/routes/shared_reviews.py` | Доступ APPLICANT |
| `apps/web/routes/shared_profiles.py` | Доступ APPLICANT |
| `domain/entities/contract.py` | Поле rejection_reason |
| `migrations/versions/20260228_profile_documents_and_rejection.py` | Миграция БД |
