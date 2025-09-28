# Устранение неполадок

## 🚨 Критические проблемы

### Система не запускается

#### Проблема: Контейнеры не стартуют
**Симптомы:**
- Контейнеры постоянно перезапускаются
- Ошибки в логах Docker
- Сервисы недоступны

**Диагностика:**
```bash
# Проверка статуса контейнеров
docker compose -f docker-compose.dev.yml ps

# Подробные логи
docker compose -f docker-compose.dev.yml logs

# Проверка ресурсов
docker system df
docker system prune
```

**Решение:**
1. Проверьте доступность ресурсов (RAM, диск)
2. Очистите неиспользуемые Docker ресурсы
3. Пересоберите контейнеры без кэша
4. Проверьте конфигурацию docker-compose

#### Проблема: База данных недоступна
**Симптомы:**
- Ошибки подключения к БД
- Timeout при запросах
- Приложение не запускается

**Диагностика:**
```bash
# Проверка статуса PostgreSQL
docker compose -f docker-compose.dev.yml exec postgres pg_isready -U postgres

# Проверка логов БД
docker compose -f docker-compose.dev.yml logs postgres

# Проверка подключения
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "SELECT 1;"
```

**Решение:**
1. Проверьте переменные окружения DATABASE_URL
2. Убедитесь, что PostgreSQL запущен
3. Проверьте доступность порта 5432
4. Примените миграции: `alembic upgrade head`

### Веб-приложение не работает

#### Проблема: 500 Internal Server Error
**Симптомы:**
- Ошибка 500 при обращении к сайту
- Пустая страница или сообщение об ошибке

**Диагностика:**
```bash
# Логи веб-приложения
docker compose -f docker-compose.dev.yml logs web --tail=50

# Проверка переменных окружения
docker compose -f docker-compose.dev.yml exec web env | grep -E "(DATABASE|REDIS|JWT)"
```

**Решение:**
1. Проверьте логи на наличие ошибок
2. Убедитесь, что все переменные окружения настроены
3. Проверьте подключение к БД и Redis
4. Перезапустите веб-контейнер

#### Проблема: Страницы не загружаются
**Симптомы:**
- Медленная загрузка страниц
- Таймауты
- Частичная загрузка контента

**Диагностика:**
```bash
# Проверка производительности
docker stats

# Проверка сетевых соединений
docker compose -f docker-compose.dev.yml exec web netstat -tulpn

# Тест производительности БД
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "EXPLAIN ANALYZE SELECT * FROM users LIMIT 100;"
```

**Решение:**
1. Оптимизируйте запросы к БД
2. Увеличьте ресурсы контейнеров
3. Настройте кэширование Redis
4. Проверьте индексы в БД

### Telegram бот не отвечает

#### Проблема: Бот не реагирует на команды
**Симптомы:**
- Команды /start не работают
- Бот не отвечает на сообщения
- Ошибки в логах бота

**Диагностика:**
```bash
# Логи бота
docker compose -f docker-compose.dev.yml logs bot --tail=50

# Проверка токена бота
docker compose -f docker-compose.dev.yml exec bot printenv TELEGRAM_BOT_TOKEN

# Тест API Telegram
curl -X GET "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```

**Решение:**
1. Проверьте правильность токена бота
2. Убедитесь, что бот не заблокирован
3. Проверьте webhook настройки
4. Перезапустите бот-контейнер

## ⚠️ Проблемы средней критичности

### Проблемы с SSL

#### Проблема: SSL сертификаты не получаются
**Симптомы:**
- Ошибки при настройке SSL
- HTTPS не работает
- Ошибки certbot

**Диагностика:**
```bash
# Проверка DNS
nslookup yourdomain.com
dig yourdomain.com

# Проверка портов
sudo netstat -tulpn | grep -E ":80|:443"

# Логи certbot
sudo certbot logs
```

**Решение:**
1. Убедитесь, что домен указывает на сервер
2. Проверьте, что порты 80 и 443 открыты
3. Остановите другие веб-серверы на время получения сертификатов
4. Используйте режим --standalone для certbot

#### Проблема: SSL сертификаты истекли
**Симптомы:**
- Предупреждения браузера о недействительном сертификате
- HTTPS не работает
- Ошибки в логах

**Решение:**
```bash
# Обновление сертификатов
sudo certbot renew

# Принудительное обновление
sudo certbot renew --force-renewal

# Проверка статуса
sudo certbot certificates
```

### Проблемы с производительностью

