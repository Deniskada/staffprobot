## Бэкап и восстановление БД без потери кодировки (UTF-8)

Кратко: избегайте пайпа через PowerShell. Делайте бэкап на сервере, скачивайте файл, копируйте в контейнер и восстанавливайте через `psql -f` с явной клиентской кодировкой.

### 1) Создание бэкапа на проде

Выполняется на сервере через SSH, редирект на стороне сервера (не локально):

```bash
ssh staffprobot@staffprobot.ru \
  'cd /opt/staffprobot && \
   docker compose -f docker-compose.prod.yml exec postgres \
   pg_dump -U postgres -d staffprobot_prod \
     --encoding=UTF8 --no-owner --no-privileges --format=plain \
   > /tmp/staffprobot_prod_backup_$(date +%Y%m%d_%H%M%S).sql'
```

Проверить файл:

```bash
ssh staffprobot@staffprobot.ru 'ls -lh /tmp/staffprobot_prod_backup_*.sql | tail -1'
```

Скачать файл локально:

```bash
scp staffprobot@staffprobot.ru:/tmp/staffprobot_prod_backup_YYYYMMDD_HHMMSS.sql .
```

### 2) Подготовка локальной БД (dev)

Важно: база должна совпадать с прод по параметрам `LC_COLLATE`/`LC_CTYPE` и кодировке UTF-8.

```bash
# Остановить dev (по необходимости)
docker compose -f docker-compose.dev.yml down

# Запустить только Postgres
docker compose -f docker-compose.dev.yml up -d postgres

# Дать время на старт
sleep 5

# Пересоздать БД с параметрами как в проде (ENCODING UTF8, LC_COLLATE=C, LC_CTYPE=C)
docker compose -f docker-compose.dev.yml exec postgres \
  psql -U postgres -c "DROP DATABASE IF EXISTS staffprobot_dev;"

docker compose -f docker-compose.dev.yml exec postgres \
  psql -U postgres -c "CREATE DATABASE staffprobot_dev \
    WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;"
```

Проверка параметров БД:

```bash
docker compose -f docker-compose.dev.yml exec postgres \
  psql -U postgres -d staffprobot_dev -c "SHOW SERVER_ENCODING;"

docker compose -f docker-compose.dev.yml exec postgres \
  psql -U postgres -c "SELECT datname, datcollate, datctype FROM pg_database WHERE datname='staffprobot_dev';"
```

### 3) Восстановление дампа БЕЗ PowerShell-пайпа

Нельзя использовать в Windows команду вида `Get-Content dump.sql | docker ... psql`, так как PowerShell конвертирует поток в текст и ломает не-ASCII символы. Вместо этого:

```bash
# Скопировать дамп внутрь контейнера Postgres
docker cp staffprobot_prod_backup_YYYYMMDD_HHMMSS.sql staffprobot_postgres_dev:/tmp/backup.sql

# Восстановить через psql -f с явной клиентской кодировкой
docker compose -f docker-compose.dev.yml exec -e PGCLIENTENCODING=UTF8 postgres \
  psql -U postgres -d staffprobot_dev -f /tmp/backup.sql
```

После восстановления применить миграции:

```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml exec web alembic upgrade head
```

### 4) Быстрая проверка кириллицы

```bash
docker compose -f docker-compose.dev.yml exec postgres \
  psql -U postgres -d staffprobot_dev -c "SELECT first_name, last_name FROM users LIMIT 5;"
```

Если в выводе видны `Алина`, `Екатерина` и т.п. — всё корректно. Если отображаются `????????`, значит дамп восстанавливали через текстовый пайп в PowerShell — повторите шаг 3 корректно.

### Почему возникала проблема

- PowerShell преобразует поток данных в строки (UTF-16) и при передаче через пайп в `docker exec ... psql` часть символов теряется или заменяется на `?`.
- Правильный способ — передавать дамп как файл без промежуточной текстовой обработки: `docker cp` + `psql -f` (или выполняйте восстановление внутри Linux/WSL).

### Дополнительно

- Для Windows-консоли при просмотре вывода можно использовать UTF-8: `chcp 65001` (CMD) или установить `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` (PowerShell), но это не заменяет корректную процедуру восстановления.


