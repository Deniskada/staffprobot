# Ручное тестирование restruct1 Фаза 1 (медиа, хранилище, биллинг)

**Ветка:** `plan/restruct1`  
**План:** [restruct1.md](../../doc/plans/2026/restruct1.md)  
**Аудит:** [PHASE1_MEDIA_AUDIT.md](../../doc/plans/2026/PHASE1_MEDIA_AUDIT.md)

---

## Подготовка

1. **Docker dev:**  
   `docker compose -f docker-compose.dev.yml up -d`  
   Убедиться, что подняты: `web`, `bot`, `postgres`, `redis`, `minio` (при тестах S3).

2. **MinIO bucket:**  
   `./scripts/ensure_minio_bucket.sh`  
   Бакет `staffprobot-media` должен существовать.

3. **Переменные (.env, dev в Docker):**

   | Переменная | Значение |
   |------------|----------|
   | `MEDIA_STORAGE_PROVIDER` | `minio` (или `telegram` для тестов без S3) |
   | `MINIO_ENDPOINT` | `http://minio:9000` |
   | `MINIO_ACCESS_KEY` | `minioadmin` |
   | `MINIO_SECRET_KEY` | `minioadmin` |

   **MinIO порты:** `9000` — S3 API (приложение подключается по `minio:9000` внутри Docker). В браузере не открывается. `9001` — MinIO Console (веб-UI): открывать `http://127.0.0.1:9001` или `http://localhost:9001` для просмотра бакетов. Логин/пароль `minioadmin`/`minioadmin`.

   Для отмен через S3 нужен `minio`. Вне Docker — `MINIO_ENDPOINT=http://localhost:9000`.

4. **Миграции:**  
   `docker compose -f docker-compose.dev.yml exec web alembic upgrade head`

5. **Данные для тестов:**  
   - Владелец (owner) с активной подпиской и тарифом, в `features` которого есть `secure_media_storage`.  
   - При необходимости добавить в тариф:  
     `UPDATE tariff_plans SET features = features || '["secure_media_storage"]'::jsonb WHERE id = N;`  
     (для `json` может понадобиться приведение через `jsonb`.)

---

## 1. Фаза 1.2–1.3: MinIO, фабрика, MediaStorageClient

