# 🚀 Руководство по развертыванию StaffProBot

## 📋 Обзор

**StaffProBot** - это полнофункциональная система управления персоналом с Telegram ботом и веб-интерфейсом. Система включает:

- **Telegram Bot** - для сотрудников и владельцев
- **Веб-интерфейс** - для владельцев, управляющих и администраторов
- **Система множественных ролей** - owner, employee, manager, superadmin, applicant
- **Геолокационный контроль** - проверка присутствия на объектах
- **Планирование смен** - календарь и автоматическое закрытие
- **Отчетность** - Excel экспорт и аналитика
- **Мониторинг** - Prometheus + Grafana

## 🎯 Статус проекта

✅ **ПРОЕКТ ЗАВЕРШЕН** - Все итерации успешно реализованы
✅ **Готов к production** - Миграции применены, тесты пройдены
✅ **Система стабильна** - Все критические ошибки исправлены

---

## 🛠️ Требования к серверу

### Минимальные требования:
- **CPU**: 2 ядра
- **RAM**: 4 GB
- **Диск**: 20 GB SSD
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+

### Рекомендуемые требования:
- **CPU**: 4 ядра
- **RAM**: 8 GB
- **Диск**: 50 GB SSD
- **OS**: Ubuntu 22.04 LTS

### Программное обеспечение:
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.30+
- **Nginx**: 1.18+ (для reverse proxy)

---

## 📦 Быстрое развертывание

### 1. Подготовка сервера

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Устанавливаем Git
sudo apt install git -y

# Перезагружаемся для применения изменений
sudo reboot
```

### 2. Клонирование проекта

```bash
# Клонируем репозиторий
git clone https://github.com/Deniskada/staffprobot.git
cd staffprobot

# Переключаемся на main ветку
git checkout main
```

### 3. Настройка окружения

```bash
# Создаем файл окружения для продакшена
cp .env.example .env.prod

# Редактируем настройки
nano .env.prod
```

### 4. Основные переменные окружения

```bash
# База данных
DATABASE_URL=postgresql://staffprobot:your_password@postgres:5432/staffprobot_prod
POSTGRES_DB=staffprobot_prod
POSTGRES_USER=staffprobot
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://redis:6379/0

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook

# Веб-приложение
SECRET_KEY=your_secret_key_here
WEB_HOST=0.0.0.0
WEB_PORT=8001

# Мониторинг
GRAFANA_ADMIN_PASSWORD=your_grafana_password

# Доменное имя
DOMAIN_NAME=yourdomain.com
```

### 5. Запуск системы

```bash
# Запускаем production окружение
docker-compose -f docker-compose.prod.yml up -d

# Проверяем статус
docker-compose -f docker-compose.prod.yml ps

# Смотрим логи
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🔧 Подробная настройка

### 1. Настройка Nginx (Reverse Proxy)

```bash
# Устанавливаем Nginx
sudo apt install nginx -y

# Создаем конфигурацию
sudo nano /etc/nginx/sites-available/staffprobot
```

