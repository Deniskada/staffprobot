# Owner Profile Autosave (Итерация 31)

## Обзор
Система автоматического сохранения полей профиля владельца без необходимости нажимать кнопку "Сохранить".

## Изменённые файлы

### Backend

#### `apps/web/routes/owner.py`
- **Добавлено:** `POST /owner/profile/api/autosave`
  - Роль: owner
  - Назначение: JSON API для автосохранения отдельных полей профиля
  - Тело запроса: `{about_company?, values?, contact_phone?, contact_messengers?, photos?}`
  - Ответ: `{success: bool, profile_id?: int, error?: str}`

#### `apps/web/services/tag_service.py`
- **Добавлено:** `async def update_owner_profile_fields(session, user_id, fields) -> OwnerProfile`
  - Частичное обновление полей профиля
  - Поддерживаемые поля: `about_company`, `values`, `contact_phone`, `contact_messengers`, `photos`
  - Авто-создание профиля, если отсутствует

#### `shared/services/system_features_service.py`
- **Изменено:** `async def toggle_user_feature(...)`
  - Авто-создание `OwnerProfile` при отсутствии
  - По умолчанию включается `telegram_bot`
  - Логирование: "Owner profile auto-created for user X with default ['telegram_bot']"

### Frontend

#### `apps/web/templates/owner/profile/index.html`
**JavaScript добавления:**
- `scheduleAutosave(payload)` - планирует автосохранение с debounce 600мс
- `doAutosave(extra)` - выполняет POST запрос к `/owner/profile/api/autosave`
- `initAutosaveBindings()` - привязывает события к полям:
  - `textarea[name="about_company"]` → `input` event
  - `textarea[name="values"]` → `input` event
  - `#contact_phone` → `input` event
  - `.messenger-check` → `change` event

## Поведение

### Автосохранение текстовых полей
1. Пользователь вводит текст в "О компании" / "Ценности" / "Телефон"
2. Через 600мс после последнего изменения отправляется запрос
3. Поле сохраняется на бэкенде без перезагрузки страницы
4. При ошибке выводится console.warn (без блокировки UI)

### Автосохранение мессенджеров
1. Пользователь изменяет чекбокс WhatsApp/Telegram/MAX
2. Немедленно обновляется hidden input `contactMessengersData`
3. Запрос отправляется мгновенно (без debounce)
4. Массив мессенджеров сохраняется: `["whatsapp", "telegram"]`

### Авто-создание профиля
1. Пользователь переключает функцию в "Дополнительные функции"
2. Если `OwnerProfile` не существует:
   - Создаётся новый профиль
   - Устанавливается `enabled_features = ["telegram_bot"]`
3. Иначе обновляется существующий профиль
4. Redis кэш инвалидируется автоматически

## Технические детали

### Debounce Logic
```javascript
let autosaveTimer = null;
function scheduleAutosave(payload) {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => doAutosave(payload), 600);
}
```

### API Request
```javascript
async function doAutosave(extra) {
    const resp = await fetch('/owner/profile/api/autosave', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(extra)
    });
    const data = await resp.json();
    if (!data.success) console.warn('Автосохранение не удалось:', data.error);
}
```

### Backend Service
```python
async def update_owner_profile_fields(
    self, session: AsyncSession, user_id: int, fields: Dict[str, Any]
) -> OwnerProfile:
    profile = await self.get_owner_profile(session, user_id)
    if not profile:
        profile = OwnerProfile(user_id=user_id)
        session.add(profile)
    
    allowed_keys = {'about_company', 'values', 'contact_phone', 
                    'contact_messengers', 'photos'}
    for key in allowed_keys:
        if key in fields:
            setattr(profile, key, fields[key])
    
    await session.commit()
    await session.refresh(profile)
    return profile
```

## Безопасность

### Валидация полей
- Только белый список полей: `about_company`, `values`, `contact_phone`, `contact_messengers`, `photos`
- Аутентификация через `require_owner_or_superadmin`
- Проверка принадлежности профиля через `user_id`

### Защита от race conditions
- SQLAlchemy MVCC изоляция (PostgreSQL)
- Последний запрос побеждает (last-write-wins)
- Потеря данных маловероятна из-за debounce

## Мониторинг и отладка

### Логи
```
INFO - Owner profile auto-created for user 123 with default ['telegram_bot']
INFO - Profile saved for user 123: 0 tags, 0 values
ERROR - Error autosaving profile: <error message>
```

### Метрики для мониторинга
- Частота вызовов `/owner/profile/api/autosave`
- Средняя задержка автосохранения
- Процент ошибок автосохранения

## Тестирование

### Ручное тестирование
1. Открыть `/owner/profile`
2. Ввести текст в "О компании" → должно сохраниться через ~1 сек
3. Изменить чекбокс мессенджера → должно сохраниться моментально
4. Перезагрузить страницу → данные должны сохраниться
5. Включить/выключить функцию → не должно быть ошибки "Owner profile not found"

### Автоматическое тестирование
```bash
# Проверка API
curl -X POST http://localhost:8001/owner/profile/api/autosave \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"about_company": "Test company"}'
```

## Известные ограничения

1. **Отсутствие UI-индикатора сохранения:**
   - Пользователь не видит, когда данные сохраняются
   - Планируется добавить spinner/галочку в будущем

2. **Нет валидации на клиенте:**
   - Ошибки валидации обрабатываются только на бэкенде
   - При ошибке данные не сохраняются, но пользователь не уведомлён

3. **Фотографии через URL:**
   - Загрузка файлов ещё не реализована
   - Текущая версия работает только с URL

## Дальнейшие улучшения

1. Добавить UI-индикатор состояния сохранения
2. Реализовать валидацию на клиенте (макс. длина, формат телефона)
3. Добавить возможность загрузки файлов для фотографий
4. Реализовать offline-режим с синхронизацией при восстановлении связи
5. Добавить undo/redo для критичных изменений

## Ссылки

- [Roadmap Итерация 31](/doc/plans/roadmap.md#итерация-31-owner-profile-enhancement)
- [Owner Routes Documentation](/doc/vision_v1/roles/owner.md)
- [System Features Service](/doc/vision_v1/shared/system_features.md)

