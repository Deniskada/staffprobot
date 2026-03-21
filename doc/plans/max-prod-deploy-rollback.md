# Прод: первый выклад MAX + откат (один токен, max.staffprobot.ru)

Прод сейчас **без MAX**. Этот документ — порядок действий, откат и nginx **только для StaffProBot** (не трогаем vhost’ы cvetbuket.com и цветутцветы.рф).

## Архитектура на проде (важно)

- **Приём webhook MAX** обрабатывает контейнер **`web`** (FastAPI), порт **8001** на хосте, путь **`/max/webhook`** (`apps/web/routes/max_webhook.py`, `MAX_WEBHOOK_PATH`).
- **`bot.staffprobot.ru`** в `deployment/nginx/staffprobot.conf` проксирует только **`/webhook`** → Telegram — **не** подходит как единственная точка для MAX без доработки.
- Отдельный хост **`max.staffprobot.ru`** → прокси на **`http://127.0.0.1:8001/max/webhook`** (и только нужные пути, см. ниже).

## TLS для max.staffprobot.ru

Платформа MAX обычно требует **HTTPS** для URL webhook. «Сертификатов нет» = перед регистрацией webhook нужно получить сертификат:

1. DNS: `A` (или `CNAME`) **`max.staffprobot.ru`** → IP прод-сервера (как у `staffprobot.ru`).
2. На сервере (типично):  
   `certbot certonly --webroot -w /var/www/html -d max.staffprobot.ru`  
   (или тот же механизм, что уже используется для LE на этом хосте).
3. В nginx для `max.staffprobot.ru` указать пути к `fullchain.pem` / `privkey.pem` (отдельная папка `live/max.staffprobot.ru/` или wildcard `*.staffprobot.ru`, если он уже есть).

Пока нет валидного HTTPS — **не регистрировать** webhook в кабинете MAX на этот URL (будут ошибки доставки).

---

## План деплоя (порядок)

### 0. Подготовка

- Зафиксировать текущий коммит на проде: `git rev-parse HEAD`.
- Бэкап БД (pg_dump) **до** `alembic upgrade`.
- Убедиться, что в репозитории на проде известен **head** миграций и есть ревизия с `messenger_accounts` и др. (`20260317_max_phase1` и всё до неё по цепочке).

### 1. Dev: «потушить» MAX (один токен)

Цель: на деве перестать дергать MAX API и не конкурировать с продом за webhook.

В `.env` / `docker-compose.dev.yml` на **dev**:

- Убрать или закомментировать **`MAX_BOT_TOKEN`** (или задать пустым), **и/или**
- **`MAX_FEATURES_ENABLED=false`**

Затем перезапуск сервисов, где читается конфиг MAX (как минимум **`web`**, при необходимости **`bot`**, **`celery_worker`**, **`celery_beat`** — по факту использования `settings` / MaxClient в коде).

Опционально: в кабинете MAX **удалить/сменить webhook** с dev-URL (если он был зарегистрирован), чтобы не оставалось указателя на старый домен.

### 2. Prod: код + миграции

- `git pull` (нужная ветка).
- В каталоге проекта:  
  `docker compose -f docker-compose.prod.yml exec web alembic upgrade head`  
  (или принятый у вас способ миграций; **не** через произвольный контейнер без БД).

### 3. Prod: переменные окружения (`web` и при необходимости остальные)

В **прод** `.env` (и при необходимости продублировать в `environment:` в `docker-compose.prod.yml`, если переменные не пробрасываются из `.env`):

| Переменная | Значение |
|------------|----------|
| `MAX_BOT_TOKEN` | единственный боевой токен |
| `MAX_WEBHOOK_BASE_URL` | `https://max.staffprobot.ru` (без слэша в конце) |
| `MAX_WEBHOOK_PATH` | по умолчанию `/max/webhook` (если не меняли) |
| `MAX_FEATURES_ENABLED` | `true` |

Итоговый URL для регистрации у MAX: **`https://max.staffprobot.ru/max/webhook`**.

Сейчас в `docker-compose.prod.yml` у **`web`** нет явного проброса `MAX_*` — их нужно **обязательно** добавить в `env_file` / `environment`, иначе на проде `MAX_BOT_TOKEN` может быть пустым.

