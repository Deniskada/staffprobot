#!/bin/bash
# Скрипт настройки SSL сертификатов для staffprobot.ru

set -e

DOMAIN="staffprobot.ru"
EMAIL="admin@staffprobot.ru"  # Замените на ваш email

echo "🔐 Настройка SSL сертификатов для $DOMAIN"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo $0"
    exit 1
fi

# Установка certbot
echo "📦 Установка certbot..."
apt update
apt install -y certbot python3-certbot-nginx

# Остановка nginx для получения сертификатов
echo "⏹️ Остановка nginx..."
systemctl stop nginx

# Получение сертификатов
echo "🔑 Получение SSL сертификатов..."
certbot certonly \
    --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --domains $DOMAIN,www.$DOMAIN,api.$DOMAIN,admin.$DOMAIN,bot.$DOMAIN

# Проверка сертификатов
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✅ Сертификаты успешно получены!"
else
    echo "❌ Ошибка получения сертификатов"
    exit 1
fi

# Настройка автообновления
echo "🔄 Настройка автообновления сертификатов..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -

# Создание тестового обновления
echo "🧪 Тестирование автообновления..."
certbot renew --dry-run

# Настройка nginx
echo "⚙️ Настройка nginx..."
cp deployment/nginx/staffprobot.conf /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/staffprobot.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверка конфигурации nginx
echo "🔍 Проверка конфигурации nginx..."
nginx -t

# Запуск nginx
echo "🚀 Запуск nginx..."
systemctl start nginx
systemctl enable nginx

# Проверка статуса
echo "📊 Статус сервисов:"
systemctl status nginx --no-pager -l

echo "✅ SSL настройка завершена!"
echo "🌐 Сайт доступен по адресу: https://$DOMAIN"
echo "🔧 API доступен по адресу: https://api.$DOMAIN"
echo "👨‍💼 Админка доступна по адресу: https://admin.$DOMAIN"
echo "🤖 Bot webhook: https://bot.$DOMAIN/webhook"
