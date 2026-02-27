# Progress: Implementation Status

## Текущий статус

**Эпик: Оферта + KYC ЕСИА + ПЭП**  
Фаза: A+B (backend-инфраструктура) — завершена  
Прогресс: 8/8 задач текущего спринта

### Выполнено (2026-02-15)
- ✅ `NotificationType`: 7 новых типов (OFFER_SENT/ACCEPTED/REJECTED/TERMS_CHANGED, KYC_REQUIRED/VERIFIED/FAILED)
- ✅ `base_templates.py`: шаблоны OFFER_TEMPLATES + KYC_TEMPLATES, подключены в ALL_TEMPLATES
- ✅ Миграция `offer_edo_260215`: ContractType "offer", ConstructorFlow (6 шагов, 13 фрагментов), pep_metadata, file_key, seed NotificationTypeMeta
- ✅ `Contract.pep_metadata` + `ContractVersion.file_key` — модели обновлены
- ✅ `PepService` + `TelegramPepChannel` + `SmsPepChannel` (заглушка) — `shared/services/pep_service.py`
- ✅ `ContractPdfService` (weasyprint HTML→PDF + S3 upload) — `shared/services/contract_pdf_service.py`
- ✅ `weasyprint>=62.0` добавлен в requirements.txt

## Наблюдения

- S3-инфраструктура полностью готова (MinIO dev и prod) — не нужно создавать с нуля
- KYC-сервис есть как заглушка (`GosuslugiKycProvider`) — нужна только реальная реализация
- Конструктор договоров работает (ConstructorFlow/Step/Fragment) — нужны только seed-данные для оферты
- Система уведомлений полная — нужны новые типы и шаблоны
- Profile/IndividualProfile уже содержит все поля для реквизитов (паспорт, СНИЛС, адреса, банк)

## Проблемы и решения

| Проблема | Решение |
|----------|---------|
| Клиентская лицензия КриптоПро не подходит для сервера | Триал 3 мес. для dev, серверная лицензия для prod |
| Нет client_id ЕСИА | Фазы A+B не зависят от ЕСИА, делаем параллельно с заявкой |
| ПЭП через ТГ — юридическая валидность | Абстракция каналов, SMS для прода |

---

**Обновлено**: 2026-02-15
