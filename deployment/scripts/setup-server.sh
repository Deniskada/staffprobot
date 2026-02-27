#!/bin/bash
# Скрипт полной настройки сервера для staffprobot.ru

set -e

DOMAIN="staffprobot.ru"
USER="staffprobot"
PROJECT_DIR="/opt/sites/staffprobot"

echo "🚀 Настройка сервера для $DOMAIN"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo $0"
    exit 1
fi

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка необходимых пакетов
echo "🔧 Установка пакетов..."
apt install -y \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    htop \
    nano \
    vim

# Установка Docker
echo "🐳 Установка Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Установка Docker Compose
echo "🐙 Установка Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Создание пользователя для деплоя
echo "👤 Создание пользователя $USER..."
if ! id "$USER" &>/dev/null; then
    echo "Создание нового пользователя $USER..."
    useradd -m -s /bin/bash $USER
    usermod -aG docker $USER
    usermod -aG sudo $USER
    echo "✅ Пользователь $USER создан"
else
    echo "Пользователь $USER уже существует, обновляем группы..."
    usermod -aG docker $USER
    usermod -aG sudo $USER
    echo "✅ Группы пользователя $USER обновлены"
fi

# Создание директории проекта
echo "📁 Создание директории проекта..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Создание директории $PROJECT_DIR..."
    mkdir -p $PROJECT_DIR
    chown $USER:$USER $PROJECT_DIR
    echo "✅ Директория $PROJECT_DIR создана"
else
    echo "Директория $PROJECT_DIR уже существует, обновляем права..."
    chown $USER:$USER $PROJECT_DIR
    echo "✅ Права на директорию $PROJECT_DIR обновлены"
fi

# Настройка SSH
echo "🔐 Настройка SSH..."
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# Настройка firewall
echo "🔥 Настройка firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Настройка fail2ban
echo "🛡️ Настройка fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl start fail2ban

# Установка Nginx
echo "🌐 Установка Nginx..."
apt install -y nginx

# Настройка системных лимитов
echo "⚙️ Настройка системных лимитов..."
cat >> /etc/security/limits.conf << EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF

# Настройка sysctl
echo "🔧 Настройка sysctl..."
cat >> /etc/sysctl.conf << EOF
# Network optimizations
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 10
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.tcp_congestion_control = bbr
EOF

sysctl -p

# Создание swap файла
echo "💾 Создание swap файла..."
if [ ! -f /swapfile ]; then
    echo "Создание нового swap файла..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        echo "✅ Запись добавлена в /etc/fstab"
    else
        echo "✅ Запись уже существует в /etc/fstab"
    fi
    echo "✅ Swap файл создан и активирован"
else
    echo "Swap файл уже существует, проверяем статус..."
    if ! swapon --show | grep -q /swapfile; then
        echo "Активируем существующий swap файл..."
        swapon /swapfile
    else
        echo "✅ Swap файл уже активен"
    fi
fi

# Настройка логирования
echo "📝 Настройка логирования..."
mkdir -p /var/log/staffprobot
chown $USER:$USER /var/log/staffprobot

# Создание systemd сервиса для мониторинга
echo "🔍 Создание сервиса мониторинга..."
cat > /etc/systemd/system/staffprobot-monitor.service << EOF
[Unit]
Description=StaffProBot Monitoring
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable staffprobot-monitor

# Создание скрипта деплоя
echo "🚀 Создание скрипта деплоя..."
cat > $PROJECT_DIR/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Deploying StaffProBot..."

# Переход в директорию проекта
cd /opt/staffprobot

# Обновление кода
git pull origin main

# Сборка и запуск
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Ожидание готовности сервисов
sleep 30

# Проверка здоровья
if [ -x "$PROJECT_DIR/scripts/health-check.sh" ]; then
    ./scripts/health-check.sh
else
    echo "⚠️ health-check.sh не найден, пропускаем проверку здоровья на первом запуске"
fi

echo "✅ Deployment completed!"
EOF

chmod +x $PROJECT_DIR/deploy.sh
chown $USER:$USER $PROJECT_DIR/deploy.sh

# Создание скрипта проверки здоровья
echo "🏥 Создание скрипта проверки здоровья..."
mkdir -p $PROJECT_DIR/scripts
cat > $PROJECT_DIR/scripts/health-check.sh << 'EOF'
#!/bin/bash

echo "🏥 Checking service health..."

# Проверка Docker контейнеров
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "❌ Some containers are not running"
    exit 1
fi

# Проверка HTTP endpoints
if ! curl -f -s https://staffprobot.ru/health > /dev/null; then
    echo "❌ Main site is not responding"
    exit 1
fi

if ! curl -f -s https://api.staffprobot.ru/health > /dev/null; then
    echo "❌ API is not responding"
    exit 1
fi

echo "✅ All services are healthy"
EOF

chmod +x $PROJECT_DIR/scripts/health-check.sh
chown $USER:$USER $PROJECT_DIR/scripts/health-check.sh

# Создание директории для логов
mkdir -p $PROJECT_DIR/logs
chown $USER:$USER $PROJECT_DIR/logs

# Настройка ротации логов
echo "📋 Настройка ротации логов..."
cat > /etc/logrotate.d/staffprobot << EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload nginx
    endscript
}
EOF

echo "✅ Настройка сервера завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Скопируйте SSH ключ для пользователя $USER"
echo "2. Запустите: sudo -u $USER git clone <repository> $PROJECT_DIR"
echo "3. Настройте DNS записи для $DOMAIN"
echo "4. Запустите: sudo ./deployment/scripts/setup-ssl.sh"
echo "5. Запустите: sudo -u $USER $PROJECT_DIR/deploy.sh"
echo ""
echo "🌐 После настройки сайт будет доступен по адресу: https://$DOMAIN"