### 4. Prod: nginx (только StaffProBot)

Файл в репозитории-ориентире: `deployment/nginx/staffprobot.conf`. На сервере править **тот файл**, который реально подключён в `sites-enabled` для staffprobot (не смешивать с конфигами цветутцветы / cvetbuket).

Добавить **отдельный** `server` для `max.staffprobot.ru`:

- `listen 443 ssl http2` + сертификаты для `max.staffprobot.ru` (или wildcard).
- HTTP → редирект на HTTPS (как у остальных сайтов), плюс `/.well-known/acme-challenge/` для выпуска сертификата.
- Минимальный `location`:

```nginx
location = /max/webhook {
    proxy_pass http://127.0.0.1:8001/max/webhook;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
}
```

Не проксировать весь `/` на прод в этот же `server`, если не нужно публично светить остальной сайт с другого имени хоста.

Проверка конфига: `nginx -t`, затем `systemctl reload nginx` (или ваш процесс).

**Важно:** в `staffprobot.conf` в репозитории есть блок `http { ... }` в конце — на реальном сервере зоны `limit_req` обычно задаются в **главном** `nginx.conf`. Не копировать ошибочно вложенный `http` внутрь `server`; править по факту рабочей схемы на сервере.

### 5. Поднять контейнеры

- `docker compose -f docker-compose.prod.yml up -d --build` (или ваш регламент: build + up).
- Обязательно перезапустить **`web`** после смены `.env` / nginx.

### 6. Зарегистрировать webhook у MAX

- Скрипт: `scripts/setup_max_webhook.py` (из контейнера `web` или с хоста с теми же env), **или** ручной вызов API MAX.
- Убедиться, что снаружи доступен **`https://max.staffprobot.ru/max/webhook`** (curl POST с тестовым телом / логи web).

### 7. Смоки

Чеклист из `doc/plans/max-rollout-runbook.md`: `/start` в MAX, привязка из ЛК, при необходимости группы отчётов, tasks v2.

---

## План отката при поломке

### Уровень 1 — быстро выключить MAX, не откатывая код

1. На проде в `.env`: **`MAX_FEATURES_ENABLED=false`**.
2. Перезапуск: **`web`**, **`celery_worker`**, **`celery_beat`**, **`bot`** (если где-то дергается MaxClient / те же флаги).
3. В кабинете MAX: **удалить webhook** или указывать заглушку (чтобы не слали на ваш URL).
4. В ЛК владельцев: выключить канал MAX в уведомлениях / группах отчётов (как в runbook).

Telegram (`bot.staffprobot.ru/webhook`) и основной сайт при этом **не зависят** от нового `server_name max.staffprobot.ru`.

### Уровень 2 — откат кода

- `git checkout <предыдущий_хэш>` + пересборка образов / `up -d`.
- Миграции БД **назад** крутить только осознанно: если уже появились строки в `messenger_accounts`, `downgrade` может удалить таблицы — заранее бэкап и решение, нужен ли откат схемы.

### Уровень 3 — nginx

- Удалить или закомментировать `server { server_name max.staffprobot.ru; ... }`, `nginx -t`, `reload`.

### Уровень 4 — токен обратно на dev

- После стабилизации прода: вернуть `MAX_BOT_TOKEN` на dev **только если** снова нужен второй стенд; иначе оставить выключенным, чтобы не пересекаться с продом.

---

## Контрольный список «не сломать соседей»

- Правки только в конфиге, который обслуживает **staffprobot.ru** / его поддомены.
- Не менять `server_name` и `root` проектов **cvetbuket.com** и **цветутцветы.рф**.
- Новый vhost — **изолированный** `max.staffprobot.ru`.

---

## Ссылки

- Общий runbook: `doc/plans/max-rollout-runbook.md`
- Готовый vhost MAX (подключать на сервере после certbot): `deployment/nginx/max.staffprobot.ru.conf`
- Шаблон nginx (полный): `deployment/nginx/staffprobot.template.conf`
- Текущий снимок прод-nginx в репо: `deployment/nginx/staffprobot.conf`
