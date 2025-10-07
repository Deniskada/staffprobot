# Роль: Модератор (Moderator)

## Роуты и эндпоинты
- [GET] `/moderator/`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/`  — (apps/web/routes/moderator_web.py)
- [GET] `/moderator/appeals`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/appeals`  — (apps/web/routes/moderator_web.py)
- [GET] `/moderator/appeals/overdue`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/appeals/statistics`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/appeals/{appeal_id}`  — (apps/web/routes/moderator.py)
- [POST] `/moderator/appeals/{appeal_id}/review`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/dashboard`  — (apps/web/routes/moderator_web.py)
- [GET] `/moderator/overdue`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/reviews`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/reviews`  — (apps/web/routes/moderator_web.py)
- [POST] `/moderator/reviews/bulk-moderate`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/reviews/{review_id}`  — (apps/web/routes/moderator.py)
- [POST] `/moderator/reviews/{review_id}/auto-moderate`  — (apps/web/routes/moderator.py)
- [POST] `/moderator/reviews/{review_id}/moderate`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/statistics`  — (apps/web/routes/moderator.py)
- [GET] `/moderator/statistics`  — (apps/web/routes/moderator_web.py)

## Шаблоны (Jinja2)
- `moderator/appeals.html`
- `moderator/dashboard.html`
- `moderator/reviews.html`
- `moderator/statistics.html`
