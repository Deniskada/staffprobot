# Настройка S3-совместимого хранилища (reg.ru, Cloud.ru, AWS и др.)

Провайдер **s3** — универсальный: подходит любому S3-совместимому сервису.  
Раньше использовался отдельно Selectel; теперь один набор переменных для всех.

## Переменные окружения

```bash
MEDIA_STORAGE_PROVIDER=s3
S3_ENDPOINT=https://...        # URL API хранилища
S3_ACCESS_KEY=...              # Access Key / Key ID
S3_SECRET_KEY=...              # Secret Key / Secret
S3_BUCKET=...                  # Имя бакета
S3_REGION=us-east-1            # Опционально. По умолчанию us-east-1; для reg.ru/Cloud.ru можно не менять.
```

**S3_REGION:** для reg.ru, Cloud.ru и многих S3-совместимых провайдеров можно оставить `us-east-1` или не задавать (подставится по умолчанию). Менять имеет смысл только для AWS с региональными бакетами.

## reg.ru (объектное хранилище S3)

1. **Панель reg.ru** → Объектное хранилище S3 (или VPS/облако с S3).
2. **Создать бакет** — запомнить имя.
3. **Ключи доступа** — создать API-ключ (Access Key + Secret Key).  
   Обычно: «Управление» → «Ключи доступа» / «API-ключи».
4. **Endpoint** — указывается в панели или в справке.  
   Часто: `https://s3.cloud.ru` (Cloud.ru) или адрес из документации reg.ru.  
   Если выдали только хост — используйте `https://<хост>`.
5. В `.env`:

```bash
MEDIA_STORAGE_PROVIDER=s3
S3_ENDPOINT=https://s3.cloud.ru
S3_ACCESS_KEY=<ваш_access_key>
S3_SECRET_KEY=<ваш_secret_key>
S3_BUCKET=<имя_бакета>
S3_REGION=us-east-1
```

Точный endpoint и раздел с ключами см. в актуальной справке reg.ru по объектному хранилищу.

## Другие провайдеры

| Провайдер   | Endpoint (пример)        | Примечание                          |
|-------------|--------------------------|-------------------------------------|
| Cloud.ru    | `https://s3.cloud.ru`    | Регион при необходимости            |
| AWS         | `https://s3.amazonaws.com` | Указать регион в `S3_REGION`      |
| Selectel    | `https://s3.selcdn.ru`   | `S3_REGION=ru-1`                    |
| MinIO (dev) | `http://minio:9000`      | Использовать провайдер `minio`      |

## Проверка

После настройки перезапустите web/bot/celery. При включённой опции «Защищённое хранилище» и выборе «хранилище» или «оба» загрузка пойдёт в указанный S3-бакет.

### Проверка загрузки настроек на проде

Убедитесь, что в `.env` есть все переменные (в т.ч. `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`). В `docker-compose.prod` для сервисов web, bot, celery_worker, celery_beat указан `env_file: .env`, иначе контейнеры их не получают.

Проверка из контейнера web:

```bash
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec -T web python -c "
from core.config.settings import settings
from shared.services.media_storage import get_media_storage_client

p = (settings.media_storage_provider or \"\").strip().lower()
print(\"MEDIA_STORAGE_PROVIDER:\", p)
print(\"S3_ENDPOINT:\", \"SET\" if settings.s3_endpoint else \"MISSING\")
print(\"S3_ACCESS_KEY:\", \"SET\" if settings.s3_access_key else \"MISSING\")
print(\"S3_SECRET_KEY:\", \"SET\" if settings.s3_secret_key else \"MISSING\")
print(\"S3_BUCKET:\", settings.s3_bucket or \"MISSING\")
print(\"S3_REGION:\", settings.s3_region or \"us-east-1\")
if p == \"s3\" and all([settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key, settings.s3_bucket]):
    c = get_media_storage_client(provider_override=\"s3\")
    print(\"S3 client: OK\")
else:
    print(\"S3 client: skip (config incomplete or provider != s3)\")
"'
```

Если всё «SET» и «S3 client: OK» — настройки загрузились и клиент создаётся.
