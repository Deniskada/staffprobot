# System Features

## Инициализация фич при первом входе владельца
- При первом успешном входе, если у пользователя нет активной подписки, назначается активный тариф с `is_popular=true` (самый дешёвый среди активных).
- Список включённых фич берётся из `tariff_plans.features` выбранного тарифа и записывается в `OwnerProfile.enabled_features` (идемпотентно).
- Кэш Redis `enabled_features:{telegram_id}` инвалидируется при изменениях через `SystemFeaturesService` (для ручных переключений в профиле).

## Зависимости
- `domain.entities.tariff_plan.TariffPlan.features` — список ключей фич тарифа
- `domain.entities.owner_profile.OwnerProfile.enabled_features` — включённые фичи пользователя
- `shared.services.system_features_service.SystemFeaturesService` — вычисление доступности, переключение фич, инвалидация кэша


