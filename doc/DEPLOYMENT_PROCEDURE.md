# 🚀 Процедура развертывания StaffProBot на production сервер

## 📋 Обзор процесса
Развертывание происходит через сборку Docker образов на локальной машине, их передачу на сервер и запуск там. Это обеспечивает полную изоляцию production и dev окружений.

## 🧹 Очистка production перед развертыванием

### Этап 0: Подготовка production сервера

#### 0.1 Остановка текущего production
```bash
# Подключаемся к серверу
ssh user@yourdomain.com

# Переходим в рабочую директорию
cd /opt

# Останавливаем текущее production окружение
docker compose -f docker-compose.prod.yml down

# Удаляем остановленные контейнеры
docker container prune -f

# Удаляем неиспользуемые образы (ОСТОРОЖНО!)
docker image prune -a -f

# Удаляем неиспользуемые volumes (ОСТОРОЖНО!)
docker volume prune -f

# Удаляем неиспользуемые сети
docker network prune -f

# Проверяем освобожденное место
df -h
```

#### 0.2 Создание бэкапов production
```bash
# Создаем бэкап production базы данных
docker compose -f docker-compose.prod.yml up -d postgres
sleep 10
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres staffprobot_prod > prod_backup_$(date +%Y%m%d_%H%M%S).sql

# Создаем бэкап production конфигураций
tar -czf prod_config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env docker-compose.prod.yml

# Создаем бэкап загруженных файлов (если есть)
if [ -d "uploads/" ]; then
    tar -czf prod_uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/
fi

# Останавливаем postgres после бэкапа
docker compose -f docker-compose.prod.yml down

# Проверяем созданные бэкапы
ls -la prod_backup_*.sql prod_config_backup_*.tar.gz prod_uploads_backup_*.tar.gz
```

#### 0.3 Очистка Docker системы
```bash
# Показываем использование места Docker
docker system df

# Очищаем все неиспользуемые ресурсы (ОСТОРОЖНО!)
docker system prune -a --volumes -f

# Проверяем освобожденное место
df -h
```

## 👑 Создание суперадминистратора

### Создание суперадмина через миграцию
```bash
# На сервере - запускаем только postgres для создания суперадмина
docker compose -f docker-compose.prod.yml up -d postgres
sleep 10

# Создаем SQL скрипт для суперадмина
cat > create_superadmin.sql << 'EOF'
-- Создание суперадминистратора
INSERT INTO users (
    telegram_id, 
    first_name, 
    last_name, 
    username, 
    phone, 
    email, 
    role, 
    is_active, 
    created_at, 
    updated_at
) VALUES (
    123456789,  -- Замените на ваш Telegram ID
    'Super', 
    'Admin', 
    'superadmin', 
    '+1234567890', 
    'admin@yourdomain.com', 
    'superadmin', 
    true, 
    NOW(), 
    NOW()
) ON CONFLICT (telegram_id) DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    username = EXCLUDED.username,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Добавляем роль superadmin в user_roles
INSERT INTO user_roles (user_id, roles) 
SELECT id, '["superadmin"]'::jsonb 
FROM users 
WHERE telegram_id = 123456789
ON CONFLICT (user_id) DO UPDATE SET 
    roles = '["superadmin"]'::jsonb;

-- Показываем созданного суперадмина
SELECT id, telegram_id, first_name, last_name, username, role, is_active 
FROM users 
WHERE telegram_id = 123456789;
EOF

# Выполняем скрипт
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -f /tmp/create_superadmin.sql

# Останавливаем postgres
docker compose -f docker-compose.prod.yml down
```

### Создание суперадмина через API (альтернативный способ)
```bash
# После запуска полного production окружения
curl -X POST "http://localhost:8001/api/admin/create-superadmin" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "first_name": "Super",
    "last_name": "Admin",
    "username": "superadmin",
    "phone": "+1234567890",
    "email": "admin@yourdomain.com"
  }'
```

## 🔄 Полный цикл развертывания

### Этап 1: Подготовка локальной среды

#### 1.1 Создание бэкапов
```bash
# Переходим в корень проекта
cd /path/to/staffprobot

# Создаем бэкап dev базы данных
docker compose -f docker-compose.dev.yml exec postgres pg_dump -U postgres staffprobot_dev > dev_backup_$(date +%Y%m%d_%H%M%S).sql

# Создаем бэкап dev конфигураций
tar -czf dev_config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env docker-compose.dev.yml

# Проверяем созданные бэкапы
ls -la dev_backup_*.sql dev_config_backup_*.tar.gz
```

