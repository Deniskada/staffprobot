#!/bin/bash
# Локальный скрипт настройки для staffprobot.ru

set -e

DOMAIN="staffprobot.ru"
USER="staffprobot"
PROJECT_DIR="/opt/staffprobot"

echo "🚀 Локальная настройка сервера для $DOMAIN"

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
    vim \
    nginx \
    certbot \
    python3-certbot-nginx

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
useradd -m -s /bin/bash $USER
usermod -aG docker $USER
usermod -aG sudo $USER

# Создание директории проекта
echo "📁 Создание директории проекта..."
mkdir -p $PROJECT_DIR
chown $USER:$USER $PROJECT_DIR

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

# Создание swap файла
echo "💾 Создание swap файла..."
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Создание директории для логов
mkdir -p /var/log/staffprobot
chown $USER:$USER /var/log/staffprobot

echo "✅ Локальная настройка сервера завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Скопируйте SSH ключ для пользователя $USER"
echo "2. Скопируйте проект в $PROJECT_DIR"
echo "3. Настройте DNS записи для $DOMAIN"
echo "4. Запустите настройку SSL и деплой"
