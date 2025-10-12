# Rollback Plan - Phase 4B/4C (Object State + TimeSlot Fields)

**Дата создания:** 2025-10-12  
**Ветка:** feature/employee-payment-accounting  
**Миграции:** 96bcb588d0c8, 3bcf125fefbd  
**Критичность:** Средняя (новые фичи, не затрагивает старый функционал)

---

## 📊 Что было добавлено

### Новые таблицы:
- `object_openings` - отслеживание открыт/закрыт

### Новые поля:
**TimeSlot:**
- `penalize_late_start` (Boolean)
- `ignore_object_tasks` (Boolean)
- `shift_tasks` (JSONB)

**Shift:**
- `planned_start` (DateTime TZ)
- `actual_start` (DateTime TZ)

**Object:**
- `telegram_report_chat_id` (BigInteger)
- `inherit_telegram_chat` (Boolean)

**OrgStructureUnit:**
- `telegram_report_chat_id` (BigInteger)

---

## 🚨 Когда нужен rollback

1. ❌ Миграция не применяется на prod
2. ❌ Критичные ошибки в логах после деплоя
3. ❌ Смены не закрываются
4. ❌ Celery падает с ошибками
5. ❌ Пользователи не могут открывать смены

---

## 🔄 Процедура rollback

### Вариант 1: Откат миграций (безопасный, но долгий)

```bash
# 1. Подключиться к prod
ssh staffprobot@staffprobot.ru

# 2. Перейти в директорию проекта
cd /opt/staffprobot

# 3. Откатить миграции
docker compose -f docker-compose.prod.yml exec web alembic downgrade -1  # откат 3bcf125fefbd
docker compose -f docker-compose.prod.yml exec web alembic downgrade -1  # откат 96bcb588d0c8

# 4. Откатить код
git checkout main
git pull origin main

# 5. Перезапустить сервисы
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 6. Проверить логи
docker compose -f docker-compose.prod.yml logs web --tail 100
docker compose -f docker-compose.prod.yml logs celery_worker --tail 100
docker compose -f docker-compose.prod.yml logs bot --tail 100
```

**Время:** ~10 минут  
**Риск:** Низкий (миграции поддерживают downgrade)

---

### Вариант 2: Откат кода БЕЗ отката миграций (быстрый)

```bash
# 1. Откатить код
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git checkout main && git pull origin main'

# 2. Перезапустить сервисы
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d'

# 3. Проверить
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml ps'
```

**Время:** ~3 минуты  
**Риск:** Средний (новые поля останутся пустыми, но не критично)

**Почему безопасно:**
- ✅ Новые поля nullable
- ✅ Старый код не использует новые поля
- ✅ object_openings не используется старым кодом
- ✅ Можно докатить миграции позже

---

### Вариант 3: Исправление вперед (hot-fix)

Если проблема локальная:

```bash
# 1. Исправить код локально
# 2. Коммит
git commit -m "Hotfix: ..."

# 3. Деплой исправления
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git pull origin feature/employee-payment-accounting'
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml restart web bot celery_worker'
```

**Время:** ~5 минут  
**Риск:** Низкий (если проблема понятна)

---

## 🧪 Тест rollback'а на dev

Можно протестировать откат прямо сейчас на dev:

```bash
# 1. Сохранить текущие данные
docker compose -f docker-compose.dev.yml exec postgres pg_dump -U postgres staffprobot_dev > backup_before_rollback.sql

# 2. Откатить миграции
docker compose -f docker-compose.dev.yml exec web alembic downgrade -2

# 3. Проверить что всё работает
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "\d object_openings"
# Должно быть: "relation does not exist"

# 4. Накатить обратно
docker compose -f docker-compose.dev.yml exec web alembic upgrade head

# 5. Восстановить данные если нужно
docker compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d staffprobot_dev < backup_before_rollback.sql
```

---

## 📝 Чеклист после rollback

- [ ] Все сервисы запущены (docker ps)
- [ ] Web отвечает (curl http://localhost:8001/health)
- [ ] Бот отвечает на /start
- [ ] Пользователи могут открывать/закрывать смены
- [ ] Dashboard'ы загружаются
- [ ] Нет ошибок в логах

---

## 📞 Контакты на случай проблем

**Команды для быстрой диагностики:**
```bash
# Статус сервисов
docker compose -f docker-compose.prod.yml ps

# Логи за последние 100 строк
docker compose -f docker-compose.prod.yml logs web --tail 100
docker compose -f docker-compose.prod.yml logs bot --tail 100
docker compose -f docker-compose.prod.yml logs celery_worker --tail 100

# Проверка БД
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT version();"
docker compose -f docker-compose.prod.yml exec web alembic current
```

---

## 🎯 Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Миграция не применяется | Низкая | Высокое | Протестировать на копии prod перед деплоем |
| Конфликт типов Integer/BigInteger | Очень низкая | Среднее | Проверено: используется user.id (Integer) ✅ |
| Greenlet ошибки в Celery | Очень низкая | Среднее | Все исправлены на dev ✅ |
| Проблемы с timezone | Очень низкая | Низкое | Протестировано на dev ✅ |
| Ошибки в UI manager/owner | Низкая | Низкое | Smoke тесты пройдены ✅ |

---

## 💡 Рекомендации

1. **Деплой в нерабочее время** (ночь/выходные)
2. **Мониторинг первые 2-4 часа** после деплоя
3. **Бэкап БД перед деплоем** обязателен
4. **Rollback-команды наготове** (скопировать в отдельный файл)

---

## ✅ Готовность к деплоу

**Текущий статус:** ГОТОВО с оговорками

**Что сделано:**
- ✅ 6 критичных багов исправлены
- ✅ 50+ smoke тестов пройдены
- ✅ Unit-тесты проходят (15/15)
- ✅ Синтаксис корректен
- ✅ Все сервисы работают стабильно
- ✅ Нет зависших смен/объектов
- ✅ Celery обрабатывает без ошибок

**Что рекомендуется:**
- ⏳ Протестировать миграции на копии prod БД
- ⏳ Создать бэкап prod перед деплоем
- ⏳ Согласовать время деплоя

