# Shared: Медиа, Рейтинги, Обжалования, Уведомления, System Settings

## Медиа
- [POST] `/upload`
- [DELETE] `/{media_id}`
- [GET] `/review/{review_id}`
- [POST] `/validate`
- [GET] `/limits`

## Рейтинги
- [GET] `/top/{target_type}`
- [GET] `/{target_type}/{target_id}`
- [POST] `/{target_type}/{target_id}/recalculate`
- [POST] `/batch`
- [GET] `/statistics/{target_type}/{target_id}`
- [POST] `/admin/recalculate-all`

## Обжалования
- [POST] `/create`
- [GET] `/check/{review_id}`
- [GET] `/my-appeals`
- [GET] `/details/{appeal_id}`
- [GET] `/statistics`
- [GET] `/pending`
- [POST] `/{appeal_id}/review`

## Отзывы
- [POST] `/create`
- [GET] `/my-reviews`
- [GET] `/targets/{target_type}`
- [GET] `/{review_id}`

## System Settings API
- [GET] `/domain`
- [POST] `/domain`
- [GET] `/domain/validate`
- [GET] `/domain/preview`
- [GET] `/nginx/preview`
- [POST] `/nginx/generate`
- [POST] `/nginx/validate`
- [POST] `/nginx/apply`
- [GET] `/nginx/status`
- [DELETE] `/nginx/remove`
- [GET] `/nginx/backups`
- [POST] `/nginx/backups/create`
- [POST] `/nginx/backups/restore`
- [DELETE] `/nginx/backups/delete`
- [POST] `/ssl/setup`
- [POST] `/clear-cache`
- [POST] `/initialize`
- [GET] `/history`
- [GET] `/ssl/monitoring/status`
- [GET] `/ssl/monitoring/health`
- [GET] `/ssl/monitoring/alerts`
- [GET] `/ssl/monitoring/recommendations`
- [POST] `/ssl/monitoring/renew`
- [GET] `/ssl/monitoring/statistics`
- [GET] `/ssl/logs`
- [GET] `/ssl/logs/statistics`
- [GET] `/ssl/logs/errors`
- [POST] `/ssl/logs/cleanup`
- [GET] `/ssl/logs/export`
- [GET] `/ssl/email`
- [POST] `/ssl/email`
- [GET] `/https`
- [POST] `/https`
- [GET] `/all`
- [POST] `/initialize`
- [POST] `/cache/clear`
