# Сущность: Отзывы (Reviews)

## Веб-роуты и API
- [GET] `/` — (apps/web/routes/moderator.py) — роль: owner
- [GET] `/` — (apps/web/routes/moderator_web.py) — роль: owner
- [GET] `/appeals` — (apps/web/routes/moderator.py)
- [GET] `/appeals` — (apps/web/routes/moderator_web.py)
- [GET] `/appeals/overdue` — (apps/web/routes/moderator.py)
- [GET] `/appeals/statistics` — (apps/web/routes/moderator.py)
- [GET] `/appeals/{appeal_id}` — (apps/web/routes/moderator.py)
- [POST] `/appeals/{appeal_id}/review` — (apps/web/routes/moderator.py)
- [POST] `/create` — (apps/web/routes/shared_reviews.py)
- [GET] `/dashboard` — (apps/web/routes/moderator_web.py)
- [GET] `/my-reviews` — (apps/web/routes/shared_reviews.py)
- [GET] `/overdue` — (apps/web/routes/moderator.py)
- [GET] `/reviews` — (apps/web/routes/owner_reviews.py)
- [GET] `/reviews` — (apps/web/routes/manager_reviews.py)
- [GET] `/reviews` — (apps/web/routes/employee_reviews.py)
- [GET] `/reviews` — (apps/web/routes/moderator.py)
- [GET] `/reviews` — (apps/web/routes/moderator_web.py)
- [POST] `/reviews/bulk-moderate` — (apps/web/routes/moderator.py)
- [GET] `/reviews/{review_id}` — (apps/web/routes/moderator.py)
- [POST] `/reviews/{review_id}/auto-moderate` — (apps/web/routes/moderator.py)
- [POST] `/reviews/{review_id}/moderate` — (apps/web/routes/moderator.py)
- [GET] `/statistics` — (apps/web/routes/moderator.py)
- [GET] `/statistics` — (apps/web/routes/moderator_web.py)
- [GET] `/targets/{target_type}` — (apps/web/routes/shared_reviews.py)
- [GET] `/{review_id}` — (apps/web/routes/shared_reviews.py)

## Шаблоны/JS/CSS
- `employee/reviews.html`
- `manager/reviews.html`
- `moderator/appeals.html`
- `moderator/dashboard.html`
- `moderator/reviews.html`
- `moderator/statistics.html`
- `owner/reviews.html`
