-- Миграция: Очистка всех данных Tasks v2
-- Дата: 29.10.2025
-- Причина: Подготовка к чистому старту Tasks v2 после мерджа
--
-- ВАЖНО: Удаляет ВСЕ данные о задачах (шаблоны, планы, выполнение)
--         для всех владельцев
--
-- Применение на dev:
--   docker compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d staffprobot_dev < doc/CLEAR_ALL_TASKS_V2.sql
--
-- Применение на проде:
--   ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod < doc/CLEAR_ALL_TASKS_V2.sql'

BEGIN;

-- ============================================================
-- Показать текущее состояние
-- ============================================================

SELECT 'task_templates_v2' as table_name, COUNT(*) as records_count FROM task_templates_v2
UNION ALL
SELECT 'task_plans_v2', COUNT(*) FROM task_plans_v2
UNION ALL
SELECT 'task_entries_v2', COUNT(*) FROM task_entries_v2
UNION ALL
SELECT 'payroll_adjustments (task_entry_v2_id)', COUNT(*) FROM payroll_adjustments WHERE task_entry_v2_id IS NOT NULL;


-- ============================================================
-- Очистка связанных данных
-- ============================================================

-- 1. Открепить корректировки от задач (не удалять сами корректировки!)
UPDATE payroll_adjustments 
SET task_entry_v2_id = NULL 
WHERE task_entry_v2_id IS NOT NULL;


-- ============================================================
-- Удаление данных Tasks v2 (в порядке зависимостей)
-- ============================================================

-- 2. Удалить записи выполнения задач (зависят от планов и шаблонов)
DELETE FROM task_entries_v2;

-- 3. Удалить планы задач (зависят от шаблонов)
DELETE FROM task_plans_v2;

-- 4. Удалить шаблоны задач (корневая таблица)
DELETE FROM task_templates_v2;


-- ============================================================
-- Проверка результата
-- ============================================================

SELECT 'task_templates_v2' as table_name, COUNT(*) as records_after FROM task_templates_v2
UNION ALL
SELECT 'task_plans_v2', COUNT(*) FROM task_plans_v2
UNION ALL
SELECT 'task_entries_v2', COUNT(*) FROM task_entries_v2
UNION ALL
SELECT 'payroll_adjustments (task_entry_v2_id)', COUNT(*) FROM payroll_adjustments WHERE task_entry_v2_id IS NOT NULL;

COMMIT;

-- ============================================================
-- ВАЖНО: После миграции
-- ============================================================
-- 1. Очистить кэш Redis:
--    docker compose -f docker-compose.dev.yml exec redis redis-cli FLUSHALL
--
-- 2. Перезапустить веб-контейнер:
--    docker compose -f docker-compose.dev.yml restart web

