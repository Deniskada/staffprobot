# 🚀 Инструкция по деплою Iteration 25 на PRODUCTION

## ⚠️ ВАЖНО: Особенности продакшена

**На проде совершенно другое наполнение базы данных!**

- ✅ На дев окружении: тестовые данные, можно безопасно экспериментировать
- ⚠️ На проде: реальные пользователи, уведомления, транзакции

## 📋 Предварительная проверка

### 1. Проверка текущего состояния БД на проде

```bash
# Подключаемся к проду
ssh staffprobot@staffprobot.ru

# Проверяем текущие значения ENUM notificationstatus
cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT unnest(enum_range(NULL::notificationstatus));"
```

**Ожидаемый вывод (до миграции):**
```
 unnest    
-----------
 pending
 sent
 delivered
 failed
 read
 cancelled
```

### 2. Создание бэкапа БД (ОБЯЗАТЕЛЬНО!)

```bash
# На проде
cd /opt/staffprobot

# Создаём бэкап с timestamp
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres -d staffprobot_prod > /tmp/staffprobot_prod_backup_before_iter25_$(date +%Y%m%d_%H%M%S).sql

# Копируем бэкап в безопасное место
cp /tmp/staffprobot_prod_backup_*.sql ~/backups/
```

## 🔧 Миграции БД

### Миграция 1: notification_templates (3a9c09063654)

**Что делает:**
- Создаёт новую таблицу `notification_templates`
- Добавляет индексы для быстрого поиска
- Использует существующие ENUM типы `notificationtype` и `notificationchannel`

**Безопасность:** ✅ Полностью безопасна, не затрагивает существующие данные

**Применение:**
```bash
# На проде
cd /opt/staffprobot

# Применяем миграцию
docker compose -f docker-compose.prod.yml exec web alembic upgrade 3a9c09063654

# Проверяем успешность
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "\d notification_templates"
```

### Миграция 2: ENUM статусы (cdbb28b02851)

**Что делает:**
- Добавляет значения `scheduled` и `deleted` в ENUM `notificationstatus`
- Использует `IF NOT EXISTS` для безопасности

**Безопасность:** ✅ Безопасна, но требует проверки

**⚠️ ВАЖНО:** В PostgreSQL нельзя удалить значения из ENUM после добавления!

**Применение:**
```bash
# На проде
cd /opt/staffprobot

# Применяем миграцию
docker compose -f docker-compose.prod.yml exec web alembic upgrade cdbb28b02851

# Проверяем новые значения
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT unnest(enum_range(NULL::notificationstatus));"
```

**Ожидаемый вывод (после миграции):**
```
 unnest    
-----------
 pending
 sent
 delivered
 failed
 read
 cancelled
 scheduled   <-- НОВОЕ
 deleted     <-- НОВОЕ
```

## 📦 Деплой кода

### 1. Обновление кода

```bash
# На проде
ssh staffprobot@staffprobot.ru

cd /opt/staffprobot

# Получаем последние изменения из ветки develop
git fetch origin
git checkout develop
git pull origin develop
```

### 2. Проверка изменений

```bash
# Смотрим, что изменилось
git log --oneline -20

# Проверяем статус
git status
```

### 3. Перезапуск контейнеров

```bash
# Останавливаем контейнеры
docker compose -f docker-compose.prod.yml down

# Пересобираем образы (если были изменения в requirements.txt)
docker compose -f docker-compose.prod.yml build web

# Запускаем контейнеры
docker compose -f docker-compose.prod.yml up -d

# Проверяем статус
docker compose -f docker-compose.prod.yml ps
```

### 4. Проверка логов

```bash
# Смотрим логи веб-приложения
docker compose -f docker-compose.prod.yml logs web -f

# Проверяем на ошибки
docker compose -f docker-compose.prod.yml logs web | grep -i error
```

## ✅ Проверка функционала

### 1. Доступность админ-панели

```bash
# Проверяем, что сервер отвечает
curl -I https://staffprobot.ru/admin/notifications

# Ожидаемый ответ: HTTP 401 (Unauthorized) или HTTP 200 (если залогинены)
```

### 2. Проверка через браузер

