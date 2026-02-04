# Установка и настройка Project Brain

## Текущая ситуация

Project Brain не найден в системе. Нужно установить и настроить автозапуск.

## Шаг 1: Клонирование проекта

```bash
cd /home/sa/projects
git clone <repository_url> project-brain
cd project-brain
```

**Примечание**: Если репозиторий приватный или нужно создать с нуля, используйте соответствующий метод.

## Шаг 2: Запуск через Docker Compose

```bash
cd /home/sa/projects/project-brain
docker compose -f docker-compose.local.yml up -d
```

## Шаг 3: Проверка запуска

```bash
# Проверить статус контейнеров
docker compose -f docker-compose.local.yml ps

# Проверить здоровье API
curl http://192.168.2.107:8003/health

# Ожидаемый результат: {"status":"ok"}
```

## Шаг 4: Настройка автозапуска через systemd

### Создание systemd сервиса

Создать файл `/etc/systemd/system/project-brain.service`:

```ini
[Unit]
Description=Project Brain Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/sa/projects/project-brain
ExecStart=/usr/bin/docker compose -f docker-compose.local.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.local.yml down
TimeoutStartSec=0
User=sa
Group=sa

[Install]
WantedBy=multi-user.target
```

### Активация сервиса

```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable project-brain.service

# Запустить сервис
sudo systemctl start project-brain.service

# Проверить статус
sudo systemctl status project-brain.service
```

## Альтернативный вариант: через cron

Если systemd недоступен или не подходит:

```bash
# Добавить в crontab
crontab -e

# Добавить строку для запуска при загрузке системы
@reboot cd /home/sa/projects/project-brain && docker compose -f docker-compose.local.yml up -d
```

## Проверка автозапуска

```bash
# Проверить, что сервис включен
sudo systemctl is-enabled project-brain.service

# Должно быть: enabled

# Проверить статус
sudo systemctl status project-brain.service

# Перезагрузить систему для проверки
sudo reboot
```

## Мониторинг и логи

```bash
# Логи systemd сервиса
sudo journalctl -u project-brain.service -f

# Логи Docker контейнеров
docker compose -f /home/sa/projects/project-brain/docker-compose.local.yml logs -f

# Статус контейнеров
docker compose -f /home/sa/projects/project-brain/docker-compose.local.yml ps
```

## Устранение проблем

### Проблема: Сервис не запускается

```bash
# Проверить логи
sudo journalctl -u project-brain.service -n 50

# Проверить права доступа
ls -la /home/sa/projects/project-brain

# Проверить, что docker доступен
docker ps
```

### Проблема: Контейнеры не стартуют

```bash
# Проверить логи контейнеров
docker compose -f /home/sa/projects/project-brain/docker-compose.local.yml logs

# Проверить порты
netstat -tlnp | grep 8003
```

---

**Дата создания**: 2026-02-04  
**Статус**: Требует выполнения
