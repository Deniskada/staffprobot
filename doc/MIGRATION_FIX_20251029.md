# Исправление миграций (29.10.2025)

## Проблема

После мерджа feature/rules-tasks-incidents в main возникла ошибка:
```
column payroll_adjustments.shift_schedule_id does not exist
```

## Причина

БД на dev оказалась в промежуточном состоянии:
- Таблицы feature-ветки уже существуют (rules, task_templates_v2, incidents)
- Но некоторые колонки не были добавлены
- alembic_version указывал на старую миграцию (20251022_001)

## Решение

### 1. Обновлена версия миграций:
```bash
docker compose -f docker-compose.dev.yml exec web alembic stamp 78851600b877
```

### 2. Добавлены отсутствующие колонки вручную:
```sql
ALTER TABLE payroll_adjustments 
ADD COLUMN IF NOT EXISTS shift_schedule_id INTEGER REFERENCES shift_schedules(id),
ADD COLUMN IF NOT EXISTS task_entry_v2_id INTEGER REFERENCES task_entries_v2(id);

CREATE INDEX IF NOT EXISTS ix_payroll_adjustments_shift_schedule_id ON payroll_adjustments(shift_schedule_id);
CREATE INDEX IF NOT EXISTS ix_payroll_adjustments_task_entry_v2_id ON payroll_adjustments(task_entry_v2_id);
```

## Проверка

```bash
# Проверка текущей версии
docker compose -f docker-compose.dev.yml exec web alembic current
# Результат: 78851600b877 (head)

# Проверка наличия колонок
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "\d payroll_adjustments"
# Результат: shift_schedule_id и task_entry_v2_id присутствуют
```

## На проде

На проде миграции нужно применить стандартным способом:
```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic upgrade head'
```

Если возникнет аналогичная проблема, применить SQL скрипт выше.

## Статус

✅ Dev: исправлено, работает  
⏳ Prod: миграции будут применены при деплое