1. Открываем https://staffprobot.ru/admin
2. Логинимся под суперадмином
3. Проверяем пункт меню "🔔 Уведомления"
4. Открываем страницу: https://staffprobot.ru/admin/notifications
5. Проверяем дашборд - графики должны загрузиться
6. Проверяем список уведомлений
7. Проверяем шаблоны

### 3. Проверка данных

```bash
# На проде - проверяем количество уведомлений
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT status, COUNT(*) FROM notifications GROUP BY status;"

# Проверяем, что новые статусы не используются (пока)
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT COUNT(*) FROM notifications WHERE status IN ('scheduled', 'deleted');"

# Ожидаемый результат: 0
```

## 🔄 Откат (если что-то пошло не так)

### Быстрый откат кода

```bash
# На проде
cd /opt/staffprobot

# Возвращаемся на main ветку
git checkout main
git pull origin main

# Перезапускаем
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Откат миграций

```bash
# ⚠️ ВНИМАНИЕ: Откат миграции cdbb28b02851 невозможен!
# PostgreSQL не позволяет удалять значения из ENUM

# Откатываем только миграцию notification_templates (если нужно)
docker compose -f docker-compose.prod.yml exec web alembic downgrade 3a9c09063654

# Это удалит таблицу notification_templates
```

### Полный откат из бэкапа

```bash
# ⚠️ ТОЛЬКО В КРИТИЧЕСКОЙ СИТУАЦИИ!

# На проде
cd /opt/staffprobot

# Останавливаем приложение
docker compose -f docker-compose.prod.yml down

# Восстанавливаем из бэкапа
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod < ~/backups/staffprobot_prod_backup_*.sql

# Запускаем
docker compose -f docker-compose.prod.yml up -d
```

## 📊 Мониторинг после деплоя

### 1. Первые 10 минут

- ✅ Проверить логи на ошибки
- ✅ Проверить доступность сайта
- ✅ Проверить admin панель
- ✅ Открыть дашборд уведомлений

### 2. Первый час

- ✅ Проверить метрики производительности
- ✅ Проверить, что пользователи получают уведомления
- ✅ Проверить отсутствие утечек памяти
- ✅ Проверить connection pool БД

### 3. Первый день

- ✅ Собрать обратную связь от пользователей
- ✅ Проверить логи на предупреждения
- ✅ Проверить использование новых функций
- ✅ Мониторить производительность БД

## ⚠️ Особые случаи

### Если на проде уже есть уведомления со статусом 'scheduled' или 'deleted'

```bash
# Проверяем наличие
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT status, COUNT(*) FROM notifications WHERE status NOT IN ('pending', 'sent', 'delivered', 'failed', 'read', 'cancelled') GROUP BY status;"

# Если есть - НЕ применяем миграцию cdbb28b02851
# Или применяем с особой осторожностью
```

### Если на проде много уведомлений (> 1M)

```bash
# Проверяем количество
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT COUNT(*) FROM notifications;"

# Если больше 1 миллиона:
# 1. Применяем миграции в нерабочее время
# 2. Мониторим нагрузку на БД
# 3. Проверяем индексы после миграции
```

## 📝 Чеклист деплоя

- [ ] Создан бэкап БД
- [ ] Бэкап скопирован в безопасное место
- [ ] Код обновлён из develop ветки
- [ ] Миграция 3a9c09063654 применена
- [ ] Миграция cdbb28b02851 применена
- [ ] Контейнеры перезапущены
- [ ] Логи проверены на ошибки
- [ ] Админ-панель доступна
- [ ] Дашборд уведомлений работает
- [ ] Список уведомлений отображается
- [ ] Шаблоны доступны
- [ ] Массовые операции работают
- [ ] Пользователи получают уведомления
- [ ] Нет утечек соединений к БД

## 🆘 Контакты для экстренных случаев

- **Основной разработчик:** AI Assistant (Claude Sonnet 4.5)
- **Документация:** `doc/plans/iteration25/`
- **Логи:** `/opt/staffprobot/logs/` (если настроены)
- **Мониторинг:** проверить через `docker compose -f docker-compose.prod.yml logs`

---

**Дата создания:** 14 октября 2025  
**Версия:** 1.0  
**Статус:** Готов к применению

