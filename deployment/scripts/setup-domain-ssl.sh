#!/bin/bash
# Скрипт автоматической настройки SSL для StaffProBot

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Проверка аргументов
if [ $# -lt 2 ]; then
    echo "Использование: $0 <domain> <email> [options]"
    echo ""
    echo "Аргументы:"
    echo "  domain    - домен для настройки SSL (например: example.com)"
    echo "  email     - email для Let's Encrypt (например: admin@example.com)"
    echo ""
    echo "Опции:"
    echo "  --force   - принудительная настройка (перезаписать существующие сертификаты)"
    echo "  --dry-run - тестовый запуск без изменений"
    echo "  --help    - показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 example.com admin@example.com"
    echo "  $0 example.com admin@example.com --force"
    echo "  $0 example.com admin@example.com --dry-run"
    exit 1
fi

DOMAIN=$1
EMAIL=$2
FORCE=false
DRY_RUN=false

# Обработка опций
while [[ $# -gt 2 ]]; do
    case $3 in
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Справка по использованию скрипта setup-domain-ssl.sh"
            exit 0
            ;;
        *)
            error "Неизвестная опция: $3"
            exit 1
            ;;
    esac
done

log "🚀 Начинаем настройку SSL для домена: $DOMAIN"
log "📧 Email для Let's Encrypt: $EMAIL"

if [ "$DRY_RUN" = true ]; then
    warning "🔍 Режим тестового запуска - изменения не будут применены"
fi

# Функция проверки прав root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Этот скрипт должен быть запущен с правами root"
        error "Используйте: sudo $0 $*"
        exit 1
    fi
}

# Функция проверки зависимостей
check_dependencies() {
    log "🔍 Проверяем зависимости..."
    
    local missing_deps=()
    
    # Проверяем nginx
    if ! command -v nginx &> /dev/null; then
        missing_deps+=("nginx")
    fi
    
    # Проверяем certbot
    if ! command -v certbot &> /dev/null; then
        missing_deps+=("certbot")
    fi
    
    # Проверяем openssl
    if ! command -v openssl &> /dev/null; then
        missing_deps+=("openssl")
    fi
    
    # Проверяем curl
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Отсутствуют необходимые зависимости: ${missing_deps[*]}"
        log "Установите их с помощью:"
        log "  apt update && apt install -y ${missing_deps[*]}"
        exit 1
    fi
    
    success "Все зависимости установлены"
}

# Функция проверки DNS
check_dns() {
    log "🌐 Проверяем DNS резолвинг для домена: $DOMAIN"
    
    # Проверяем основной домен
    if ! nslookup "$DOMAIN" > /dev/null 2>&1; then
        error "DNS не настроен для домена $DOMAIN"
        error "Убедитесь, что домен указывает на этот сервер"
        exit 1
    fi
    
    # Проверяем www поддомен
    if ! nslookup "www.$DOMAIN" > /dev/null 2>&1; then
        warning "DNS не настроен для www.$DOMAIN (необязательно)"
    fi
    
    # Проверяем поддомены
    local subdomains=("api" "admin" "bot")
    for subdomain in "${subdomains[@]}"; do
        if ! nslookup "$subdomain.$DOMAIN" > /dev/null 2>&1; then
            warning "DNS не настроен для $subdomain.$DOMAIN (необязательно)"
        fi
    done
    
    success "DNS резолвинг работает для $DOMAIN"
}

# Функция проверки доступности портов
check_ports() {
    log "🔌 Проверяем доступность портов..."
    
    # Проверяем, что порты 80 и 443 свободны
    if netstat -tuln | grep -q ":80 "; then
        warning "Порт 80 уже используется"
    fi
    
    if netstat -tuln | grep -q ":443 "; then
        warning "Порт 443 уже используется"
    fi
    
    success "Порты проверены"
}

# Функция остановки nginx
stop_nginx() {
    log "⏹️ Останавливаем nginx..."
    
    if systemctl is-active --quiet nginx; then
        if [ "$DRY_RUN" = false ]; then
            systemctl stop nginx
            sleep 2
        fi
        success "nginx остановлен"
    else
        log "nginx уже остановлен"
    fi
}

# Функция запуска nginx
start_nginx() {
    log "▶️ Запускаем nginx..."
    
    if [ "$DRY_RUN" = false ]; then
        systemctl start nginx
        sleep 2
        
        if systemctl is-active --quiet nginx; then
            success "nginx запущен"
        else
            error "Не удалось запустить nginx"
            return 1
        fi
    else
        log "nginx был бы запущен (dry-run)"
    fi
}

# Функция получения сертификатов
obtain_certificates() {
    log "🔐 Получаем SSL сертификаты через Let's Encrypt..."
    
    # Подготавливаем список доменов
    local domains=("$DOMAIN")
    if ! nslookup "www.$DOMAIN" > /dev/null 2>&1; then
        domains+=("www.$DOMAIN")
    fi
    
    # Добавляем поддомены если они резолвятся
    local subdomains=("api" "admin" "bot")
    for subdomain in "${subdomains[@]}"; do
        if nslookup "$subdomain.$DOMAIN" > /dev/null 2>&1; then
            domains+=("$subdomain.$DOMAIN")
        fi
    done
    
    log "Домены для сертификата: ${domains[*]}"
    
    if [ "$DRY_RUN" = false ]; then
        # Формируем команду certbot
        local certbot_cmd=(
            "certbot" "certonly"
            "--standalone"
            "--email" "$EMAIL"
            "--agree-tos"
            "--no-eff-email"
            "--domains" "$(IFS=,; echo "${domains[*]}")"
            "--non-interactive"
        )
        
        # Добавляем --force-renewal если нужно
        if [ "$FORCE" = true ]; then
            certbot_cmd+=("--force-renewal")
        fi
        
        # Выполняем команду
        if "${certbot_cmd[@]}"; then
            success "Сертификаты успешно получены"
        else
            error "Ошибка получения сертификатов"
            return 1
        fi
    else
        log "Сертификаты были бы получены (dry-run)"
    fi
}

# Функция проверки сертификатов
verify_certificates() {
    log "✅ Проверяем полученные сертификаты..."
    
    local cert_path="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    local key_path="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
    
    if [ ! -f "$cert_path" ] || [ ! -f "$key_path" ]; then
        error "Файлы сертификатов не найдены"
        return 1
    fi
    
    # Проверяем валидность сертификата
    if openssl x509 -in "$cert_path" -noout -checkend 0 > /dev/null 2>&1; then
        success "Сертификат валиден"
    else
        error "Сертификат невалиден"
        return 1
    fi
    
    # Получаем информацию о сертификате
    local cert_info=$(openssl x509 -in "$cert_path" -noout -text | grep -E "(Subject:|Issuer:|Not Before:|Not After:)")
    log "Информация о сертификате:"
    echo "$cert_info" | while read -r line; do
        log "  $line"
    done
    
    success "Сертификаты проверены"
}

# Функция настройки nginx
configure_nginx() {
    log "⚙️ Настраиваем nginx..."
    
    local nginx_config="/etc/nginx/sites-available/staffprobot-$DOMAIN.conf"
    local nginx_enabled="/etc/nginx/sites-enabled/staffprobot-$DOMAIN.conf"
    
    if [ "$DRY_RUN" = false ]; then
        # Создаем конфигурацию nginx
        cat > "$nginx_config" << EOF
# Nginx конфигурация для $DOMAIN
# Сгенерировано автоматически $(date)

# Редирект с HTTP на HTTPS
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

# Основной сайт
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # Основной сайт
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# API поддомен
server {
    listen 443 ssl http2;
    server_name api.$DOMAIN;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers для API
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    add_header Access-Control-Allow-Origin "https://$DOMAIN";
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
    add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With";
    
    # API endpoints
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# Admin поддомен
server {
    listen 443 ssl http2;
    server_name admin.$DOMAIN;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers для админки
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # Админка
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# Bot webhook поддомен
server {
    listen 443 ssl http2;
    server_name bot.$DOMAIN;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    
    # Telegram webhook
    location /webhook {
        proxy_pass http://localhost:8001/webhook;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:8001/health;
        access_log off;
    }
}
EOF
        
        # Включаем конфигурацию
        ln -sf "$nginx_config" "$nginx_enabled"
        
        # Удаляем дефолтную конфигурацию
        rm -f /etc/nginx/sites-enabled/default
        
        # Проверяем конфигурацию nginx
        if nginx -t; then
            success "Конфигурация nginx создана и проверена"
        else
            error "Ошибка в конфигурации nginx"
            return 1
        fi
    else
        log "Конфигурация nginx была бы создана (dry-run)"
    fi
}

# Функция настройки автообновления
setup_auto_renewal() {
    log "🔄 Настраиваем автообновление сертификатов..."
    
    if [ "$DRY_RUN" = false ]; then
        # Добавляем задачу в crontab
        local cron_job="0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'"
        
        # Проверяем, есть ли уже такая задача
        if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
            (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
            success "Автообновление настроено"
        else
            log "Автообновление уже настроено"
        fi
        
        # Тестируем автообновление
        if certbot renew --dry-run; then
            success "Тест автообновления прошел успешно"
        else
            warning "Тест автообновления не прошел"
        fi
    else
        log "Автообновление было бы настроено (dry-run)"
    fi
}

# Функция финальной проверки
final_check() {
    log "🔍 Выполняем финальную проверку..."
    
    # Проверяем, что nginx работает
    if systemctl is-active --quiet nginx; then
        success "nginx работает"
    else
        error "nginx не работает"
        return 1
    fi
    
    # Проверяем доступность сайта
    if curl -s -f "https://$DOMAIN" > /dev/null; then
        success "Сайт доступен по HTTPS: https://$DOMAIN"
    else
        warning "Сайт недоступен по HTTPS (возможно, приложение не запущено)"
    fi
    
    # Проверяем API
    if curl -s -f "https://api.$DOMAIN" > /dev/null; then
        success "API доступен по HTTPS: https://api.$DOMAIN"
    else
        warning "API недоступен по HTTPS"
    fi
    
    success "Финальная проверка завершена"
}

# Основная функция
main() {
    log "🚀 Начинаем настройку SSL для StaffProBot"
    
    # Выполняем все шаги
    check_root
    check_dependencies
    check_dns
    check_ports
    stop_nginx
    obtain_certificates
    verify_certificates
    configure_nginx
    start_nginx
    setup_auto_renewal
    final_check
    
    success "🎉 Настройка SSL завершена успешно!"
    log ""
    log "📋 Что было сделано:"
    log "  ✅ Получены SSL сертификаты от Let's Encrypt"
    log "  ✅ Настроен nginx с HTTPS"
    log "  ✅ Настроено автообновление сертификатов"
    log "  ✅ Проверена работоспособность"
    log ""
    log "🌐 Ваш сайт теперь доступен по адресу:"
    log "  • Основной сайт: https://$DOMAIN"
    log "  • API: https://api.$DOMAIN"
    log "  • Админка: https://admin.$DOMAIN"
    log "  • Webhook: https://bot.$DOMAIN"
    log ""
    log "📝 Не забудьте обновить настройки в StaffProBot:"
    log "  • Установите домен: $DOMAIN"
    log "  • Включите HTTPS"
    log "  • Обновите webhook URL в Telegram боте"
}

# Запуск основной функции
main "$@"
