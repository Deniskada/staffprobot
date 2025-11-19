# 🚀 Развертывание StaffProBot на staffprobot.ru

Полное руководство по развертыванию StaffProBot в production окружении.

## 📋 Предварительные требования

### 1. Сервер
- **ОС**: Ubuntu 22.04 LTS
- **RAM**: Минимум 2GB (рекомендуется 4GB)
- **CPU**: Минимум 2 ядра
- **Диск**: Минимум 20GB SSD
- **Сеть**: Статический IP адрес

### 2. Домен
- **Основной домен**: staffprobot.ru ✅
- **Поддомены**:
  - `api.staffprobot.ru` - API
  - `admin.staffprobot.ru` - Админка
  - `bot.staffprobot.ru` - Telegram webhook

### 3. DNS настройки
```
A     staffprobot.ru          → IP_СЕРВЕРА
A     www.staffprobot.ru      → IP_СЕРВЕРА
A     api.staffprobot.ru      → IP_СЕРВЕРА
A     admin.staffprobot.ru    → IP_СЕРВЕРА
A     bot.staffprobot.ru      → IP_СЕРВЕРА
CNAME *.staffprobot.ru        → staffprobot.ru
```

## 🔧 Пошаговая инструкция

### Шаг 1: Подготовка сервера

1. **Подключение к серверу**:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

2. **Запуск скрипта настройки**:
   ```bash
   wget https://raw.githubusercontent.com/your-repo/staffprobot/main/deployment/scripts/setup-server.sh
   chmod +x setup-server.sh
   sudo ./setup-server.sh
   ```

3. **Настройка SSH ключей для пользователя**:
   ```bash
   sudo -u staffprobot mkdir -p /home/staffprobot/.ssh
   sudo -u staffprobot nano /home/staffprobot/.ssh/authorized_keys
   # Добавьте ваш публичный SSH ключ
   sudo chown staffprobot:staffprobot /home/staffprobot/.ssh/authorized_keys
   sudo chmod 600 /home/staffprobot/.ssh/authorized_keys
   ```

### Шаг 2: Клонирование репозитория

```bash
sudo -u staffprobot git clone https://github.com/your-repo/staffprobot.git /opt/staffprobot
cd /opt/staffprobot
```

### Шаг 3: Настройка переменных окружения

```bash
sudo -u staffprobot cp deployment/env.prod.example .env.prod
sudo -u staffprobot nano .env.prod
```

**Обязательно заполните**:
- `POSTGRES_PASSWORD` - надежный пароль для БД
- `REDIS_PASSWORD` - надежный пароль для Redis
- `RABBITMQ_PASSWORD` - надежный пароль для RabbitMQ
- `TELEGRAM_BOT_TOKEN_PROD` - токен вашего бота
- `OPENAI_API_KEY` - ключ OpenAI API
- `SECRET_KEY` - секретный ключ (минимум 32 символа)
- `GRAFANA_PASSWORD` - пароль для Grafana

### Шаг 4: Настройка SSL сертификатов

```bash
sudo ./deployment/scripts/setup-ssl.sh
```

### Шаг 5: Настройка Nginx

```bash
sudo cp deployment/nginx/staffprobot.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/staffprobot.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Шаг 6: Первый деплой

```bash
sudo -u staffprobot ./deploy.sh
```

### Шаг 7: Настройка GitHub Actions

1. **Добавьте Secrets в GitHub**:
   - `PRODUCTION_HOST` - IP адрес сервера
   - `PRODUCTION_USER` - staffprobot
   - `PRODUCTION_SSH_KEY` - приватный SSH ключ
   - `SLACK_WEBHOOK` - URL webhook для Slack (опционально)

2. **Проверьте workflow**:
   - Перейдите в Actions в GitHub
   - Убедитесь, что workflow запускается при push в main

## 🔍 Проверка развертывания

### Проверка сервисов
```bash
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Логи
docker-compose -f docker-compose.prod.yml logs -f

# Проверка здоровья
./scripts/health-check.sh
```

### Проверка веб-интерфейса
- **Основной сайт**: https://staffprobot.ru
- **API**: https://api.staffprobot.ru
- **Админка**: https://admin.staffprobot.ru
- **Grafana**: https://staffprobot.ru:3000 (admin/admin)

### Проверка SSL
```bash
# Проверка сертификатов
openssl s_client -connect staffprobot.ru:443 -servername staffprobot.ru

# Проверка автообновления
sudo certbot renew --dry-run
```

## 📊 Мониторинг

### Prometheus
- **URL**: http://staffprobot.ru:9090
- **Метрики**: CPU, память, БД, Redis, RabbitMQ

### Grafana
- **URL**: http://staffprobot.ru:3000
- **Логин**: admin
- **Пароль**: из .env.prod

### Логи
```bash
# Логи приложения
tail -f /var/log/staffprobot/app.log

# Логи Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Логи Docker
docker-compose -f docker-compose.prod.yml logs -f bot
```

## 🔄 Обновление

### Автоматическое обновление
При push в ветку `main` GitHub Actions автоматически:
1. Запустит тесты
2. Соберет Docker образ
3. Развернет на сервере
4. Проверит здоровье сервисов

### Ручное обновление
```bash
cd /opt/staffprobot
sudo -u staffprobot git pull origin main
sudo -u staffprobot ./deploy.sh
```

### Откат
```bash
cd /opt/staffprobot
sudo -u staffprobot git checkout HEAD~1
sudo -u staffprobot ./deploy.sh
```

## 🛠️ Устранение неполадок

### Проблемы с SSL
```bash
# Проверка сертификатов
sudo certbot certificates

# Обновление сертификатов
sudo certbot renew

# Перезапуск Nginx
sudo systemctl reload nginx
```

### Проблемы с Docker
```bash
# Очистка Docker
docker system prune -a

# Перезапуск сервисов
docker-compose -f docker-compose.prod.yml restart
```

### Проблемы с БД
```bash
# Подключение к БД
docker-compose -f docker-compose.prod.yml exec postgres psql -U staffprobot_user -d staffprobot_prod

# Проверка миграций
docker-compose -f docker-compose.prod.yml exec bot alembic current
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи**: `docker-compose -f docker-compose.prod.yml logs`
2. **Проверьте статус**: `./scripts/health-check.sh`
3. **Проверьте мониторинг**: Grafana дашборды
4. **Создайте issue** в GitHub с подробным описанием

## 🔐 Безопасность

### Рекомендации
- Регулярно обновляйте систему
- Используйте сильные пароли
- Настройте мониторинг безопасности
- Регулярно проверяйте логи
- Настройте бэкапы

### Бэкапы
```bash
# Ручной бэкап БД
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U staffprobot_user staffprobot_prod > backup_$(date +%Y%m%d).sql

# Автоматические бэкапы настроены в docker-compose.prod.yml
```

---

**🎉 Поздравляем! StaffProBot успешно развернут на staffprobot.ru!**
