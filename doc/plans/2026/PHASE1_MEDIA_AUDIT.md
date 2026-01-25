# Фаза 1 restruct1: техаудит MediaOrchestrator и медиа

**Дата:** 2026-01-25  
**Ветка:** `plan/restruct1`  
**План:** [restruct1.md](restruct1.md)

---

## 1. Места использования MediaOrchestrator

| Место | Файл | Контекст | Действия |
|-------|------|----------|----------|
| Отмена смены (начало потока) | `schedule_handlers.py` ~694 | `context_type="cancellation_doc"`, `context_id=shift_id` | `begin_flow`, затем `UserStep.INPUT_PHOTO` |
| Отмена смены (добавление фото) | `schedule_handlers.py` ~762 | — | `add_photo(telegram_id, file_id)` |
| Отмена смены (отмена потока) | `shift_handlers.py` ~2330 | — | `cancel(user_id)` |
| Отмена смены (ожидание фото) | `shift_handlers.py` ~2612, ~2749 | — | `get_flow(user_id)` для проверки состояния |
| Tasks v2 (начало потока) | `shift_handlers.py` ~2280 | `context_type` из задачи, `context_id=entry_id` | `begin_flow` |
| Tasks v2 (финиш) | `core_handlers.py` ~325, ~415; `shift_handlers.py` ~2525 | — | `get_flow` → логика сохранения, затем явно не вызывается `finish` в одном из путей (см. код) |

**Итого:** отмены смен (`cancellation_doc`) и Tasks v2 (task_proof / и т.п.). Инциденты (`incident_evidence`) в оркестраторе не используются — только `Incident.evidence_media_ids` в сервисе.

---

## 2. Форматы данных

### 2.1. MediaOrchestrator (Redis)

- **Ключ:** `media_flow:{user_id}`, TTL 1 ч.
- **Значение:** JSON `MediaFlowConfig`: `user_id`, `context_type`, `context_id`, `require_text`, `require_photo`, `max_photos`, `allow_skip`, `collected_text`, `collected_photos`.
- **`collected_photos`:** список **Telegram `file_id`** (строка). Никаких URL или key хранилища пока нет.

### 2.2. TaskEntryV2.completion_media

- **Тип:** JSON, nullable.
- **Формат:** `[{"url": "https://t.me/c/.../message_id", "type": "photo"|"video", "file_id": "..."}]`
- **Источник URL:** ссылки на сообщения в группе отчётов после `_send_multiple_media_to_group`. Файлы в Object Storage не сохраняются.
- **Где задаётся:** `shift_handlers._finish_task_v2_media_upload` → сохранение в `TaskEntryV2`.

### 2.3. ShiftCancellation

- **Медиа:** только `document_description` (Text) — описание справки. Фото из MediaOrchestrator при отмене **не пишутся** в БД: они отправляются в группу отчётов, но в `ShiftCancellationService.cancel_shift` передаётся лишь `document_description`. Медиа-файлы отмен нигде не хранятся.

### 2.4. Incident.evidence_media_ids

- **Тип:** Text (JSON list of IDs). В коде — заглушка, фактически не используется в MediaOrchestrator.

### 2.5. ReviewMedia (эталон для shift_cancellation_media)

- `review_id`, `file_type`, `file_path`, `file_size`, `mime_type`, `is_primary`, `created_at`.

---

## 3. Точки интеграции для MediaStorageClient

1. **Tasks v2:** при `finish` потока — вместо только «отправить в TG + сохранить t.me URL» опционально загружать в хранилище; в `completion_media` хранить либо `key`/`url` из хранилища, либо TG (в зависимости от настроек owner).
2. **Отмены смен:** передавать собранные медиа в `ShiftCancellationService`, сохранять в **`shift_cancellation_media`** (новая таблица по аналогии с `ReviewMedia`). По плану — отказ от `document_description` в пользу медиа.
3. **Инциденты:** при появлении потока `incident_evidence` — писать в хранилище и обновлять `evidence_media_ids` или аналог (согласовать формат).
4. **Договоры:** папка `contracts/{contract_id}/` — использование в Фазе 2 и при KEDO.

---

## 4. Оценка объёма данных

**Dev (на 2026-01-25):**

| Метрика | Значение |
|---------|----------|
| TaskEntryV2 с completion_media | 583 |
| ShiftCancellation с document_description | 0 |
| Incident с evidence_media_ids | 0 |
| ReviewMedia | 0 |

Для prod при необходимости выполнить те же запросы. Существующие медиа в TG по плану **не мигрируем**; новые — в Object Storage.

---

## 5. Выводы

- **MediaOrchestrator** хранит только Telegram `file_id`. Загрузки в S3/MinIO пока нет.
- **Tasks v2:** медиа сохраняются как ссылки на посты в TG-группе + `file_id`.
- **Отмены:** медиа собираются, но в БД не попадают. Нужны таблица `shift_cancellation_media` и доработка бота + `ShiftCancellationService`.
- **Инциденты:** поле есть, оркестратор не задействован.
- Для Фазы 1 критичны: доработка оркестратора под MediaStorageClient, смена формата хранения отмен (таблица + сохранение медиа), shared-страница отмены, опция хранилища и биллинг.

---

## 6. Фаза 1.2 (сделано): MinIO, .env, фабрика

- **MinIO:** сервис в `docker-compose.dev.yml`, порты 9000 (API) и 9001 (Console). Том `minio_dev_data`.
- **Переменные:** `MEDIA_STORAGE_PROVIDER` (telegram | minio | selectel), `MINIO_*`, `SELECTEL_*`, `MEDIA_PRESIGNED_EXPIRES_SECONDS`. В `core.config.settings` и в env web/bot/celery.
- **Фабрика:** `shared/services/media_storage/factory.get_media_storage_client()`. Реализации клиентов — Фаза 1.3; пока вызов поднимает `NotImplementedError`.
- **Бакет:** `scripts/ensure_minio_bucket.sh` создаёт `staffprobot-media` в MinIO (mc в one-off контейнере). Запускать после `docker compose up`.

---

## 7. Связанные файлы

- `shared/services/media_orchestrator.py`
- `apps/bot/handlers_div/shift_handlers.py` (Tasks v2, отмена)
- `apps/bot/handlers_div/schedule_handlers.py` (отмена)
- `apps/bot/handlers_div/core_handlers.py` (Tasks v2)
- `shared/services/shift_cancellation_service.py`
- `shared/services/task_service.py`
- `domain/entities/task_entry.py`, `shift_cancellation.py`, `review.py`, `incident.py`
- `shared/services/media_storage/` (фабрика), `core/config/settings.py` (медиа-настройки), `scripts/ensure_minio_bucket.sh`
