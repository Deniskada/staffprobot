# Инвентаризация: legacy TG vs MAX / notification_targets

Актуализация: 2026-03-21. Цель — зафиксировать, где чаты отчётов и рассылки **уже** идут через единые сервисы, а где остаётся прямой Telegram без MAX.

## 1. Чаты отчётов объекта (`telegram_report_chat_id` / targets)

| Путь | Через `notification_target_service` / broadcast | Комментарий |
|------|--------------------------------------------------|-------------|
| `get_telegram_report_chat_id_for_object` | ✅ Единая точка: targets → org → legacy колонка объекта | Все вызовы ниже должны опираться на неё, а не на `obj.telegram_report_chat_id` напрямую |
| `shared/services/report_group_broadcast.py` | ✅ `resolve_object_report_group_channels` + TG/MAX отправка | Celery ДР/праздники |
| `apps/web/routes/owner.py` | ✅ create/edit object: `get_object_report_targets` + upsert | Форма пишет в targets и legacy |
| `apps/bot/handlers_div/shift_handlers.py` | ✅ Медиа/отчёты: `get_telegram_report_chat_id_for_object` | Логи не путать с сырой колонкой (см. правки в коде) |

**Прямых обходов** резолвера в `core/celery` для групповых чатов не найдено (поздравления → `send_object_report_group_text`).

## 2. Прямой `Bot.send_message` / `telegram` chat_id (не группы отчётов)

| Файл | Назначение | MAX |
|------|------------|-----|
| `report_group_broadcast.py` | Группа TG при `allow_telegram` | Параллельно MAX в том же сервисе |
| `birthday_tasks.py` | Личные TG: сотрудник, владелец, менеджер | Не дублируется в MAX (отдельное решение продукта) |
| `offer_tasks.py` | Уведомления офферов в TG user id | Аналогично |
| `employee_offers.py` (web) | TG при действии из ЛК | Проверить по сценарию |
| `telegram_sender.py`, `pep_service.py` | Инфраструктура TG | Ок |
| `shift_handlers.py`, `core_handlers.py` | Ответы пользователю в личке TG | MAX — через unified/webhook |

## 3. Повторяемые команды проверки (из корня репозитория)

```bash
rg "telegram_report_chat_id|get_effective_report_chat_id" --glob "*.py" apps core shared
rg "Bot\\(token=" --glob "*.py" apps core shared
rg "send_object_report_group_text|resolve_object_report_group_channels" --glob "*.py"
```

После изменений — `pytest tests/unit -m ci_smoke`.

## 4. Следующие шаги (бэклог)

- Дублировать ли **личные** поздравления ДР (`birthday_tasks`) в MAX при привязке — продукт.
- `offer_tasks` / `employee_offers`: приоритет MAX для тех же событий, что и TG.
- Unified: перенос гео/планирования TG из `shift_handlers` — отдельный эпик.

См. также: `max-bot-implementation.md`, `max-rollout-runbook.md`.