#### 1.2 Остановка dev окружения
```bash
# Останавливаем dev окружение
docker compose -f docker-compose.dev.yml down

# Проверяем, что контейнеры остановлены
docker ps -a | grep staffprobot
```

#### 1.3 Подготовка production конфигурации
```bash
# Создаем production .env файл (если его ещё нет)
cp env.example .env

# Редактируем .env для production настроек
# - Изменить DATABASE_URL на production
# - Изменить REDIS_URL на production
# - Настроить другие production переменные
```

### Этап 2: Сборка production образов

#### 2.1 Сборка Docker образов
```bash
# Собираем production образы
docker compose -f docker-compose.prod.yml build --no-cache

# Проверяем, что образы собрались
docker images | grep staffprobot
```

#### 2.2 Тестирование production локально
```bash
# Запускаем production локально
docker compose -f docker-compose.prod.yml up -d

# Проверяем логи всех сервисов
docker compose -f docker-compose.prod.yml logs web
docker compose -f docker-compose.prod.yml logs bot
docker compose -f docker-compose.prod.yml logs postgres
docker compose -f docker-compose.prod.yml logs redis

# Проверяем статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Тестируем основные функции
curl -s "http://localhost:8001/api/health" | jq
```

#### 2.3 Создание архива с образами
```bash
# Сохраняем образы в tar файлы
docker save staffprobot_web:latest > staffprobot_web_$(date +%Y%m%d_%H%M%S).tar
docker save staffprobot_bot:latest > staffprobot_bot_$(date +%Y%m%d_%H%M%S).tar
docker save staffprobot_postgres:latest > staffprobot_postgres_$(date +%Y%m%d_%H%M%S).tar
docker save staffprobot_redis:latest > staffprobot_redis_$(date +%Y%m%d_%H%M%S).tar

# Создаем архив с образами и конфигурациями
tar -czf staffprobot_production_images_$(date +%Y%m%d_%H%M%S).tar.gz \
    staffprobot_web_*.tar \
    staffprobot_bot_*.tar \
    staffprobot_postgres_*.tar \
    staffprobot_redis_*.tar \
    docker-compose.prod.yml \
    .env \
    migrations/ \
    requirements.txt

# Проверяем размер архива
ls -lh staffprobot_production_images_*.tar.gz
```

### Этап 3: Развертывание на сервере

#### 3.1 Подготовка сервера
```bash
# Подключаемся к серверу
ssh user@yourdomain.com

# Переходим в рабочую директорию
cd /opt

# Останавливаем текущее production окружение
docker compose -f docker-compose.prod.yml down

# Создаем бэкап production базы данных
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres staffprobot_prod > prod_backup_$(date +%Y%m%d_%H%M%S).sql

# Создаем бэкап production конфигураций
tar -czf prod_config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env docker-compose.prod.yml
```

#### 3.2 Передача архива на сервер
```bash
# На локальной машине - загружаем архив на сервер
scp staffprobot_production_images_*.tar.gz user@yourdomain.com:/tmp/

# На сервере - проверяем загрузку
ls -la /tmp/staffprobot_production_images_*.tar.gz
```

#### 3.3 Распаковка и загрузка образов
```bash
# На сервере - переходим в рабочую директорию
cd /opt

# Распаковываем архив
tar -xzf /tmp/staffprobot_production_images_*.tar.gz

# Загружаем образы в Docker
docker load < staffprobot_web_*.tar
docker load < staffprobot_bot_*.tar
docker load < staffprobot_postgres_*.tar
docker load < staffprobot_redis_*.tar

# Проверяем загруженные образы
docker images | grep staffprobot
```

#### 3.4 Настройка production конфигурации
```bash
# Копируем production конфигурации
cp .env .env
cp docker-compose.prod.yml .

# Проверяем конфигурации
cat .env | grep -E "(DATABASE_URL|REDIS_URL|TELEGRAM_BOT_TOKEN)"
```

#### 3.5 Запуск production на сервере
```bash
# Запускаем production окружение
docker compose -f docker-compose.prod.yml up -d

# Проверяем статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Проверяем логи
docker compose -f docker-compose.prod.yml logs web
docker compose -f docker-compose.prod.yml logs bot

# Тестируем API
curl -s "http://localhost:8001/api/health" | jq
```

