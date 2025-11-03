# GitHub Actions CI/CD Setup

## Инструкция по настройке автоматического деплоя

### 1. SSH ключ для деплоя уже сгенерирован

**Публичный ключ (добавлен на сервер):**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPNBDyRGQGX0jvGQeT9xkArMrQiQWHcuwwKjq7RlTd7U github-actions-staffprobot-deploy
```

**Приватный ключ (нужно добавить в GitHub Secrets):**

Найден в файле: `/tmp/deploy_key` (локально на твоей машине)

### 2. Разрешить использование Actions (ОДИН РАЗ)

1. Перейди в репозиторий на GitHub
2. **Settings → Actions → General**
3. В разделе "Actions permissions" выбери: **"Allow all actions and reusable workflows"**
4. Нажми **Save** внизу страницы

### 3. Добавление секрета SSH ключа

1. Перейди в **Settings → Secrets and variables → Actions**
2. Убедись что выбран раздел **Repository secrets** (не Environment secrets!)
3. Нажми "New repository secret"
4. Name: `SSH_DEPLOY_KEY`
5. Value: скопируй содержимое приватного ключа из `/tmp/deploy_key`:

```bash
cat /tmp/deploy_key
```

Скопируй весь вывод, включая `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`

6. Сохрани секрет

### 4. Как работает деплой

**Триггер:** Push в ветку `main`

**Этапы:**
1. **test** - Запускает pytest с покрытием
2. **lint** - Проверяет код black/flake8/mypy
3. **security** - Проверяет зависимости (safety/bandit)
4. **deploy** - Делает деплой на production (только если все проверки прошли)
5. **notify** - Уведомляет в Telegram о результатах

**Job deploy:**
- Подключается по SSH к `staffprobot@staffprobot.ru`
- Выполняет:
  - `cd /opt/staffprobot`
  - `git fetch origin`
  - `git reset --hard origin/main`
  - `docker compose -f docker-compose.prod.yml down`
  - `docker compose -f docker-compose.prod.yml up -d`
  - Health check всех сервисов

### 5. Опциональные секреты

Для уведомлений в Telegram добавь:
- `TELEGRAM_BOT_TOKEN` - токен бота
- `TELEGRAM_CHAT_ID` - ID чата куда слать

Для codecov добавь:
- `CODECOV_TOKEN` - токен от codecov.io

### 6. Проверка работы

После добавления секрета:
1. Сделай commit в `main`
2. Перейди на GitHub → Actions
3. Наблюдай за выполнением workflow
4. Деплой произойдет автоматически если все проверки прошли

### 7. Troubleshooting

Если deploy падает:
1. Проверь что SSH ключ добавлен в authorized_keys на сервере
2. Проверь что путь `/opt/staffprobot` существует и доступен
3. Проверь что Docker Compose файл корректный
4. Смотри логи в GitHub Actions → конкретный workflow → deploy job

