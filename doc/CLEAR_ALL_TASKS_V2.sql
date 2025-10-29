-- Миграция: Очистка всех задач (v1 - legacy JSONB)
-- Дата: 29.10.2025
-- Причина: Подготовка к переходу на Tasks v2 после мерджа
--
-- ВАЖНО: 
--   НА DEV: Очищает objects.shift_tasks (legacy) + таблицы Tasks v2 (если есть)
--   НА ПРОДЕ: Очищает ТОЛЬКО objects.shift_tasks (legacy), т.к. Tasks v2 там ещё нет
--
-- Применение на dev:
--   docker compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d staffprobot_dev < doc/CLEAR_ALL_TASKS_V2.sql
--
-- Применение на проде:
--   ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod < doc/CLEAR_ALL_TASKS_V2.sql'

BEGIN;

-- ============================================================
-- ЧАСТЬ 1: Очистка СТАРЫХ задач (Objects.shift_tasks - JSONB)
-- ============================================================

-- Показать текущее состояние
SELECT 
    COUNT(*) as objects_total,
    COUNT(CASE WHEN shift_tasks IS NOT NULL AND shift_tasks::text != '[]' AND shift_tasks::text != 'null' THEN 1 END) as objects_with_tasks
FROM objects;

-- Очистить поле shift_tasks у всех объектов
UPDATE objects 
SET shift_tasks = '[]'::jsonb
WHERE shift_tasks IS NOT NULL 
  AND shift_tasks::text != '[]' 
  AND shift_tasks::text != 'null';

-- Показать результат
SELECT 
    COUNT(*) as objects_total,
    COUNT(CASE WHEN shift_tasks IS NOT NULL AND shift_tasks::text != '[]' AND shift_tasks::text != 'null' THEN 1 END) as objects_with_tasks_after
FROM objects;


-- ============================================================
-- ЧАСТЬ 2: Очистка Tasks v2 (только если таблицы существуют - для dev)
-- ============================================================

-- Проверяем существование таблиц Tasks v2
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'task_entries_v2') THEN
        -- Показать состояние
        RAISE NOTICE 'Tasks v2 tables found - cleaning...';
        
        -- Открепить корректировки от задач
        UPDATE payroll_adjustments 
        SET task_entry_v2_id = NULL 
        WHERE task_entry_v2_id IS NOT NULL;
        
        -- Удалить данные Tasks v2 (в порядке зависимостей)
        DELETE FROM task_entries_v2;
        DELETE FROM task_plans_v2;
        DELETE FROM task_templates_v2;
        
        RAISE NOTICE 'Tasks v2 data cleared';
    ELSE
        RAISE NOTICE 'Tasks v2 tables not found - skipping';
    END IF;
END $$;


-- ============================================================
-- Финальная проверка
-- ============================================================

-- Показать итог по старым задачам
SELECT 'Objects.shift_tasks очищено' as status, 
       COUNT(*) as objects_cleared 
FROM objects 
WHERE shift_tasks = '[]'::jsonb OR shift_tasks IS NULL;

COMMIT;

-- ============================================================
-- ВАЖНО: После миграции
-- ============================================================
-- 1. Очистить кэш Redis:
--    docker compose -f docker-compose.dev.yml exec redis redis-cli FLUSHALL
--
-- 2. Перезапустить веб-контейнер:
--    docker compose -f docker-compose.dev.yml restart web

