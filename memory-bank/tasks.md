# Tasks: StaffProBot Development

## Активные задачи

### Эпик: Оферта + KYC ЕСИА + ПЭП (doc/plans/offer_edo_plan.md)

#### Фаза A (сейчас)

| # | Задача | Статус | Файлы |
|---|--------|--------|-------|
| 1.1 | Seed-миграция: ContractType "offer" | ⏳ Ожидает | migrations/ |
| 1.2 | ConstructorFlow для оферты (9 шагов) | ⏳ Ожидает | migrations/, constructor_service.py |
| 1.3 | Доработка build_template() для подстановки из профиля владельца | ⏳ Ожидает | constructor_service.py |
| 1.4 | UI: множественные оферты в списке шаблонов | ⏳ Ожидает | templates/contracts/ |
| 4.1 | Новые NotificationType (OFFER_*, KYC_*) | ⏳ Ожидает | notification.py |
| 4.2 | Шаблоны уведомлений для оферт | ⏳ Ожидает | base_templates.py |
| 4.3 | Seed NotificationTypeMeta | ⏳ Ожидает | migrations/ |

#### Фаза B (параллельно)

| # | Задача | Статус | Файлы |
|---|--------|--------|-------|
| 3.1 | Статус pending_acceptance в Contract | ⏳ Ожидает | contract.py |
| 3.2 | UI создания договора по оферте (owner) | ⏳ Ожидает | routes/, templates/ |
| 3.3 | Валидация заполненности реквизитов в профиле сотрудника | ⏳ Ожидает | profile_service.py, templates/ |
| 3.3a | Страница акцепта оферты (employee) | ⏳ Ожидает | routes/, templates/ |
| 3.3b | Бейдж KYC-верификации в профилях (employee, owner, карточки) | ⏳ Ожидает | templates/ |
| 3.4 | PepService + TelegramPepChannel | ⏳ Ожидает | shared/services/pep_service.py |
| 3.5 | ContractPdfService (weasyprint) | ⏳ Ожидает | shared/services/contract_pdf_service.py |
| 3.6 | Фиксация подписания + S3 | ⏳ Ожидает | contract services |
| 3.7 | Миграция: file_key, pep_metadata | ⏳ Ожидает | migrations/ |

#### Фаза C (после ЕСИА client_id)

| # | Задача | Статус | Файлы |
|---|--------|--------|-------|
| 2.1 | Docker cryptopro-sign | ⏳ Блокер | docker-compose, infrastructure/ |
| 2.2 | EsiaClient (Python) | ⏳ Блокер | infrastructure/external/esia/ |
| 2.3 | Реальный GosuslugiKycProvider | ⏳ Блокер | kyc_service.py |
| 2.4 | Callback /auth/esia/callback | ⏳ Блокер | routes/auth.py |

## Блокировки

- **ЕСИА client_id**: нужна регистрация ИС → заявка в Минцифры (2-4 недели)
- **Серверная лицензия КриптоПро**: триал 3 мес. для dev, серверная лицензия для prod

## Завершённые задачи

_Пока нет_

---

**Обновлено**: 2026-02-15
