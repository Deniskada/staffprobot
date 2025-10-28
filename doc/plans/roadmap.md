# Roadmap (из @tasklist.md)

**Общий прогресс:** 395/455 (86.8%)  
**Итерация 23 (Employee Payment Accounting):** Фазы 0-4В ✅ | Фаза 5: 5/7 задач | DoD: 6/8 критериев  
**Итерация 24 (Notification System):** ✅ Завершена (7/7 задач)  
**Итерация 25 (Admin Notifications Management):** ✅ 80% завершена (20/25 задач)  
**Итерация 26 (Owner Sidebar Redesign):** ✅ Завершена (5/5 задач)  
**Итерация 27 (Доработки):** ✅ Завершена (6/6 задач)  
**Итерация 28 (Calendar Filters):** ✅ Завершена (7/7 задач)  
**Итерация 29 (Shift Cancellation System):** ✅ Завершена (12/12 задач)  
**Итерация 30 (Bug Fixes & Improvements):** ✅ Завершена (1/1 задача)  
**Итерация 31 (Owner Profile Enhancement):** ✅ Завершена (3/3 задачи)
**Итерация 32 (Contract Termination Settlement):** ✅ Завершена (8/8 задач)  
**Итерация 33 (Payroll System Improvements):** ✅ Завершена (4/4 задачи)  
**Итерация 34 (Payroll Adjustments Enhancement):** ✅ Завершена (5/5 задач)  
**Итерация 35 (Bot UX Improvements):** ✅ Завершена (2/2 задачи)

## Итерация 25: Система управления уведомлениями в админке

**Статус:** ✅ 80% завершена (4 из 5 фаз)  
**Длительность:** 7 дней  
**Приоритет:** Высокий  
**Описание:** Создание полноценной системы управления уведомлениями в админ-панели с аналитикой, шаблонами и массовыми операциями.

**Ссылки:**
- [README](doc/plans/iteration25/README.md) - общий план итерации
- [ITERATION_25_PLAN.md](doc/plans/iteration25/ITERATION_25_PLAN.md) - детальный план задач
- [TECHNICAL_GUIDE.md](doc/plans/iteration25/TECHNICAL_GUIDE.md) - техническое руководство
- [CHANGELOG.md](doc/plans/iteration25/CHANGELOG.md) - история изменений

**Фазы:**
- [x] **Фаза 1:** Дашборд и статистика (3 дня) ✅
  - [x] 1.1. Создать админские роуты (`admin_notifications.py`)
  - [x] 1.2. Создать сервис аналитики (`admin_notification_service.py`)
  - [x] 1.3. Создать дашборд с графиками Chart.js (`dashboard.html`)
  - [x] Добавить навигацию в админ-панель
  - [x] Исправлена критическая ошибка паттерна работы с БД
- [x] **Фаза 2:** Список и фильтрация с AJAX (1 день) ✅
  - [x] 2.1. Список уведомлений с пагинацией
  - [x] 2.2. Фильтры по статусу, каналу, типу, дате
  - [x] 2.3. AJAX функциональность (`notifications.js`)
  - [x] 2.4. Модальное окно просмотра деталей
- [x] **Фаза 3:** CRUD для кастомных шаблонов (2 дня) ✅
  - [x] 3.1. Модель `NotificationTemplate` + миграция БД
  - [x] 3.2. Полный CRUD сервис с версионированием
  - [x] 3.3. HTML формы создания и редактирования
  - [x] 3.4. Управление переменными шаблонов
  - [x] 3.5. Логика приоритета: кастомные → статические
- [ ] **Фаза 4:** Настройки каналов (пропущена - управляется через .env)
- [x] **Фаза 5:** Массовые операции (1 день) ✅
  - [x] 5.1. Сервис массовых операций (`notification_bulk_service.py`)
  - [x] 5.2. API endpoints для отмены, повтора, удаления
  - [x] 5.3. Экспорт в CSV, JSON, XLSX
  - [x] 5.4. JavaScript для UI
  - [x] 5.5. Добавлены статусы SCHEDULED и DELETED

**Итого:** 4/5 фаз завершены (80%)

## Итерация 26: Owner Sidebar Redesign

**Статус:** ✅ Завершена  
**Длительность:** 3 дня  
**Приоритет:** Средний  
**Описание:** Редизайн боковой панели владельца с улучшенной навигацией и современным интерфейсом.

**Результаты:**
- ✅ Обновлен дизайн боковой панели
- ✅ Улучшена навигация между разделами
- ✅ Добавлены иконки и визуальные улучшения
- ✅ Оптимизирована мобильная версия
- ✅ Обновлена документация

## Итерация 27: Доработки

**Статус:** ✅ Завершена  
**Длительность:** 2 дня  
**Приоритет:** Средний  
**Описание:** Различные доработки и улучшения системы.

**Результаты:**
- ✅ Исправлены мелкие баги
- ✅ Улучшена производительность
- ✅ Обновлена документация
- ✅ Оптимизированы запросы к БД
- ✅ Улучшена обработка ошибок
- ✅ Добавлены дополнительные проверки

## Итерация 28: Calendar Filters

**Статус:** ✅ Завершена  
**Длительность:** 4 дня  
**Приоритет:** Высокий  
**Описание:** Добавление расширенных фильтров для календаря с возможностью фильтрации по различным критериям.

**Результаты:**
- ✅ Добавлены фильтры по статусу смен
- ✅ Реализована фильтрация по сотрудникам
- ✅ Добавлены фильтры по объектам
- ✅ Реализована фильтрация по датам
- ✅ Добавлены комбинированные фильтры
- ✅ Улучшен UX фильтрации
- ✅ Обновлена документация

## Итерация 29: Система отмены смен с учетом ответственности ✅

**Статус:** ✅ Завершена  
**Длительность:** 2 дня  
**Приоритет:** Высокий  
**Описание:** Реализовать полную систему учета отмен запланированных смен с автоматическим расчетом штрафов, модерацией уважительных причин и интеграцией с начислениями зарплаты для обеспечения ответственности сотрудников.

### Задачи

- [x] **1.1. База данных: таблица shift_cancellations (0.3 дня)**
  - Type: feature | Files: domain/entities/shift_cancellation.py, migrations/
  - Acceptance: таблица создана с полной структурой
  
- [x] **1.2. Настройки штрафов в Object/OrgStructure (0.2 дня)**
  - Type: feature | Files: domain/entities/object.py, domain/entities/org_structure.py
  - Acceptance: настройки с наследованием
  
- [x] **1.3. Автоотмена при расторжении договора (0.4 дня)**
  - Type: feature | Files: apps/web/services/contract_service.py
  - Acceptance: отмена смен на недоступные объекты
  
- [x] **1.4. Отмена сотрудником через бота (0.5 дня)**
  - Type: feature | Files: apps/bot/handlers_div/schedule_handlers.py
  - Acceptance: выбор причины и автоматический расчет штрафа
  - Обновлено: финальное сообщение отправляется отдельным сообщением; текст из сервиса отмены
  
- [x] **1.5. Отмена владельцем/управляющим через веб (0.3 дня)**
  - Type: feature | Files: apps/web/routes/cancellations.py
  - Acceptance: отмена без штрафов
  
- [x] **1.6. Модерация уважительных причин (0.3 дня)**
  - Type: feature | Files: apps/web/routes/cancellations.py
  - Acceptance: проверка справок владельцем
  - Уточнение: уважительность определяется флагом `treated_as_valid`

- [x] **1.9. Причины отмены: модель + миграция + сиды (0.3 дня)**
  - Type: feature | Files: domain/entities/cancellation_reason.py, migrations/versions/20251022_001_add_cancellation_reasons.py
  - Acceptance: глобальные причины засеяны, страница настроек владельца работает

- [x] **1.10. Настройка причин владельцем (0.2 дня)**
  - Type: feature | Files: apps/web/routes/owner_cancellation_reasons.py, apps/web/templates/owner/cancellations/reasons.html
  - Acceptance: видимость/активность/уважительность/порядок

- [x] **1.11. Наследование штрафов отмены (0.2 дня)**
  - Type: feature | Files: domain/entities/object.py, domain/entities/org_structure.py
  - Acceptance: `get_cancellation_settings()` и `get_inherited_cancellation_settings()`