#### Проблема: Медленная работа системы
**Симптомы:**
- Долгая загрузка страниц
- Таймауты запросов
- Высокая загрузка сервера

**Диагностика:**
```bash
# Мониторинг ресурсов
htop
iotop
free -h
df -h

# Анализ медленных запросов
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"
```

**Решение:**
1. Оптимизируйте запросы к БД
2. Добавьте индексы для часто используемых полей
3. Увеличьте ресурсы сервера
4. Настройте кэширование

## 🔧 Проблемы конфигурации

### Проблемы с переменными окружения

#### Проблема: Неправильные настройки
**Симптомы:**
- Ошибки подключения к сервисам
- Неожиданное поведение приложения
- Ошибки аутентификации

**Диагностика:**
```bash
# Проверка всех переменных
docker compose -f docker-compose.dev.yml exec web env

# Проверка конкретных переменных
docker compose -f docker-compose.dev.yml exec web printenv DATABASE_URL
docker compose -f docker-compose.dev.yml exec web printenv REDIS_URL
```

**Решение:**
1. Проверьте файл .env
2. Убедитесь в правильности формата URL
3. Проверьте доступность внешних сервисов
4. Перезапустите контейнеры после изменений

### Проблемы с миграциями БД

#### Проблема: Ошибки миграций
**Симптомы:**
- Ошибки при применении миграций
- Несоответствие схемы БД
- Ошибки SQL

**Диагностика:**
```bash
# Текущая версия миграций
docker compose -f docker-compose.dev.yml exec web alembic current

# История миграций
docker compose -f docker-compose.dev.yml exec web alembic history

# Проверка состояния БД
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -d staffprobot_dev -c "\dt"
```

**Решение:**
1. Проверьте логи миграций
2. Откатитесь к предыдущей версии: `alembic downgrade -1`
3. Исправьте проблемную миграцию
4. Примените миграции заново: `alembic upgrade head`

## 📊 Диагностические команды

### Проверка состояния системы
```bash
# Общий статус
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs --tail=20

# Ресурсы системы
docker stats --no-stream
df -h
free -h
uptime
```

### Проверка сетевых соединений
```bash
# Порты
sudo netstat -tulpn | grep -E ":80|:443|:5432|:6379"

# DNS
nslookup yourdomain.com
dig yourdomain.com

# Соединения
ss -tulpn
```

### Проверка логов
```bash
# Все сервисы
docker compose -f docker-compose.dev.yml logs --tail=100

# Конкретный сервис
docker compose -f docker-compose.dev.yml logs web --tail=50 -f

# Фильтрация по уровню
docker compose -f docker-compose.dev.yml logs web | grep ERROR
```

## 🔄 Процедуры восстановления

### Восстановление из резервной копии
```bash
# Остановка сервисов
docker compose -f docker-compose.dev.yml down

# Восстановление БД
docker compose -f docker-compose.dev.yml exec postgres pg_restore -U postgres -d staffprobot_dev /backup/backup.sql

# Запуск сервисов
docker compose -f docker-compose.dev.yml up -d
```

### Откат к предыдущей версии
```bash
# Остановка сервисов
docker compose -f docker-compose.dev.yml down

# Откат к предыдущему коммиту
git checkout HEAD~1

# Пересборка и запуск
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d
```

### Сброс к заводским настройкам
```bash
# Полная остановка
docker compose -f docker-compose.dev.yml down -v

# Удаление всех данных
docker system prune -a
docker volume prune

# Пересоздание с нуля
docker compose -f docker-compose.dev.yml up -d
```

## 📞 Получение помощи

### Сбор информации для поддержки
```bash
# Создание отчета о системе
{
  echo "=== System Info ==="
  uname -a
  docker --version
  docker compose --version
  
  echo "=== Container Status ==="
  docker compose -f docker-compose.dev.yml ps
  
  echo "=== Recent Logs ==="
  docker compose -f docker-compose.dev.yml logs --tail=50
  
  echo "=== Resource Usage ==="
  docker stats --no-stream
} > system_report.txt
```

### Контакты поддержки
- **Email**: support@staffprobot.com
- **Telegram**: @staffprobot_support
- **Документация**: https://docs.staffprobot.com
- **GitHub Issues**: https://github.com/your-org/staffprobot/issues

---

**Связанные разделы**:
- [Мониторинг и логи](monitoring.md)
- [Установка и настройка](installation.md)
- [Резервное копирование](backup.md)
