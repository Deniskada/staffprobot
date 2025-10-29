-- Миграция данных: обновление ключей фич в owner_profiles
-- Дата: 29.10.2025
-- Причина: Переименование фич в ветке feature/rules-tasks-incidents
--
-- Маппинг:
--   bonuses_and_penalties → rules_engine
--   shift_tasks → tasks_v2
--
-- Применение на проде:
--   ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod < migrations/data/migrate_feature_keys.sql'

BEGIN;

-- Показать текущее состояние (для логирования)
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

-- Обновить ключи фич
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

-- Показать обновлённое состояние (для проверки)
SELECT 
    user_id, 
    enabled_features,
    CASE 
        WHEN enabled_features::text LIKE '%rules_engine%' THEN 'updated_to_rules_engine'
        WHEN enabled_features::text LIKE '%tasks_v2%' THEN 'updated_to_tasks_v2'
        ELSE 'ok'
    END as status
FROM owner_profiles 
WHERE enabled_features::text LIKE '%rules_engine%' 
   OR enabled_features::text LIKE '%tasks_v2%';

COMMIT;

-- Очистить кэш Redis для enabled_features после миграции
-- Выполнить отдельно:
-- docker compose -f docker-compose.prod.yml exec redis redis-cli KEYS "enabled_features:*" | xargs docker compose -f docker-compose.prod.yml exec redis redis-cli DEL

