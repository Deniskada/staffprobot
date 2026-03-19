# Engineering log

Generated from `doc/changelog-entries.md`.
Run: `python3 scripts/build_engineering_log.py doc/changelog-entries.md doc/engineering-log.md`

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

