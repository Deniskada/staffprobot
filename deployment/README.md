# Развертывание StaffProBot на staffprobot.ru

## Текущее production-окружение

- **Сервер**: `155.212.217.38` (VPS)
- **ОС**: Ubuntu 22.04 LTS
- **Путь**: `/opt/sites/staffprobot`
- **SSH**: `ssh root@155.212.217.38`
- **Docker Compose**: `docker-compose.prod.yml`
- **Nginx**: общий контейнер `sites_nginx` (конфиг `/opt/sites/nginx/conf.d/staffprobot.conf`)
- **SSL**: Let's Encrypt через общий `sites_certbot`

### DNS

```
A     staffprobot.ru          → 155.212.217.38
A     www.staffprobot.ru      → 155.212.217.38
```

### Dev-окружение

- **Сервер**: `192.168.77.177` (локальный)
- **Прокси**: `dev-proxy` на том же сервере
- **URL**: `https://dev.staffprobot.ru` (через `79.174.62.232`)

---

## Пошаговая инструкция (для нового сервера)

### Шаг 1: Подготовка сервера

```bash
ssh root@155.212.217.38
```

### Шаг 2: Клонирование репозитория

```bash
git clone https://github.com/Deniskada/staffprobot.git /opt/sites/staffprobot
cd /opt/sites/staffprobot
```

### Шаг 3: Настройка переменных окружения

```bash
cp env.example .env
nano .env
```

**Обязательно заполните**: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `RABBITMQ_PASSWORD`, `TELEGRAM_BOT_TOKEN_PROD`, `SECRET_KEY`.

### Шаг 4: SSL сертификат

SSL выдаётся через общий контейнер `sites_certbot`:
```bash
cd /opt/sites
docker compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot \
  --email admin@staffprobot.ru --agree-tos -d staffprobot.ru -d www.staffprobot.ru
```

Затем активировать HTTPS-конфиг:
```bash
cp nginx/conf.d/staffprobot.conf.ssl nginx/conf.d/staffprobot.conf
docker exec sites_nginx nginx -s reload
```

### Шаг 5: Запуск

```bash
cd /opt/sites/staffprobot
docker compose -f docker-compose.prod.yml up -d
```

### GitHub Actions (CI/CD)

Секреты в GitHub:
- `SSH_DEPLOY_KEY` — приватный SSH ключ для деплоя
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — уведомления (опционально)

## Проверка

```bash
# Статус контейнеров
ssh root@155.212.217.38 "cd /opt/sites/staffprobot && docker compose -f docker-compose.prod.yml ps"

# Логи бота
ssh root@155.212.217.38 "docker logs staffprobot_bot_prod --tail 50"

# Веб-интерфейс
curl -sI https://staffprobot.ru/
```

- **Сайт**: https://staffprobot.ru
- **SSL**: Let's Encrypt, автообновление через `sites_certbot`

## Ручное обновление

```bash
ssh root@155.212.217.38
cd /opt/sites/staffprobot
git pull origin main
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Бэкапы

```bash
# Бэкап БД
docker exec staffprobot_postgres_prod pg_dump -U staffprobot staffprobot_prod | gzip > backup_$(date +%Y%m%d).sql.gz
```

## Перезапуск отдельных сервисов

```bash
cd /opt/sites/staffprobot
docker compose -f docker-compose.prod.yml restart web        # изменения в apps/web
docker compose -f docker-compose.prod.yml restart bot        # изменения в apps/bot
docker compose -f docker-compose.prod.yml restart web bot celery_worker celery_beat  # изменения в shared/domain
```
