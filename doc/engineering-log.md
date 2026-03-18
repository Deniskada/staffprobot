# Engineering log

Generated from `doc/changelog-entries.md`.

Run endlog pipeline to refresh this file.

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
