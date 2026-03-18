## Руководство: как добавить MAX-бота в StaffProBot (с 1 кодовой базой)

Цель: сделать так, чтобы логика (команды, FSM, права, валидации) была **одна**, а вход/выход — через разные транспорта:
- Telegram: `python-telegram-bot` (у вас уже есть)
- MAX: `platform-api.max.ru` (webhook JSON + HTTP отправка)

Паттерн взят из `cvetbuket.com`: `Adapter -> NormalizedUpdate -> BotHandler`.

---

### 0) Что НЕ делаем

- Не копируем/форкаем обработчики под MAX.
- Не «прячем» различия через if-ы по всей логике.

Вся разница должна жить в **адаптерах** и в **фиче‑флагах** (`supports_webapp`, `supports_contact_request`).

---

### 1) Выделить общий слой бизнес-логики

Сейчас в `staffprobot` обработчики сильно завязаны на `telegram.Update`.
Нужно выделить слой, который работает с DTO и абстрактным Messenger.

Рекомендованная структура (минимально инвазивно):

```
apps/bot_unified/
  normalized_update.py
  messenger.py
  router.py
  tg_adapter.py
  max_adapter.py
  max_client.py
```

Где:
- `router.py` — общий «BotHandler» (принимает `NormalizedUpdate`, вызывает доменные сервисы и шлёт ответы через `Messenger`)
- `tg_adapter.py` — парсинг `telegram.Update` → `NormalizedUpdate` + thin wrapper отправки
- `max_adapter.py` — парсинг webhook JSON MAX → `NormalizedUpdate`
- `max_client.py` — отправка сообщений в MAX HTTP API

---

### 2) NormalizedUpdate

Возьмите шаблон из `templates/python/normalized_update.py`.

Минимальный контракт, который нужен почти всем ботам:
- `type: message|callback`
- `chat_id`
- `text`
- callback поля: `callback_data`, `callback_id`
- optional: `from_username`, `contact_phone`, `location`, `photo_file_id`/`photo_url`

Важно: DTO должен быть **стабильным** (не тащить телеграм-объекты).

---

### 3) Messenger интерфейс

Возьмите шаблон из `templates/python/messenger.py`.

Один важный нюанс: клавиатуры стоит передавать в **логическом формате**, чтобы оба транспорта могли их рендерить по-своему.

Рекомендованный логический формат кнопок (как в `cvetbuket.com`):

```
[
  [ {"text": "...", "callback_data": "..."}, {"text": "...", "url": "https://..."} ],
  [ {"text": "...", "callback_data": "..."} ]
]
```

Адаптеры делают рендеринг:
- TG: inline_keyboard / reply_keyboard
- MAX: inline_keyboard attachment (url/callback), без webapp

---

### 4) TelegramAdapter для StaffProBot

Вариант А (самый быстрый): оставить текущий `python-telegram-bot`, но добавить «мост»:
- На входе `Update` → `NormalizedUpdate`
- На выходе использовать `context.bot`/`update.effective_chat` для отправки.

Где внедрять:
- в точке маршрутизации апдейтов (см. `apps/bot/bot.py`, где собирается `Application` и регистрируются handlers).

Цель: сделать так, чтобы существующие хендлеры могли постепенно мигрировать в `router.py`.

---

### 5) MAX webhook endpoint

В StaffProBot добавьте endpoint:
- `POST /max/webhook` (путь в env)

На входе:
- получаете raw JSON
- превращаете через `MaxAdapter.parse_update(raw)` → `NormalizedUpdate`
- вызываете общий `router.handle(update, messenger=max_messenger)`

Критично:
- `bot_started` конвертируйте в текст `"/start"` или `"/start payload"` — это позволяет переиспользовать одну ветку /start.

---

### 6) MAX client (отправка сообщений)

MAX API из референса (`cvetbuket.com/bot/MaxAdapter.php`):
- базовый URL: `https://platform-api.max.ru`
- токен: `access_token` передаётся в query string
- отправка текста: `POST /messages?chat_id=...`
- callback ack: `POST /answers?callback_id=...` (тело не должно быть пустым)
- фото: `POST /uploads?type=image` → upload → attach token в message

Вынесите HTTP‑вызовы в `max_client.py`.

---

### 7) Где MAX отличается (и как не сломать UX)

- **Нет WebApp**: если вы используете WebApp-кнопки в TG — для MAX нужен fallback на ввод текста/ссылку.
- **Нет request_contact**: вместо кнопки «поделиться номером» — просите ввести номер вручную + валидация.
- **Клавиатуры**: MAX — attachment inline_keyboard. Reply keyboard как в TG нет.

Именно поэтому нужны `features` у Messenger.

---

### 8) Тестирование (минимум)

Сделайте 2 smoke‑теста:
- `test_tg_parse_update()` — `Update` → `NormalizedUpdate` (message/callback)
- `test_max_parse_update()` — JSON → `NormalizedUpdate` (message_created/message_callback/bot_started)

Цель тестов — защитить контракт DTO.

---

### 9) Конфиги/секреты

Рекомендованные env:
- `TELEGRAM_BOT_TOKEN`
- `MAX_BOT_TOKEN`
- `MAX_WEBHOOK_PATH`

