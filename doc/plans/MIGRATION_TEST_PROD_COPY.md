# Тестирование миграций на копии prod БД

**Дата:** 2025-10-12  
**Миграции для теста:** 96bcb588d0c8, 3bcf125fefbd  
**Время выполнения:** ~15 минут

---

## 🎯 Цель

Убедиться, что миграции корректно применяются на реальных prod данных без ошибок.

---

## 📋 Чеклист

### Шаг 1: Создать бэкап prod БД (5 мин)

```bash
# 1. Подключиться к prod
ssh staffprobot@staffprobot.ru

# 2. Создать бэкап
cd /opt/staffprobot
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres -d staffprobot_prod > /tmp/staffprobot_prod_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Скопировать бэкап на локальную машину
exit
scp staffprobot@staffprobot.ru:/tmp/staffprobot_prod_backup_*.sql ~/
```

**Результат:** ✅ Файл `staffprobot_prod_backup_YYYYMMDD_HHMMSS.sql` скачан

---

### Шаг 2: Развернуть копию prod на dev (5 мин)

```bash
# 1. Остановить dev БД (опционально - создать отдельную БД test_prod)
cd /home/sa/projects/staffprobot

# 2. Создать тестовую БД
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "CREATE DATABASE staffprobot_test_prod;"

# 3. Восстановить бэкап
docker compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d staffprobot_test_prod < ~/staffprobot_prod_backup_*.sql

# 4. Проверить восстановление
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "
SELECT 
  (SELECT COUNT(*) FROM users) as users,
  (SELECT COUNT(*) FROM objects) as objects,
  (SELECT COUNT(*) FROM shifts) as shifts,
  (SELECT COUNT(*) FROM contracts) as contracts;
"
```

**Ожидается:** Данные совпадают с prod (users, objects, shifts, contracts)

---

### Шаг 3: Применить миграции на копии (2 мин)

```bash
# 1. Проверить текущую версию миграции
docker compose -f docker-compose.dev.yml exec web alembic -c alembic.ini -x db_name=staffprobot_test_prod current

# 2. Применить недостающие миграции
docker compose -f docker-compose.dev.yml exec web alembic -c alembic.ini -x db_name=staffprobot_test_prod upgrade head

# 3. Проверить финальную версию
docker compose -f docker-compose.dev.yml exec web alembic -c alembic.ini -x db_name=staffprobot_test_prod current
```

**Ожидается:** 
- ✅ Миграции применились без ошибок
- ✅ Текущая версия: `3bcf125fefbd (head)`

---

### Шаг 4: Валидация структуры БД (2 мин)

```bash
# 1. Проверить новую таблицу object_openings
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "\d object_openings"

# Ожидается:
# ✅ Таблица существует
# ✅ Поля: id, object_id, opened_by (Integer), opened_at, closed_by (Integer), closed_at, coordinates
# ✅ 5 индексов
# ✅ 3 FK

# 2. Проверить новые поля в time_slots
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "
SELECT 
  column_name, 
  data_type, 
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_name = 'time_slots' 
  AND column_name IN ('penalize_late_start', 'ignore_object_tasks', 'shift_tasks')
ORDER BY column_name;
"

# Ожидается:
# ✅ penalize_late_start | boolean | NO | true
# ✅ ignore_object_tasks | boolean | NO | false
# ✅ shift_tasks | jsonb | YES | NULL

# 3. Проверить новые поля в shifts
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "
SELECT 
  column_name, 
  data_type, 
  is_nullable
FROM information_schema.columns
WHERE table_name = 'shifts' 
  AND column_name IN ('planned_start', 'actual_start')
ORDER BY column_name;
"

# Ожидается:
# ✅ actual_start | timestamp with time zone | YES
# ✅ planned_start | timestamp with time zone | YES
```

**Критерии успеха:**
- ✅ Все таблицы созданы
- ✅ Все поля добавлены с правильными типами
- ✅ Индексы созданы
- ✅ FK ограничения работают

