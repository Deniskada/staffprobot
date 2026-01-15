# Nginx: статика и кеш — инцидент и решение

## Симптом
- На проде панель объектов/сотрудников не отправляла XHR (`/owner/api/employees`, `/owner/calendar/api/objects`).
- В логах браузера были только сообщения календаря, но отсутствовали логи загрузки панелей.
- На деве XHR уходили и всё работало.

## Причина
- Nginx на проде отдавал статические файлы из `alias /var/www/staffprobot/static/`.
- В этой директории лежала старая копия `apps/web/static/js/shared/calendar_panels.js` без:
  - `credentials: 'same-origin'` в `fetch`
  - новых диагностических `console.log`
- Браузер грузил устаревший JS, XHR не отправлялись.

Проверка:
- `curl -s https://staffprobot.ru/static/js/shared/calendar_panels.js | grep -n "[CalendarPanels] Fetching"` — пусто (старая версия).
- `curl -s http://localhost:8001/static/js/shared/calendar_panels.js | grep -n "[CalendarPanels] Fetching"` — есть (актуальная версия из backend).

## Временный фикс (для восстановления работы)
Скопировать актуальные файлы из контейнера web в директорию, откуда обслуживает Nginx:

```bash
docker cp staffprobot_web_prod:/app/apps/web/static/js/shared/calendar_panels.js /tmp/
sudo install -m 0644 /tmp/calendar_panels.js /var/www/staffprobot/static/js/shared/calendar_panels.js

docker cp staffprobot_web_prod:/app/apps/web/static/js/shared/universal_calendar.js /tmp/
sudo install -m 0644 /tmp/universal_calendar.js /var/www/staffprobot/static/js/shared/universal_calendar.js
```

Проверка:

```bash
curl -s https://staffprobot.ru/static/js/shared/calendar_panels.js | grep -n "[CalendarPanels] Fetching"
```

## Постоянное решение (рекомендуется)
Перевести раздачу `/static/` через backend, чтобы Nginx всегда отдавал актуальные файлы из контейнера.

Изменение в `deployment/nginx/staffprobot.conf`:

```nginx
# Статические файлы (отдаются бэкендом из /static)
location /static/ {
    proxy_pass http://localhost:8001/static/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header X-Content-Type-Options nosniff;
}
```

Применение на сервере:

```bash
sudo cp /etc/nginx/sites-enabled/staffprobot.conf /etc/nginx/sites-enabled/staffprobot.conf.bak.$(date +%s)
sudo vim /etc/nginx/sites-enabled/staffprobot.conf   # заменить блок location /static/ на proxy_pass
sudo nginx -t && sudo systemctl reload nginx

# Проверить активный блок
sudo nginx -T 2>/dev/null | awk '/location \/static\//, /}/'

# Проверить, что отдается актуальный JS
curl -s https://staffprobot.ru/static/js/shared/calendar_panels.js | grep -n "[CalendarPanels] Fetching"
```

## Почему не сработала первая правка
- В конфиге был активен `alias`, и ранее правка не переписала нужный блок корректно (правки через однострочные awk/sed сложно поддерживать).
- После явной замены блока и reload — проблема исчезла.

## Рекомендации
- Избегать параллельного хранения статики вне контейнера (рассинхрон).
- Для кэш-бастинга использовать query-параметр `?v=...`, но полагаться на него только при корректной точке раздачи.
- Держать `deployment/nginx/staffprobot.conf` в репозитории источником правды и применять его на проде.

## Чек-лист проверки
- [ ] `nginx -T` показывает `location /static/ { proxy_pass http://localhost:8001/static/; ... }`
- [ ] `curl https://staffprobot.ru/static/js/shared/calendar_panels.js` содержит свежие логи
- [ ] В браузере в консоли видны логи `[CalendarPanels] Fetching ...`
- [ ] В Network уходят XHR на `/owner/api/employees` и `/owner/calendar/api/objects`