**Конфигурация Nginx:**

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=web:10m rate=30r/s;
    
    # Web application
    location / {
        limit_req zone=web burst=20 nodelay;
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # API endpoints
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Telegram webhook
    location /webhook {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Monitoring
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /prometheus/ {
        proxy_pass http://localhost:9090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активируем конфигурацию
sudo ln -s /etc/nginx/sites-available/staffprobot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2. SSL сертификаты (Let's Encrypt)

```bash
# Устанавливаем Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получаем SSL сертификат
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Проверяем автообновление
sudo certbot renew --dry-run
```

### 3. Настройка Telegram Bot

```bash
# Получаем токен бота от @BotFather в Telegram
# Добавляем в .env.prod:
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Настраиваем webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://yourdomain.com/webhook"}'
```

---

## 🗄️ Управление базой данных

### Применение миграций

```bash
# Проверяем текущую версию
docker-compose -f docker-compose.prod.yml exec web alembic current

# Применяем все миграции
docker-compose -f docker-compose.prod.yml exec web alembic upgrade head

# Проверяем статус
docker-compose -f docker-compose.prod.yml exec web alembic check
```

### Резервное копирование

```bash
# Создаем бэкап
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U staffprobot staffprobot_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстанавливаем из бэкапа
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U staffprobot staffprobot_prod < backup_file.sql
```

---

## 📊 Мониторинг и логи

### Просмотр логов

```bash
# Все сервисы
docker-compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f bot

# Последние 100 строк
docker-compose -f docker-compose.prod.yml logs --tail=100 web
```

### Мониторинг через Grafana

- **URL**: https://yourdomain.com/grafana/
- **Логин**: admin
- **Пароль**: из переменной GRAFANA_ADMIN_PASSWORD

**Дашборды:**
- **System Overview** - общее состояние системы
- **Database Metrics** - метрики PostgreSQL
- **Application Metrics** - метрики приложения
- **Bot Metrics** - метрики Telegram бота

### Prometheus

- **URL**: https://yourdomain.com/prometheus/
- **Метрики**: CPU, RAM, диск, сеть, база данных, приложение

---

## 🔄 Обновление системы

### 1. Создание бэкапа

```bash
# Бэкап базы данных
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U staffprobot staffprobot_prod > backup_before_update_$(date +%Y%m%d_%H%M%S).sql

# Бэкап конфигураций
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env.prod docker-compose.prod.yml
```

### 2. Обновление кода

```bash
# Останавливаем сервисы
docker-compose -f docker-compose.prod.yml down

# Обновляем код
git pull origin main

# Пересобираем образы
docker-compose -f docker-compose.prod.yml build --no-cache

# Запускаем обновленную систему
docker-compose -f docker-compose.prod.yml up -d

# Применяем миграции (если есть)
docker-compose -f docker-compose.prod.yml exec web alembic upgrade head
```

### 3. Проверка после обновления

```bash
# Проверяем статус сервисов
docker-compose -f docker-compose.prod.yml ps

# Проверяем логи
docker-compose -f docker-compose.prod.yml logs --tail=50

# Проверяем веб-интерфейс
curl -I https://yourdomain.com/

# Проверяем API
curl -I https://yourdomain.com/api/health
```

---

## 🚨 Устранение неполадок

### Проблемы с базой данных

```bash
# Проверяем подключение к PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U staffprobot -d staffprobot_prod -c "SELECT 1;"

# Проверяем миграции
docker-compose -f docker-compose.prod.yml exec web alembic current

# Сбрасываем миграции (ОСТОРОЖНО!)
docker-compose -f docker-compose.prod.yml exec web alembic downgrade base
docker-compose -f docker-compose.prod.yml exec web alembic upgrade head
```

### Проблемы с Redis

```bash
# Проверяем подключение к Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Очищаем кэш Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL
```

### Проблемы с Telegram Bot

```bash
# Проверяем webhook
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Сбрасываем webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"

# Устанавливаем webhook заново
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://yourdomain.com/webhook"}'
```

### Проблемы с веб-приложением

```bash
# Проверяем статус контейнера
docker-compose -f docker-compose.prod.yml ps web

# Перезапускаем веб-сервис
docker-compose -f docker-compose.prod.yml restart web

# Проверяем логи
docker-compose -f docker-compose.prod.yml logs web --tail=100
```

---

## 📞 Поддержка

### Контакты
- **GitHub**: https://github.com/Deniskada/staffprobot
- **Issues**: https://github.com/Deniskada/staffprobot/issues

### Полезные команды

```bash
# Проверка здоровья системы
curl https://yourdomain.com/api/health

# Статистика системы
docker stats

# Очистка неиспользуемых образов
docker system prune -a

# Проверка дискового пространства
df -h

# Проверка использования памяти
free -h
```

---

## ✅ Чек-лист развертывания

- [ ] Сервер подготовлен (Docker, Docker Compose, Git)
- [ ] Проект склонирован и настроен
- [ ] Переменные окружения настроены
- [ ] SSL сертификаты установлены
- [ ] Nginx настроен как reverse proxy
- [ ] База данных создана и миграции применены
- [ ] Telegram Bot настроен и webhook установлен
- [ ] Система запущена и проверена
- [ ] Мониторинг настроен (Grafana/Prometheus)
- [ ] Резервное копирование настроено
- [ ] Домен настроен и работает
- [ ] Тестирование всех функций завершено

**🎉 Система готова к работе!**

---

*Последнее обновление: 21 сентября 2025*
*Версия: 1.0*