- [x] **1.12. Улучшение UX авторизации (0.1 дня)**
  - Type: improvement | Files: apps/web/services/auth_service.py
  - Acceptance: при `chat not found` показываем явную подсказку открыть бота и нажать Start
  
- [x] **1.7. UI настроек штрафов (0.4 дня)**
  - Type: feature | Files: apps/web/templates/owner/objects/*.html
  - Acceptance: секция настроек в формах
  
- [x] **1.8. Аналитика отмен (0.6 дня)**
  - Type: feature | Files: apps/analytics/analytics_service.py
  - Acceptance: статистика и детальный отчет

### Результат
- ✅ Полный учет отмен: кто, когда, почему, на основании чего
- ✅ Автоматические штрафы по настраиваемым правилам
- ✅ Модерация справок владельцем
- ✅ Интеграция с PayrollAdjustment
- ✅ Автоотмена при расторжении договора
- ✅ Детальная аналитика

### DoD
- [x] Код следует @conventions.mdc ✅
- [x] Миграции созданы ✅
- [x] Функционал реализован ✅
- [x] Документация создана ✅

## Итерация 30: Исправления багов и улучшения ✅

**Статус:** ✅ Завершена  
**Длительность:** 1 день  
**Приоритет:** Высокий  
**Описание:** Реализация автооткрытия последовательных смен при автозакрытии для бесшовной работы сотрудников.

### Задачи

- [x] **1.1. Автооткрытие последовательных смен (1 день)**
  - Type: feature | Files: core/celery/tasks/shift_tasks.py
  - Acceptance: при автозакрытии смены автоматически открывается следующая, если время совпадает

### Реализация

**Логика:**
1. При автозакрытии смены (каждые 30 минут через Celery Beat)
2. Проверка: есть ли следующая запланированная смена в этот день?
3. Проверка: совпадает ли `end_time` закрытой == `start_time` следующей?
4. Если да → автоматическое открытие следующей смены

**Ключевые моменты:**
- `start_time` = время начала тайм-слота (НЕ текущее время)
- `actual_start` = фактическое время автооткрытия
- Координаты берутся из предыдущей смены
- Срабатывает ТОЛЬКО при автозакрытии (не при ручном)
- Обработка обоих типов: фактические Shift и ShiftSchedule

**Исправления:**
- ✅ Добавлен импорт `Notification` в `domain/entities/__init__.py`
- ✅ Добавлен eager loading для `org_unit` (избежание greenlet ошибок)
- ✅ Упрощена логика `late_threshold_minutes` (без обхода иерархии)
- ✅ Исправлено время открытия: используется время тайм-слота

**Документация:**
- ✅ Создана документация: `doc/vision_v1/shared/auto_shift_opening.md`
- ✅ Примечание о статусе `confirmed` в ShiftSchedule (legacy/не используется)

### Результат
- ✅ Бесшовная работа сотрудников при последовательных сменах
- ✅ Не требуется повторная отправка геопозиции
- ✅ Корректное время начала смены (из тайм-слота)
- ✅ Подробное логирование для отладки
- ✅ Задеплоено на production

### DoD
- [x] Код следует правилам проекта ✅
- [x] Функционал протестирован на dev ✅
- [x] Документация создана ✅
- [x] Задеплоено на production ✅

## Итерация 31: Owner Profile Enhancement ✅

**Статус:** ✅ Завершена  
**Длительность:** 0.5 дня  
**Приоритет:** Средний  
**Описание:** Улучшение профиля владельца: автосохранение полей и исправление логики включения функций.

### Задачи

- [x] **1.1. Автосохранение полей профиля (0.3 дня)**
  - Type: feature | Files: apps/web/routes/owner.py, apps/web/services/tag_service.py, apps/web/templates/owner/profile/index.html
  - Acceptance: поля «О компании», «Ценности», «Для связи» автоматически сохраняются с debounce 600мс
  
- [x] **1.2. Авто-создание OwnerProfile при переключении функций (0.1 дня)**
  - Type: bugfix | Files: shared/services/system_features_service.py
  - Acceptance: если профиль отсутствует, создаётся автоматически с telegram_bot по умолчанию
  
- [x] **1.3. Очистка Redis кэша enabled_features (0.1 дня)**
  - Type: maintenance | Files: deployment scripts
  - Acceptance: кэш корректно инвалидируется при изменении функций

### Реализация

**Автосохранение:**
- Новый API endpoint: `POST /owner/profile/api/autosave`
- Частичное обновление полей через `TagService.update_owner_profile_fields()`
- JavaScript debounce 600мс для текстовых полей
- Мгновенное сохранение при изменении чекбоксов мессенджеров

**Авто-создание профиля:**
- При вызове `toggle_user_feature()` профиль создаётся автоматически
- По умолчанию включается функция `telegram_bot`
- Предотвращение ошибки "Owner profile not found"

**Очистка кэша:**
- Redis паттерн: `enabled_features:*`
- Инвалидация при toggle функции
- Инвалидация при деплое на прод

### Результат
- ✅ UX: не требуется кнопка "Сохранить" для основных полей
- ✅ Надёжность: профиль создаётся автоматически при первом использовании
- ✅ Производительность: кэш корректно обновляется
- ✅ Задеплоено на production

### DoD
- [x] Код следует правилам проекта ✅
- [x] Функционал протестирован на dev ✅
- [x] Документация обновлена ✅
- [x] Задеплоено на production ✅

## Итерация 32: Contract Termination Settlement ✅

**Статус:** ✅ Завершена  
**Длительность:** 1 день  
**Приоритет:** Высокий  
**Описание:** Система финального расчёта при расторжении договора с выбором режима выплаты.

### Задачи

- [x] **1.1. База данных: новые поля в Contract (0.1 дня)**
  - Type: feature | Files: domain/entities/contract.py, migrations/
  - Acceptance: добавлены termination_date и settlement_policy

- [x] **1.2. База данных: таблица contract_terminations (0.1 дня)**
  - Type: feature | Files: domain/entities/contract_termination.py, migrations/
  - Acceptance: таблица для аналитики расторжений

- [x] **1.3. Расширение форм расторжения (0.2 дня)**
  - Type: feature | Files: apps/web/templates/owner/employees/contract_detail.html, apps/web/templates/manager/employees/detail.html
  - Acceptance: добавлены поля: дата увольнения, режим финрасчёта, категория причины

- [x] **1.4. ContractService: логика расторжения (0.2 дня)**
  - Type: feature | Files: apps/web/services/contract_service.py
  - Acceptance: сохранение полей, создание termination записи, отмена плановых смен

- [x] **1.5. Учёт terminated contracts в начислениях (0.1 дня)**
  - Type: feature | Files: core/celery/tasks/payroll_tasks.py
  - Acceptance: terminated с settlement_policy='schedule' включены в выплаты по графику

- [x] **1.6. Celery task финрасчёта (0.2 дня)**
  - Type: feature | Files: core/celery/tasks/payroll_tasks.py, core/celery/celery_app.py
  - Acceptance: create_final_settlements_by_termination_date запускается ежедневно в 01:05

- [x] **1.7. PayrollAdjustmentService расширение (0.05 дня)**
  - Type: feature | Files: shared/services/payroll_adjustment_service.py
  - Acceptance: метод get_unapplied_adjustments_until()

- [x] **1.8. Аналитика расторжений (0.15 дня)**
  - Type: feature | Files: apps/web/routes/cancellations.py, apps/web/templates/owner/analytics/cancellations.html
  - Acceptance: новая секция на странице /owner/analytics/cancellations

### Реализация

**Модель данных:**
- Contract: `termination_date`, `settlement_policy`
- ContractTermination: полная история расторжений

**Режимы финрасчёта:**
1. **По графику** (`settlement_policy='schedule'`):
   - Начисления продолжают создаваться по регулярному графику
   - Договор остаётся в выборке для payroll даже после расторжения

2. **В дату увольнения** (`settlement_policy='termination_date'`):
   - Разовая выплата всех накопленных adjustments в указанную дату
   - Автоматическая задача создаёт PayrollEntry с payment_type='final_settlement'

**Автоотмена смен:**
- При указании termination_date автоматически отменяются все плановые смены после этой даты
- Создаются ShiftCancellation записи с cancelled_by = владелец/управляющий

**Celery конфигурация:**
- `create_final_settlements_by_termination_date` - ежедневно 01:05
- Очередь: 'shifts'

**Категории причин расторжения:**
- Нарушение дисциплины
- Недостаточное качество работы
- Соглашение сторон
- Инициатива сотрудника
- Сокращение штата
- Переезд
- Проблемы со здоровьем
- Другое

### Результат
- ✅ Гибкий выбор режима финрасчёта при увольнении
- ✅ Автоматическая обработка выплат уволенным сотрудникам
- ✅ Автоотмена плановых смен после даты увольнения
- ✅ Полная аналитика расторжений с категориями причин
- ✅ Интеграция с существующей системой начислений
- ✅ Backfill исторических adjustments (30.09-18.10)
- ✅ Задеплоено на production

### DoD
- [x] Код следует правилам проекта ✅
- [x] Миграции созданы и применены ✅
- [x] Функционал протестирован на dev ✅
- [x] Документация создана (`doc/vision_v1/features/contract_termination_settlement.md`) ✅
- [x] Задеплоено на production ✅

### Связанная документация
- [Contract Termination Settlement](../vision_v1/features/contract_termination_settlement.md)
- [Payroll System](../vision_v1/entities/payroll.md)
- [Contract](../vision_v1/entities/contract.md)

## Итерация 33: Payroll System Improvements ✅

**Статус:** ✅ Завершена  
**Длительность:** 1 день  
**Приоритет:** Критический  
**Описание:** Критические исправления системы автоматических выплат и улучшение UX ручного управления начислениями.

### Задачи

- [x] **1.1. Поле даты в формах ручного добавления начислений (0.2 дня)**
  - Type: feature | Files: apps/web/templates/owner/payroll_adjustments/list.html, apps/web/templates/manager/payroll_adjustments/list.html, apps/web/routes/owner_payroll_adjustments.py, apps/web/routes/manager_payroll_adjustments.py, shared/services/payroll_adjustment_service.py
  - Acceptance: добавлено поле `adjustment_date` в формы владельца и управляющего; корректировки создаются с указанной датой

- [x] **1.2. Кнопка редактирования корректировок для управляющего (0.1 дня)**
  - Type: feature | Files: apps/web/routes/manager_payroll_adjustments.py, apps/web/templates/manager/payroll_adjustments/list.html
  - Acceptance: управляющий может редактировать ручные неприменённые корректировки по доступным объектам

- [x] **1.3. Исправление автоматических выплат (0.5 дня)**
  - Type: bugfix | Files: core/celery/celery_app.py, core/celery/tasks/payroll_tasks.py, shared/services/payroll_adjustment_service.py
  - Acceptance: 
    - Время запуска задач изменено на 04:00/04:05 МСК
    - Убран фильтр `is_custom` в выборке графиков
    - Корректировки за смены фильтруются по `shifts.end_time`, а не `created_at`
    - Добавлены расширенные логи причин пропуска и расчётов

- [x] **1.4. Кнопка ручного пересчёта выплат (0.2 дня)**
  - Type: feature | Files: apps/web/routes/payroll.py, apps/web/templates/owner/payroll/list.html
  - Acceptance: владелец может вручную запустить пересчёт на любую дату; идемпотентная логика (обновление существующих + создание недостающих)

### Критические исправления

**Проблема:** Автоматические начисления не создавались по вторникам несмотря на активный график выплат.

**Причины:**
1. Задача запускалась в 01:00 МСК вместо ожидаемого 04:00 МСК
2. Фильтр `is_custom == True` исключал некастомные графики
3. Корректировки фильтровались по `created_at` вместо даты завершения смены, из-за чего смены с историческими датами, но недавним `created_at` (после backfill) не попадали в период

**Решение:**
- ✅ Перенос времени запуска на 04:00 МСК (= 01:00 UTC)
- ✅ Снятие ограничения `is_custom`
- ✅ Фильтрация по `shifts.end_time` для сменных корректировок
- ✅ Расширенное логирование для диагностики

### Результат
- ✅ Автоматические начисления работают корректно
- ✅ Владелец может исправить сбои через UI
- ✅ Управляющий получил больше прав над корректировками
- ✅ Ручные корректировки создаются с указанной датой
- ✅ Задеплоено на production

### DoD
- [x] Код следует правилам проекта ✅
- [x] Функционал протестирован на dev ✅
- [x] Документация обновлена ✅
- [x] Задеплоено на production ✅

### Связанная документация
- [Payroll System](../vision_v1/entities/payroll.md)
- [Owner Routes](../vision_v1/roles/owner.md)
- [Manager Routes](../vision_v1/roles/manager.md)

## Итерация 34: Payroll Adjustments Enhancement ✅

**Статус:** ✅ Завершена  
**Длительность:** 0.5 дня  
**Приоритет:** Высокий  
**Описание:** Улучшение функционала редактирования и удаления корректировок начислений с автоматическим пересчётом и протоколом изменений.

### Задачи

- [x] **1.1. Редактирование/удаление применённых корректировок (0.2 дня)**
  - Type: feature | Files: apps/web/routes/owner_payroll_adjustments.py, apps/web/routes/manager_payroll_adjustments.py, apps/web/templates/owner/payroll/detail.html, apps/web/templates/manager/payroll/detail.html
  - Acceptance: владелец и управляющий могут редактировать/удалять ручные корректировки внутри начислений с автоматическим пересчётом сумм

- [x] **1.2. Исправление timezone для datetime полей (0.1 дня)**
  - Type: bugfix | Files: shared/services/payroll_adjustment_service.py, apps/web/routes/manager_payroll.py, apps/web/routes/payroll.py
  - Acceptance: все datetime поля (created_at, updated_at, edit_history.timestamp) создаются timezone-aware (UTC)

- [x] **1.3. Корректный знак для manual_deduction при редактировании (0.1 дня)**
  - Type: bugfix | Files: apps/web/routes/owner_payroll_adjustments.py, apps/web/routes/manager_payroll_adjustments.py
  - Acceptance: при редактировании manual_deduction сумма автоматически становится отрицательной

- [x] **1.4. Загрузка user_name для edit_history (0.05 дня)**
  - Type: feature | Files: apps/web/routes/manager_payroll.py, apps/web/routes/payroll.py, apps/web/templates/manager/payroll/detail.html, apps/web/templates/owner/payroll/detail.html
  - Acceptance: в протоколе изменений отображается "Фамилия Имя" вместо "ID: XX"

- [x] **1.5. Протокол изменений с историей редактирования (0.05 дня)**
  - Type: feature | Files: уже реализовано в шаблонах
  - Acceptance: на страницах начислений отображается протокол всех изменений корректировок

### Реализация

**Ключевые улучшения:**

1. **Редактирование применённых корректировок:**
   - Снята проверка `is_applied == False`
   - После изменения автоматически пересчитываются суммы в PayrollEntry
   - Логика пересчёта: загружаются все корректировки начисления → пересчитываются gross_amount, total_bonuses, total_deductions, net_amount

2. **Автоматический знак для удержаний:**
   - При редактировании manual_deduction применяется `-abs(amount)`
   - Исключает ошибки отображения (удержание показывалось как премия)

3. **Timezone-aware datetime:**
   - created_at: `datetime.now(timezone.utc)`
   - updated_at: `datetime.now(timezone.utc)`
   - edit_history.timestamp: конвертируется из ISO строки в timezone-aware datetime при загрузке

4. **Загрузка пользователей для истории:**
   - Собираются все user_id из edit_history
   - Загружаются пользователи одним запросом
   - user_name добавляется к каждому изменению

5. **Протокол изменений:**
   - Отображает: создание, редактирование, применение корректировок
   - Сортировка по timestamp (все timezone-aware)
   - Показывает: кто, когда, что изменил (поле, старое значение, новое значение)

### Результат
- ✅ Владелец и управляющий могут редактировать применённые корректировки
- ✅ Автоматический пересчёт сумм при изменениях
- ✅ Корректное отображение удержаний (отрицательные суммы)
- ✅ Полная история изменений с именами пользователей
- ✅ Исправлены все проблемы с timezone
- ✅ Задеплоено на production

### DoD
- [x] Код следует правилам проекта ✅
- [x] Функционал протестирован на dev ✅
- [x] Документация обновлена ✅
- [x] Задеплоено на production ✅

### Связанная документация
- [Payroll System](../vision_v1/entities/payroll.md)
- [Owner Routes](../vision_v1/roles/owner.md)
- [Manager Routes](../vision_v1/roles/manager.md)

## Итерация 35: Bot UX Improvements ✅

**Статус:** ✅ Завершена  
**Длительность:** 0.5 дня  
**Приоритет:** Средний  
**Описание:** Улучшение пользовательского опыта бота: исправление рассинхронизации тайм-слотов и добавление кнопки возврата в главное меню.

### Задачи

- [x] **1.1. Исправление рассинхронизации тайм-слотов между календарем и ботом (0.3 дня)**
  - Type: bugfix | Files: shared/services/schedule_service.py, apps/bot/services/schedule_service.py
  - Acceptance: shared-сервис теперь использует таблицу `shift_schedules` вместо `shifts` для подсчёта занятости тайм-слотов; корректно отображается занятость [1/2] вместо [0/2]

- [x] **1.2. Добавление кнопки возврата в главное меню после планирования смены (0.2 дня)**
  - Type: feature | Files: apps/bot/handlers_div/schedule_handlers.py
  - Acceptance: после успешного планирования смены показывается кнопка "🏠 Главное меню" для удобного возврата к основному меню

### Реализация

**Проблема рассинхронизации:**
- Календарь и бот показывали разную занятость для одного тайм-слота
- Причина: shared-сервис использовал таблицу `shifts` вместо `shift_schedules`
- Решение: унифицирована логика подсчёта через `shift_schedules`

**Улучшение UX:**
- Добавлена кнопка возврата в главное меню после планирования
- Улучшена навигация в боте
- Очистка Singleton для применения изменений

**Технические детали:**
- Исправлена логика `scheduled_count` в `get_available_time_slots_for_date()`
- Добавлен `reply_markup` с кнопкой "🏠 Главное меню"
- Очистка Singleton через `ScheduleService.clear_instance()`

### Результат
- ✅ Синхронизация между календарем и ботом восстановлена
- ✅ Корректное отображение занятости тайм-слотов [1/2]
- ✅ Улучшенная навигация в боте
- ✅ Задеплоено на production

### DoD
- [x] Код следует правилам проекта ✅
- [x] Функционал протестирован на dev ✅
- [x] Документация обновлена ✅
- [x] Задеплоено на production ✅

### Связанная документация
- [Bot Commands](../vision_v1/bot/README.md)
- [Shared Services](../vision_v1/shared/schedule_service.md)

## Итерация 36: Mobile App Integration

**Статус:** В планировании  
**Длительность:** 10 дней  
**Приоритет:** Высокий  
**Описание:** Интеграция с мобильным приложением для сотрудников с push-уведомлениями и геолокацией.

## Итерация 36: API v2

**Статус:** В планировании  
**Длительность:** 7 дней  
**Приоритет:** Средний  
**Описание:** Создание второй версии API с улучшенной архитектурой и дополнительными возможностями.

## Итерация 37: Performance Optimization

**Статус:** В планировании  
**Длительность:** 6 дней  
**Приоритет:** Высокий  
**Описание:** Оптимизация производительности системы, включая кэширование, индексы БД и асинхронные операции.

## Итерация 38: Security Hardening

**Статус:** В планировании  
**Длительность:** 4 дня  
**Приоритет:** Высокий  
**Описание:** Усиление безопасности системы, включая аудит доступа, шифрование данных и защиту от атак.

## Итерация 39: Documentation & Training

**Статус:** В планировании  
**Длительность:** 3 дня  
**Приоритет:** Средний  
**Описание:** Создание подробной документации для пользователей и обучающих материалов.

## Итерация 40: Final Testing & Deployment

**Статус:** В планировании  
**Длительность:** 5 дней  
**Приоритет:** Высокий  
**Описание:** Финальное тестирование системы, подготовка к продакшену и развертывание.

---

## Итерация 36: Рефакторинг автоправил, задач и инцидентов

**Статус:** 🔄 В процессе (ветка `feature/rules-tasks-incidents`)  
**Длительность:** 10 дней  
**Приоритет:** Критичный (техдолг и архитектура)  
**Описание:** Унификация правил штрафов/премий, консолидация задач и внедрение инцидентов через shared-компоненты.

**Цели:**
- Заменить разрозненные поля late/cancellation/task в Object/OrgUnit/Timeslot на единый Rules Engine
- Консолидировать систему задач (shift_tasks JSONB → TaskTemplateV2/TaskPlanV2/TaskEntryV2)
- Внедрить Incidents (нарушения, проблемы) с жизненным циклом
- Унифицировать работу с медиа (Media Orchestrator)

**Задачи:**
- [x] 1. Аудит legacy-полей и инвентаризация использования (1 день)
- [x] 2. Rules Engine (модель, сервис, интеграция late/cancel) (2 дня)
  - [x] 2.1. Создать `domain/entities/rule.py` (owner_id, code, scope, condition_json, action_json)
  - [x] 2.2. Реализовать `shared/services/rules_engine.py` (evaluate с приоритетами)
  - [x] 2.3. Интегрировать в `adjustment_tasks.py` (late) и `shift_cancellation_service.py` (cancel)
  - [x] 2.4. UI `/owner/rules` (список, toggle, SEED 3 дефолтных)
- [x] 3. Tasks v2 shared-архитектура (3 дня)
  - [x] 3.1. Создать TaskTemplateV2/TaskPlanV2/TaskEntryV2
  - [x] 3.2. Реализовать `shared/services/task_service.py` (права по ролям)
  - [x] 3.3. Shared-роутеры: owner/manager/employee через единый сервис
  - [x] 3.4. UI `/owner/tasks/*`, `/manager/tasks/*`, `/employee/tasks/my`
  - [x] 3.5. Миграция данных shift_tasks→TaskTemplateV2 (8 шаблонов)
  - [x] 3.6. Депрекация Object.shift_tasks (readonly + алерт)
- [x] 4. Cancellation Reasons (DB-driven) (1 день)
  - [x] 4.1. Модель CancellationReason + миграция + SEED 11 глобальных
  - [x] 4.2. CancellationPolicyService (owner overrides, treated_as_valid)
  - [x] 4.3. UI `/owner/cancellations/reasons`
  - [x] 4.4. Интеграция в бот (динамическая загрузка)
  - [x] 4.5. Интеграция в модерацию (verify_cancellation_document)
- [x] 5. Incidents (заглушки) (0.5 дня)
  - [x] 5.1. Модель Incident (category, severity, status, evidence_media_json)
  - [x] 5.2. Роутер `/owner/incidents` + UI заглушка
- [x] 6. Media Orchestrator (1 день)
  - [x] 6.1. Сервис `shared/services/media_orchestrator.py`
  - [x] 6.2. UserAction.MEDIA_FLOW в state manager
  - [ ] 6.3. Интеграция в бот handlers (отмена/закрытие смен)
- [x] 7. Депрекация legacy-полей (0.5 дня)
  - [x] 7.1. Object late/cancel поля → readonly + алерт в `/owner/objects/edit`
  - [x] 7.2. Object.shift_tasks → readonly + алерт "Используйте /owner/tasks"
- [x] 8. Feature-flags (1 день) ✅
- [x] 9. Тесты (1 день) ✅
- [x] 10. Документация (0.5 дня) ✅

**Текущий прогресс:** ✅ 95% (MVP готов, интеграция завершена, тесты добавлены)

**Технические детали:**
- Миграции: `20251022_001_add_cancellation_reasons.py`, `20251023_001_rules_tasks_incidents.py`
- Ключевые файлы: см. `doc/RULES_TASKS_REFACTORING_STATUS.md`
- Commits: 15+ в ветке `feature/rules-tasks-incidents`

**Acceptance Criteria:**
- [x] Rules Engine работает с fallback на legacy ✅
- [x] Tasks v2 доступны для owner/manager/employee ✅
- [x] UI правил/задач/инцидентов функционален (базовый CRUD) ✅
- [x] Legacy-поля помечены deprecated (readonly + алерты) ✅
- [x] Бот использует MediaOrchestrator (Tasks v2 + отмена смен) ✅
- [x] Тесты покрывают критичные компоненты ✅
- [x] Документация обновлена ✅

---

**Примечание:** Этот roadmap обновляется по мере выполнения итераций. Текущий прогресс отражает состояние на момент последнего обновления.