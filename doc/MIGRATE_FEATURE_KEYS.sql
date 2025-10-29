-- Миграция данных: обновление ключей фич
-- Дата: 29.10.2025
-- Причина: Переименование фич в ветке feature/rules-tasks-incidents
--
-- Маппинг:
--   bonuses_and_penalties → rules_engine
--   shift_tasks → tasks_v2
--
-- ВАЖНО: Обновляет 2 таблицы:
--   1. system_features (каталог фич)
--   2. owner_profiles.enabled_features (включенные фичи у владельцев)
--
-- Применение на проде:
--   ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d staffprobot_prod < doc/MIGRATE_FEATURE_KEYS.sql'

BEGIN;

-- ============================================================
-- ЧАСТЬ 1: Обновление таблицы system_features (каталог фич)
-- ============================================================

-- Показать текущее состояние
SELECT key, name FROM system_features WHERE key IN ('bonuses_and_penalties', 'shift_tasks');

-- Обновить ключи в таблице system_features
UPDATE system_features 
SET key = 'rules_engine'
WHERE key = 'bonuses_and_penalties';

UPDATE system_features 
SET key = 'tasks_v2'
WHERE key = 'shift_tasks';

-- Показать обновлённое состояние
SELECT key, name FROM system_features WHERE key IN ('rules_engine', 'tasks_v2');


-- ============================================================
-- ЧАСТЬ 2: Обновление owner_profiles.enabled_features
-- ============================================================

-- Показать текущее состояние
SELECT 
    user_id, 
    enabled_features,
    CASE 
        WHEN enabled_features::text LIKE '%bonuses_and_penalties%' THEN 'needs_update_bonuses'
        WHEN enabled_features::text LIKE '%shift_tasks%' THEN 'needs_update_tasks'
        ELSE 'ok'
    END as status
FROM owner_profiles 
WHERE enabled_features::text LIKE '%bonuses_and_penalties%' 
   OR enabled_features::text LIKE '%shift_tasks%';

-- Преобразовать старые ключи в новые (сначала преобразуем все)
UPDATE owner_profiles 
SET enabled_features = (
    SELECT jsonb_agg(
        CASE 
            WHEN elem::text = '"bonuses_and_penalties"' THEN '"rules_engine"'::jsonb
            WHEN elem::text = '"shift_tasks"' THEN '"tasks_v2"'::jsonb
            ELSE elem
        END
    )
    FROM jsonb_array_elements(enabled_features::jsonb) elem
)::json
WHERE enabled_features::text LIKE '%bonuses_and_penalties%' 
   OR enabled_features::text LIKE '%shift_tasks%';

-- Удалить дубликаты (старые ключи, если остались после преобразования)
UPDATE owner_profiles 
SET enabled_features = (
    SELECT jsonb_agg(elem)
    FROM jsonb_array_elements(enabled_features::jsonb) elem
    WHERE elem::text NOT IN ('"bonuses_and_penalties"', '"shift_tasks"')
)::json
WHERE enabled_features::text LIKE '%bonuses_and_penalties%' 
   OR enabled_features::text LIKE '%shift_tasks%';

-- Показать финальное состояние
SELECT user_id, enabled_features FROM owner_profiles ORDER BY user_id;

COMMIT;

-- ============================================================
-- ФИНАЛ: Очистка кэша Redis
-- ============================================================

-- Очистить кэш enabled_features после миграции
-- Выполнить отдельно:
-- docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL

