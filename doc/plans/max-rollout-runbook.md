# Runbook: выкладка MAX (StaffProBot)

Краткий чеклист перед/после включения MAX на стенде или проде.

**Первый выклад на прод** (один токен, dev/prod, nginx `max.staffprobot.ru`, откат): см. `doc/plans/max-prod-deploy-rollback.md`.

## Переменные окружения

- `MAX_BOT_TOKEN` — токен бота в [platform-api.max.ru](https://platform-api.max.ru).
- `MAX_WEBHOOK_BASE_URL` — публичный HTTPS origin (без trailing slash); полный URL вебхука = base + путь из `MAX_WEBHOOK_PATH` (по умолчанию `/max/webhook`, см. `core/config/settings.py`).
- `MAX_FEATURES_ENABLED` — `true` по умолчанию. Установите `false` для быстрого отката: вебхук отвечает 503, исходящие вызовы MAX (группы отчётов, личные уведомления, `MaxClient`) не выполняются.
- Web-сервис должен быть доступен из интернета по этому URL (firewall / reverse proxy).

## После деплоя

1. **Web:** при `docker compose ... up -d` контейнер `web` пересоздаётся и подхватывает код. Если на проде обновляли только смонтированные шаблоны/статику **без** пересборки образа — выполните `docker compose -f docker-compose.prod.yml restart web`, чтобы процесс веб-сервера перечитал файлы.
2. Зарегистрировать webhook у MAX (скрипт или ручной вызов API) — см. `scripts/setup_max_webhook.py` при наличии.
3. Проверить личный чат: `/start` в MAX, привязка аккаунта (как в ЛК).
4. Группа отчётов: в объекте задан `max_report_chat_id`, в ЛК владельца включён канал MAX для «групп отчётов».
5. Tasks v2 с фото: в карточке смены `/owner/shifts/{id}?shift_type=shift` — блок Tasks v2 и ссылки **Telegram** / **MAX** при наличии `completion_media[].delivery`.

## Откат

- **`MAX_FEATURES_ENABLED=false`** в окружении `web` (и при необходимости `bot`/`celery`), затем `restart` соответствующих контейнеров — полная остановка исходящего MAX и приёма вебхука.
- Выключить канал MAX в настройках уведомлений владельца (группы отчётов) — отчёты пойдут только в TG при настроенном TG-чате.
- При необходимости удалить webhook у MAX и оставить только Telegram-бота (polling/webhook TG без изменений в этом runbook).

## Отладка

- Уровень логов **DEBUG** для `MaxClient`: после успешного `POST /messages` пишется превью тела ответа (`preview`, до ~1200 символов) — сверка с `_max_api_public_link`.

## Инвентаризация кода (legacy vs targets)

Сводная таблица и команды `rg`: `doc/plans/max-legacy-inventory.md`. Перед релизом имеет смысл прогнать смоки из раздела «После деплоя» и при расширении функционала — обновить инвентаризацию.