### Этап 4: Восстановление dev окружения

#### 4.1 Восстановление dev окружения локально
```bash
# На локальной машине - переходим в корень проекта
cd /path/to/staffprobot

# Запускаем dev окружение
docker compose -f docker-compose.dev.yml up -d

# Восстанавливаем бэкап базы данных
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev < dev_backup_*.sql

# Проверяем работу dev окружения
curl -s "http://localhost:8001/api/health" | jq
```

## 🔧 Команды для быстрой проверки

### Проверка статуса сервисов
```bash
# Проверка контейнеров
docker compose -f docker-compose.prod.yml ps

# Проверка логов
docker compose -f docker-compose.prod.yml logs --tail=20

# Проверка API
curl -s "http://localhost:8001/api/health" | jq
```

### Проверка базы данных
```bash
# Подключение к БД
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod

# Проверка таблиц
\dt

# Проверка данных
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM objects;
SELECT COUNT(*) FROM shifts;

# Проверка суперадмина
SELECT id, telegram_id, first_name, last_name, role, is_active 
FROM users 
WHERE role = 'superadmin' OR roles::text LIKE '%superadmin%';
```

## 🚨 Устранение неполадок

### Проблема: Контейнеры не запускаются
```bash
# Проверяем логи
docker compose -f docker-compose.prod.yml logs

# Проверяем конфигурацию
docker compose -f docker-compose.prod.yml config

# Перезапускаем
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Проблема: База данных не подключается
```bash
# Проверяем переменные окружения
docker compose -f docker-compose.prod.yml exec web env | grep DATABASE

# Проверяем подключение к БД
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "SELECT 1"
```

### Проблема: API не отвечает
```bash
# Проверяем порты
netstat -tlnp | grep 8001

# Проверяем логи веб-сервиса
docker compose -f docker-compose.prod.yml logs web
```

### Проблема: Суперадмин не создается
```bash
# Проверяем существующих пользователей
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT telegram_id, first_name, last_name, role FROM users;"

# Проверяем user_roles
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "SELECT user_id, roles FROM user_roles;"

# Создаем суперадмина вручную
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "INSERT INTO users (telegram_id, first_name, last_name, role, is_active) VALUES (123456789, 'Super', 'Admin', 'superadmin', true) ON CONFLICT (telegram_id) DO UPDATE SET role = 'superadmin';"
```

## 📝 Чек-лист развертывания

### Перед развертыванием:
- [ ] Создан бэкап dev базы данных
- [ ] Создан бэкап dev конфигураций
- [ ] Остановлено dev окружение
- [ ] Настроен production .env файл

### После сборки образов:
- [ ] Образы собрались без ошибок
- [ ] Production работает локально
- [ ] Протестированы основные функции
- [ ] Создан архив с образами

### После развертывания на сервере:
- [ ] Остановлено старое production окружение
- [ ] Создан бэкап production базы данных
- [ ] Загружены новые образы
- [ ] Запущено новое production окружение
- [ ] Проверены все сервисы
- [ ] Создан суперадминистратор
- [ ] Проверен доступ суперадмина
- [ ] Восстановлено dev окружение

## 🔄 Откат на предыдущую версию

### Если что-то пошло не так:
```bash
# На сервере - останавливаем новое окружение
docker compose -f docker-compose.prod.yml down

# Восстанавливаем старые конфигурации
tar -xzf prod_config_backup_*.tar.gz

# Восстанавливаем старую базу данных
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod < prod_backup_*.sql
```

## 📊 Мониторинг после развертывания

### Проверка работы системы:
```bash
# Статус всех сервисов
docker compose -f docker-compose.prod.yml ps

# Логи в реальном времени
docker compose -f docker-compose.prod.yml logs -f

# Использование ресурсов
docker stats
```

### Проверка API endpoints:
```bash
# Health check
curl -s "http://localhost:8001/api/health" | jq

# Проверка аутентификации
curl -s "http://localhost:8001/api/auth/me" | jq

# Проверка объектов
curl -s "http://localhost:8001/api/objects" | jq
```

---

**Важно**: Всегда создавайте бэкапы перед развертыванием и тестируйте production локально перед передачей на сервер!