| # | Действие | Ожидание |
|---|----------|----------|
| 1.1 | Проверить `.env`: `MEDIA_STORAGE_PROVIDER=minio`, `MINIO_ENDPOINT=http://minio:9000`, `MINIO_ACCESS_KEY=minioadmin`, `MINIO_SECRET_KEY=minioadmin` | Значения заданы, без ошибок при старте web/bot |
| 1.2 | Запустить `ensure_minio_bucket.sh` | Бакет `staffprobot-media` создан |
| 1.3 | Открыть MinIO Console (**http://127.0.0.1:9001** или localhost:9001). Логин: `minioadmin`, пароль: `minioadmin` | Доступ к бакету `staffprobot-media`, список объектов (пустой или с тестовыми). Не использовать `minio:9000` в браузере — это S3 API для приложения. |

---

## 2. Фаза 1.4: shift_cancellation_media, shared-страница отмены, бот

### 2.1 Shared-форма отмены

| # | Действие | Ожидание |
|---|----------|----------|
| 2.1.1 | Открыть `/shared/cancellations/form` (или редирект с `/owner/...`, `/manager/...`, `/employee/...`) | Форма с полем загрузки файлов (multiple) |
| 2.1.2 | Выбрать смену, причину отмены, приложить 1–2 файла, отправить | Успешная отправка; при `MEDIA_STORAGE_PROVIDER=minio` и настройках owner «хранилище»/«оба» — файлы в MinIO в **`cancellations/{schedule_id}/`** (например `cancellations/1692/`). В Console: бакет `staffprobot-media` → папка `cancellations` → папка с ID смены. **Где задать:** `/owner/profile` → «Настройки хранилища» → для контекста «Отмены смен» выбрать «Только хранилище (S3)» или «Оба» (сначала включить опцию в «Настройках функций»). |
| 2.1.3 | Проверить в БД: `SELECT * FROM shift_cancellation_media WHERE cancellation_id = ?` | Записи с `storage_key`, `file_type`, `mime_type` |
| 2.1.4 | **Логи:** перезапустить web после правок. Отмена с фото → смотреть `docker compose -f docker-compose.dev.yml logs web --tail 200`. Фильтр: `grep -i 'Shared cancellation'` (при пустом выводе grep выходит с кодом 1 — это не ошибка; можно добавить `\|\| true` в конец пайпа). | Строки `Shared cancellation media check` (owner_id, mode, provider, file_count), при загрузке — `uploaded to S3` с key. |

### 2.2 Бот: отмена смены с фото

| # | Действие | Ожидание |
|---|----------|----------|
| 2.2.1 | В боте начать отмену смены (если есть сценарий с фото) | Запрос фото / «Готово» / «Пропустить» |
| 2.2.2 | Добавить фото, нажать «Готово» | Отмена создаётся; при S3 — медиа в хранилище; в БД — `shift_cancellation_media` |
| 2.2.3 | Нажать «Пропустить» (без фото) | Отмена без медиа; в `shift_cancellation_media` записей нет |

---

## 3. Фаза 1.5: Опция хранилища, настройки по owner

### 3.1 Функция и UI настроек

| # | Действие | Ожидание |
|---|----------|----------|
| 3.1.1 | Залогиниться как owner. Профиль → «Перейти к настройкам функций» | Страница с переключателями функций |
| 3.1.2 | Убедиться, что в тарифе есть `secure_media_storage`. Включить «Использовать защищённое хранилище файлов» | Функция включается |
| 3.1.3 | Профиль → «Настройки хранилища» (или `/owner/profile/media-storage`) | Страница с контекстами (задачи, отмены, инциденты, договоры) и выбором: только Telegram / только хранилище / оба |
| 3.1.4 | Выключить опцию в функциях | «Настройки хранилища» показывают подсказку включить опцию |

### 3.2 API настроек хранилища

| # | Действие | Ожидание |
|---|----------|----------|
| 3.2.1 | `GET /owner/profile/media-storage/api/options` (с авторизацией owner) | `enabled`, `modes` по контекстам |
| 3.2.2 | `POST /owner/profile/media-storage/api/options` с телом `{"modes": {"tasks": "storage", "cancellations": "both"}}` | Успех; при повторном GET — соответствующие `modes` |

### 3.3 Загрузка медиа по настройкам

| # | Действие | Ожидание |
|---|----------|----------|
| 3.3.1 | У owner: опция включена; tasks = «только хранилище». Выполнить Tasks v2 с фото → «Готово» | Медиа в S3 (`tasks/{entry_id}/`), не только в TG |
| 3.3.2 | Отмены = «только Telegram». Отмена смены с фото (бот или shared) | Медиа только в TG; в S3 по отмене — ничего нового |
| 3.3.3 | Отмены = «оба». Отмена с фото | Медиа и в TG, и в S3 |

---

## 4. Фаза 1.6: Цены хранения, лог опций, учёт в биллинге

### 4.1 Поля тарифа и лог

| # | Действие | Ожидание |
|---|----------|----------|
| 4.1.1 | В БД: `SELECT id, name, price, storage_option_price FROM tariff_plans WHERE id = N` | Есть колонки `storage_option_price` и т.п. |
| 4.1.2 | Установить `storage_option_price = 100` для тестового тарифа | UPDATE выполняется |
| 4.1.3 | `SELECT * FROM subscription_option_log ORDER BY changed_at DESC LIMIT 5` | Таблица есть; при включении/выключении опции появляются записи |

### 4.2 Toggle опции → лог

| # | Действие | Ожидание |
|---|----------|----------|
| 4.2.1 | У owner активная подписка. Включить «Использовать защищённое хранилище» | В `subscription_option_log`: новая строка с `options_enabled = ["secure_media_storage"]` |
| 4.2.2 | Выключить опцию | Новая строка с `options_disabled = ["secure_media_storage"]` |

### 4.3 Расчёт суммы к оплате

| # | Действие | Ожидание |
|---|----------|----------|
| 4.3.1 | Тариф: `price = 500`, `storage_option_price = 100`. Опция **включена** у owner. Смена тарифа на него (owner) → оплата | Сумма к оплате = 600 (500 + 100) |
| 4.3.2 | Опция **выключена**. Повторить смену тарифа | Сумма = 500 |
| 4.3.3 | Админ: назначить подписку на тариф с опцией; владелец с включённой опцией. «Оплачено админом» или «требует оплаты» | Транзакция с суммой = база + 100 |
| 4.3.4 | Автопродление: подписка с опцией включена, тариф с `storage_option_price` | При создании платежа (например, через billing task) сумма = база + опция |

### 4.4 Проверка биллинга (кратко)

| # | Действие | Ожидание |
|---|----------|----------|
| 4.4.1 | Владелец: «Моя подписка» / «Выбор тарифа» | Нет ошибок; при создании платежа — корректная сумма |
| 4.4.2 | Админ: назначение подписки, создание транзакции | Сумма учитывает опцию |

---

## 5. Unit-тесты

```bash
docker compose -f docker-compose.dev.yml exec web pytest \
  tests/unit/test_billing_storage_options.py \
  tests/unit/test_owner_media_storage_service.py \
  tests/unit/test_media_orchestrator.py \
  -v
```

Все тесты должны проходить.

---

## 6. Чек-лист перед деплоем

- [ ] Миграции применены (`alembic upgrade head`)
- [ ] `secure_media_storage` есть в `system_features` и при необходимости в `tariff_plans.features`
- [ ] Unit-тесты 1.5–1.6 и media_orchestrator зелёные
- [ ] Ручные сценарии 2–4 пройдены на dev
- [ ] Переменные окружения (MinIO/Selectel) заданы на проде при использовании S3
