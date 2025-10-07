# Сущность: Лимиты и тарифы (Limits & Tariffs)

## Веб-роуты и API
- [GET] `/` — (apps/web/routes/limits.py) — роль: owner
- [GET] `/` — (apps/web/routes/tariffs.py) — роль: owner
- [GET] `/` — (apps/web/routes/user_subscriptions.py) — роль: owner
- [GET] `/` — (apps/web/routes/billing.py) — роль: owner
- [GET] `/admin/api/overview` — (apps/web/routes/limits.py) — роль: superadmin
- [GET] `/admin/overview` — (apps/web/routes/limits.py) — роль: superadmin
- [GET] `/api/check/employee` — (apps/web/routes/limits.py)
- [GET] `/api/check/feature/{feature}` — (apps/web/routes/limits.py)
- [GET] `/api/check/manager` — (apps/web/routes/limits.py)
- [GET] `/api/check/object` — (apps/web/routes/limits.py)
- [GET] `/api/list` — (apps/web/routes/tariffs.py)
- [GET] `/api/list` — (apps/web/routes/user_subscriptions.py)
- [GET] `/api/notifications` — (apps/web/routes/billing.py)
- [GET] `/api/statistics` — (apps/web/routes/tariffs.py)
- [GET] `/api/summary` — (apps/web/routes/limits.py)
- [GET] `/api/transactions` — (apps/web/routes/billing.py)
- [GET] `/api/usage/{user_id}` — (apps/web/routes/billing.py)
- [GET] `/api/user/{user_id}` — (apps/web/routes/user_subscriptions.py)
- [GET] `/api/{tariff_id}` — (apps/web/routes/tariffs.py)
- [GET] `/assign` — (apps/web/routes/user_subscriptions.py)
- [POST] `/assign` — (apps/web/routes/user_subscriptions.py)
- [POST] `/auto-renewal/{user_id}` — (apps/web/routes/billing.py)
- [GET] `/create` — (apps/web/routes/tariffs.py)
- [POST] `/create` — (apps/web/routes/tariffs.py)
- [GET] `/transactions` — (apps/web/routes/billing.py)
- [POST] `/transactions/{transaction_id}/status` — (apps/web/routes/billing.py)
- [GET] `/usage` — (apps/web/routes/billing.py)
- [POST] `/{subscription_id}/cancel` — (apps/web/routes/user_subscriptions.py)
- [POST] `/{tariff_id}/delete` — (apps/web/routes/tariffs.py)
- [GET] `/{tariff_id}/edit` — (apps/web/routes/tariffs.py)
- [POST] `/{tariff_id}/edit` — (apps/web/routes/tariffs.py)

## Шаблоны/JS/CSS
- `admin/assign_subscription.html`
- `admin/billing_dashboard.html`
- `admin/billing_transactions.html`
- `admin/limits_overview.html`
- `admin/tariff_form.html`
- `admin/tariffs.html`
- `admin/usage_metrics.html`
- `admin/user_subscriptions.html`
- `owner/limits_dashboard.html`
