# Changelog entries (source for engineering log)

Append endlog entries in format:

## YYYY — Title

Problem
...

Engineering
...

Business value
...

Tech
...

---

## 2026 — Фаза 1: docs foundation и endlog протокол

Problem
Нужно унифицировать документацию и правила endlog для перехода к self-updating docs-driven платформе.

Engineering
Добавлены стандартизированные doc-файлы (ru/en), project-manifest.yaml, integration manifests и единый протокол #endlog в rules.

Business value
Проект подготовлен к автоматической синхронизации документации и генерации портфолио.

Tech
Markdown, YAML, Cursor rules.

---

## 2026 — Skill tg-max-bots: единая логика Telegram + MAX

Problem
Нужно добавлять поддержку MAX-бота без дублирования логики Telegram-бота (команды, FSM, клавиатуры, ответы), чтобы новые каналы не удваивали стоимость разработки и сопровождения.

Engineering
Зафиксирован и оформлен паттерн «Adapter → NormalizedUpdate → общий Handler» на базе практики из cvetbuket.com: единый DTO входящего апдейта, тонкие адаптеры транспорта и единый слой бизнес-логики. Скилл подключён к проекту staffprobot как проектный справочник с пошаговым гайдом внедрения MAX-бота под текущий стек (python-telegram-bot).

Business value
Снижается time-to-market для новых мессенджеров и риск расхождения поведения между ботами. Подготовлена база для запуска MAX-бота StaffProBot без переписывания продуктовой логики.

Tech
Cursor skill, дизайн контрактов (DTO/интерфейсы), Telegram Bot API, MAX platform-api.max.ru.

---

## 2026 — Фаза 1 MAX: messenger_accounts, notification_targets, owner.py

Problem
Подготовка к MAX-боту требует: запись в messenger_accounts при регистрации, чтение report chat из notification_targets (вместо legacy telegram_report_chat_id), чёткое разделение user_id и telegram_id в owner.py, сохранение targets при редактировании объекта.

Engineering
- messenger_accounts: при register_user и веб-регистрации добавляется запись (provider=telegram)
- notification_targets: сервис get_telegram_report_chat_id_for_object; все вызовы obj.get_effective_report_chat_id() заменены в shift_handlers, core_handlers, schedule_handlers, birthday_tasks
- owner.py: get_user_id_from_current_user использует JWT id; добавлена _telegram_id_from_current_user; исправлены дубли lookup
- upsert_object_telegram_report_target в object_service при create/update объекта

Business value
Готовность моделей и веб-части к multi-messenger; без регрессий TG.

Tech
SQLAlchemy, FastAPI, Python, notification_target_service, object_service.

---

## 2026 — MAX-бот: полный цикл внедрения (Фазы 2–5, деплой, стабилизация)

Problem
StaffProBot работал только через Telegram. Нужно добавить второй мессенджер (MAX / platform-api.max.ru) без дублирования бизнес-логики: единые обработчики смен, объектов, планирования, задач, уведомлений; привязка MAX-аккаунтов к внутренним пользователям; деплой webhook на прод с feature-флагом и откатом.

Engineering
- **Unified bot layer** (`shared/bot_unified/`): `NormalizedUpdate` DTO, `TgAdapter`/`MaxAdapter` парсинг, `UnifiedBotRouter` диспатч, `TgMessenger`/`MaxMessenger` выходные адаптеры; ~3500 строк новых обработчиков (shift, object, schedule, misc, my_id_linking, user_resolver)
- **MAX client** (`MaxClient`): отправка текста/фото/callback answer, скачивание медиа по token, извлечение public link из ответа API
- **Webhook** (`apps/web/routes/max_webhook.py`): приём апдейтов MAX, feature-флаг `MAX_FEATURES_ENABLED`
- **Привязка мессенджеров**: одноразовые коды в ЛК → `/start CODE` в MAX/TG; профиль сотрудника — блок «Мессенджеры»; `messenger_link_service`
- **notification_targets**: org_unit scope, upsert для TG и MAX; fallback на legacy `telegram_report_chat_id`; broadcast через `report_group_broadcast` (TG+MAX)
- **Уведомления MAX**: `MaxNotificationSender`, канал `max` в `NotificationDispatcher`; персональные prefs MAX в ЛК
- **Web UI**: карточки сотрудников TG+MAX, договоры без жёсткой привязки TG, owner/manager формы с MAX ID, вычистка TG-only копирайта (landing, тарифы, support hub, OTP, менеджер добавления)
- **TG unified migration**: `main_menu`, `status`, `view_schedule`, `schedule_shift` через unified router; `get_report` — legacy `EarningsReportHandlers` (интерактивный); user state key по `telegram_id` для TG, `internal_id` для MAX
- **Прод-деплой**: nginx `max.staffprobot.ru`, DNS/TLS, регистрация webhook, env MAX_BOT_TOKEN/WEBHOOK; `docker-compose.prod.yml` дополнен MAX-переменными
- **CI**: `ci_smoke` gate (28 тестов) — адаптеры, public link, каналы уведомлений, state key; новые тесты `test_user_state_storage_key`, `test_bot_unified_adapters` (location), `test_notification_max_channel`
- **Стабилизация**: исправление потери TG-сессии при отправке гео (state key по `telegram_id`), персонализация `main_menu` с `START_KEYBOARD` для обоих мессенджеров

Business value
Пользователи MAX получают полный набор функций бота (смены, объекты, задачи, планирование, уведомления) наравне с Telegram. Владельцы управляют чатами отчётов для обоих мессенджеров. Платформа готова к масштабированию на новые каналы без переписывания логики.

Tech
Python, FastAPI, python-telegram-bot, MAX platform-api.max.ru, SQLAlchemy, Redis, Docker Compose, Nginx, GitHub Actions, pytest.
