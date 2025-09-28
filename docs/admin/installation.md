# Установка и настройка StaffProBot

## 📋 Предварительные требования

### Системные требования
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- Docker 20.10+
- Docker Compose 2.0+
- Git
- Минимум 4 GB RAM, 20 GB дискового пространства

### Внешние сервисы
- Telegram Bot Token (от @BotFather)
- Домен для HTTPS (опционально)
- Email для уведомлений (опционально)

## 🚀 Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-org/staffprobot.git
cd staffprobot
```

### 2. Настройка окружения
```bash
# Копируем файл с переменными окружения
cp env.example .env

# Редактируем настройки
nano .env
```

### 3. Основные настройки в .env
```bash
# База данных
DATABASE_URL=postgresql://postgres:password@postgres:5432/staffprobot_dev
POSTGRES_DB=staffprobot_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://redis:6379/0

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# JWT секреты
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256

# Домен и SSL
DOMAIN=localhost:8001
SSL_EMAIL=admin@yourdomain.com
USE_HTTPS=false

# Email (опционально)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 4. Запуск системы
```bash
# Запуск в режиме разработки
docker compose -f docker-compose.dev.yml up -d

# Проверка статуса
docker compose -f docker-compose.dev.yml ps
```

### 5. Инициализация базы данных
```bash
# Применение миграций
docker compose -f docker-compose.dev.yml exec web alembic upgrade head

# Создание суперадминистратора (опционально)
docker compose -f docker-compose.dev.yml exec web python -c "
from apps.web.services.user_service import UserService
from core.database.session import get_async_session
import asyncio

async def create_superadmin():
    async with get_async_session() as session:
        user_service = UserService(session)
        await user_service.create_superadmin(
            telegram_id=123456789,
            username='admin',
            first_name='Admin',
            last_name='User'
        )
        print('Суперадминистратор создан')

asyncio.run(create_superadmin())
"
```

## 🔧 Настройка для продакшена

### 1. Настройка домена
```bash
# В админ-панели перейдите в "Системные настройки"
# Укажите ваш домен: yourdomain.com
# Настройте SSL (если нужно)
```

### 2. Настройка Nginx
```bash
# Система автоматически сгенерирует конфигурацию Nginx
# Файл будет создан в /etc/nginx/sites-available/staffprobot.conf
# Создайте симлинк:
sudo ln -s /etc/nginx/sites-available/staffprobot.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Настройка SSL (Let's Encrypt)
```bash
# В админ-панели:
# 1. Перейдите в "Системные настройки"
# 2. Укажите email для Let's Encrypt
# 3. Нажмите "Настроить SSL"
# 4. Система автоматически получит сертификаты
```

### 4. Настройка резервного копирования
```bash
# Добавьте в crontab:
# Ежедневное резервное копирование в 2:00
0 2 * * * /path/to/staffprobot/scripts/backup.sh

# Еженедельная очистка старых бэкапов
0 3 * * 0 /path/to/staffprobot/scripts/cleanup_backups.sh
```

## 🔍 Проверка установки

### 1. Проверка сервисов
```bash
# Статус всех контейнеров
docker compose -f docker-compose.dev.yml ps

# Логи веб-приложения
docker compose -f docker-compose.dev.yml logs web

# Логи бота
docker compose -f docker-compose.dev.yml logs bot
```

### 2. Проверка веб-интерфейса
- Откройте `http://localhost:8001` (или ваш домен)
- Проверьте доступность админ-панели
- Войдите с учетными данными суперадминистратора

### 3. Проверка Telegram бота
- Найдите вашего бота в Telegram
- Отправьте команду `/start`
- Проверьте ответ бота

### 4. Проверка базы данных
```bash
# Подключение к БД
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev

# Проверка таблиц
\dt

# Выход
\q
```

## 🚨 Устранение проблем

### Проблема: Контейнеры не запускаются
```bash
# Проверьте логи
docker compose -f docker-compose.dev.yml logs

# Пересоберите контейнеры
docker compose -f docker-compose.dev.yml build --no-cache
docker compose -f docker-compose.dev.yml up -d
```

### Проблема: Ошибки базы данных
```bash
# Проверьте подключение к БД
docker compose -f docker-compose.dev.yml exec postgres pg_isready -U postgres

# Примените миграции
docker compose -f docker-compose.dev.yml exec web alembic upgrade head
```

### Проблема: Бот не отвечает
```bash
# Проверьте токен бота
echo $TELEGRAM_BOT_TOKEN

# Проверьте логи бота
docker compose -f docker-compose.dev.yml logs bot --tail=50
```

## 📚 Дополнительные настройки

### Настройка мониторинга
- Prometheus для метрик
- Grafana для дашбордов
- Alertmanager для уведомлений

### Настройка логирования
- Централизованное логирование
- Ротация логов
- Анализ логов

### Настройка безопасности
- Firewall правила
- SSL сертификаты
- Регулярные обновления

---

**Следующий раздел**: [Управление пользователями](user_management.md)