---

### Шаг 5: Проверка существующих данных (1 мин)

```bash
# 1. Проверить что старые смены не поломаны
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "
SELECT 
  id, 
  user_id, 
  object_id, 
  status,
  planned_start,  -- Должно быть NULL для старых смен
  actual_start    -- Должно быть NULL для старых смен
FROM shifts
ORDER BY id DESC
LIMIT 5;
"

# 2. Проверить что старые time_slots не поломаны
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "
SELECT 
  id,
  object_id,
  slot_date,
  penalize_late_start,  -- Должно быть TRUE (default)
  ignore_object_tasks,  -- Должно быть FALSE (default)
  shift_tasks           -- Должно быть NULL для старых
FROM time_slots
ORDER BY id DESC
LIMIT 5;
"
```

**Ожидается:**
- ✅ Старые записи имеют дефолтные значения
- ✅ NULL для nullable полей
- ✅ Нет ошибок FK

---

### Шаг 6: Тест downgrade (опционально, 2 мин)

```bash
# 1. Откатить миграции
docker compose -f docker-compose.dev.yml exec web alembic -c alembic.ini -x db_name=staffprobot_test_prod downgrade -2

# 2. Проверить что таблица удалена
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "\d object_openings"
# Ожидается: "relation does not exist"

# 3. Проверить что поля удалены
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_test_prod -c "\d+ time_slots" | grep -E "penalize|ignore|shift_tasks"
# Ожидается: пусто

# 4. Накатить обратно
docker compose -f docker-compose.dev.yml exec web alembic -c alembic.ini -x db_name=staffprobot_test_prod upgrade head
```

**Результат:** ✅ Downgrade работает корректно

---

### Шаг 7: Очистка (1 мин)

```bash
# 1. Удалить тестовую БД
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "DROP DATABASE staffprobot_test_prod;"

# 2. Удалить локальный бэкап (опционально)
rm ~/staffprobot_prod_backup_*.sql

# 3. На проде - удалить /tmp бэкап
ssh staffprobot@staffprobot.ru 'rm /tmp/staffprobot_prod_backup_*.sql'
```

---

## ✅ Критерии успешности

Миграции готовы к prod, если:

- [x] Бэкап создан ✅
- [ ] Миграции применились без ошибок
- [ ] Все таблицы и поля созданы
- [ ] Индексы и FK работают
- [ ] Существующие данные не повреждены
- [ ] Downgrade работает (опционально)
- [ ] Тестовая БД удалена

---

## 🚨 Что делать при ошибках

**Если миграция не применяется:**
1. Скопировать текст ошибки
2. Проверить конфликты с существующими таблицами/полями
3. Исправить миграцию локально
4. Повторить тест

**Если есть ошибки FK:**
1. Проверить что referenced таблицы существуют
2. Проверить типы полей (Integer vs BigInteger)
3. Проверить ondelete политики

**Если данные повреждены:**
1. НЕ деплоить на prod!
2. Проанализировать причину
3. Исправить миграцию
4. Повторить весь тест с нуля

---

## 📊 Ожидаемое время выполнения миграций на prod

**Таблица object_openings:** ~0.1 сек (новая таблица, 0 данных)  
**time_slots добавление полей:** ~0.5 сек (~200 записей)  
**shifts добавление полей:** ~2-3 сек (~1000+ записей)  
**Создание индексов:** ~1-2 сек

**Общее время:** ~5-10 секунд

**Downtime:** Не требуется (миграции не блокируют таблицы надолго)

---

## ✅ Финальный чеклист

- [ ] Бэкап prod создан
- [ ] Копия БД развернута на dev
- [ ] Миграции применены на копии
- [ ] Структура проверена
- [ ] Существующие данные проверены
- [ ] Тестовая БД очищена
- [ ] Команды деплоя подготовлены

**Статус:** ⏳ ГОТОВО К ТЕСТИРОВАНИЮ

