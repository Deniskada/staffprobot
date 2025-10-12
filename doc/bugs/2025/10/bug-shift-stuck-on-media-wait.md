# Bug: Смена застревает при ожидании медиа-отчета

**ID:** bug-shift-stuck-on-media-wait  
**Дата обнаружения:** 2025-10-12  
**Статус:** ✅ Исправлено  
**Приоритет:** Критичный  
**Теги:** `bot`, `object-closure`, `shift-closure`, `business-logic`

---

## 🐛 Симптомы

При использовании "🔒 Закрыть объект" смена остается в статусе "active":

```sql
-- После закрытия объекта смена все еще active:
SELECT id, status FROM shifts WHERE id = 91;
-- id: 91, status: active ❌

-- Объект закрыт:
SELECT closed_at FROM object_openings WHERE id = 10;
-- closed_at: 2025-10-12 01:21:38 ✅

-- Но пользователь не может открыть новую смену:
-- "❌ У вас уже есть активная смена"
```

**В UI:** Объект показывается как закрытый, но смена - как активная.

---

## 🔍 Воспроизведение

1. Открыть объект через "🏢 Открыть объект"
2. Нажать "🔒 **Закрыть объект**" (не "Закрыть смену"!)
3. Отправить геопозицию
4. **Результат:** 
   - ✅ Бот показывает "Объект закрыт!"
   - ❌ Смена остается в статусе "active"
   - ❌ Пользователь заблокирован

**Фактическая последовательность (из логов):**
```
01:21:12 - Нажата кнопка "close_object"
01:21:16-31 - Задачи отмечены как выполненные
01:21:33 - "close_shift_with_tasks:91"
01:21:38 - Медиа загружено, геопозиция получена
01:21:38 - "✅ Объект закрыт!" ← Только объект!
01:21:50 - /start (главное меню)
01:21:52 - "open_object" → "❌ У вас уже есть активная смена"
```

---

## 🔧 Корень проблемы

**Файл:** `apps/bot/handlers_div/core_handlers.py:516-551` (СТАРАЯ ВЕРСИЯ)

**Последовательность событий:**
1. Пользователь нажал "🔒 Закрыть объект"
2. Бот вызвал `_handle_close_shift` для обработки задач и медиа
3. Медиа загружено, геопозиция получена
4. `handle_location` обработал событие `UserAction.CLOSE_OBJECT`
5. **ПРОБЛЕМА:** Код закрыл ТОЛЬКО объект:
   ```python
   opening = await opening_service.close_object(...)
   ```
6. ❌ Смена НЕ закрыта! Осталась в статусе "active"

**Старый код (516-551):**
```python
elif user_state.action == UserAction.CLOSE_OBJECT:
    # Закрытие объекта после успешного закрытия смены
    
    # ... получение пользователя ...
    
    opening = await opening_service.close_object(
        object_id=user_state.selected_object_id,
        user_id=db_user.id,
        coordinates=coordinates
    )
    # ❌ СМЕНА НЕ ЗАКРЫТА!
    
    await update.message.reply_text("✅ Объект закрыт!")
```

**Проблема:** 
- Закрывался только `object_opening`
- `Shift` оставалась в статусе "active"
- Пользователь видел "Объект закрыт", но не мог открыть новый

---

## ✅ Решение

**Файл:** `apps/bot/handlers_div/core_handlers.py:516-572` (НОВАЯ ВЕРСИЯ)

### СНАЧАЛА закрыть смену, ПОТОМ объект:

```python
elif user_state.action == UserAction.CLOSE_OBJECT:
    # Закрытие объекта - СНАЧАЛА закрываем смену, ПОТОМ объект
    from shared.services.object_opening_service import ObjectOpeningService
    from domain.entities.user import User
    
    # 1. Закрыть смену ✅
    result = await shift_service.close_shift(
        user_id=user_id,
        shift_id=user_state.selected_shift_id,
        coordinates=coordinates
    )
    
    if not result['success']:
        await update.message.reply_text(
            f"❌ Ошибка при закрытии смены: {result.get('error', 'Неизвестная ошибка')}"
        )
        user_state_manager.clear_state(user_id)
        return
    
    # 2. Закрыть объект ✅
    async with get_async_session() as session:
        opening_service = ObjectOpeningService(session)
        # ... получение пользователя ...
        
        opening = await opening_service.close_object(
            object_id=user_state.selected_object_id,
            user_id=db_user.id,
            coordinates=coordinates
        )
        
        # Объединенное сообщение о смене И объекте
        await update.message.reply_text(
            f"✅ <b>Смена и объект закрыты!</b>\n\n"
            f"⏱️ Время смены: {result['hours']:.1f}ч\n"
            f"💰 Оплата: {result['payment']:.0f}₽\n"
            f"⏰ Объект закрыт в: {close_time}\n"
            f"⏱️ Время работы объекта: {opening.duration_hours:.1f}ч",
            parse_mode='HTML'
        )
```

**Ключевые изменения:**
1. ✅ **Шаг 1:** Вызов `shift_service.close_shift()` - закрывает смену
2. ✅ **Шаг 2:** Вызов `opening_service.close_object()` - закрывает объект
3. ✅ Показывается **объединенная** информация о смене и объекте

---

## 📦 Коммит

```
commit c426d23
Исправление закрытия смены при 'Закрыть объект'

Проблема: флоу 'Закрыть объект' закрывал только объект, смена оставалась active

Решение:
1. СНАЧАЛА закрываем смену (shift_service.close_shift)
2. ПОТОМ закрываем объект (opening_service.close_object)
3. Показываем объединенную информацию о смене и объекте

Теперь после 'Закрыть объект' смена корректно закрывается
```

---

## 🧪 Тестирование

**До исправления:**
```sql
-- После "Закрыть объект":
SELECT id, status FROM shifts WHERE id = 91;
-- status: active ❌

SELECT closed_at FROM object_openings WHERE object_id = 9 AND closed_at IS NOT NULL;
-- closed_at: 2025-10-12 01:21:38 ✅

-- Пользователь: "❌ У вас уже есть активная смена"
```

**После исправления:**
```sql
-- После "Закрыть объект":
SELECT id, status FROM shifts WHERE id = 92;
-- status: completed ✅

SELECT closed_at FROM object_openings WHERE object_id = 9 AND closed_at IS NOT NULL;
-- closed_at: 2025-10-12 01:30:XX ✅

-- Пользователь может открыть новую смену ✅
```

**Hotfix для смены 91:**
```sql
UPDATE shifts 
SET status = 'completed', end_time = NOW(),
    total_hours = EXTRACT(EPOCH FROM (NOW() - start_time)) / 3600,
    total_payment = (EXTRACT(EPOCH FROM (NOW() - start_time)) / 3600) * hourly_rate
WHERE id = 91;
-- Применен вручную
```

---

## 📚 Связанные задачи

- Phase 4B: Media Reports Implementation
- Bug: Media report link не открывается
- User State Management

---

## 💡 Lessons Learned

1. **Блокировка UI:** Кнопки должны быть недоступны, пока не выполнены обязательные условия
2. **Валидация:** Всегда проверять pre-conditions перед критичными операциями
3. **Recovery:** Нужен механизм автоматической очистки застрявших сущностей
4. **UX:** Четкие подсказки пользователю о текущем шаге и ожиданиях

---

## 🔗 См. также

- `apps/bot/handlers_div/shift_handlers.py` - обработка закрытия смены с задачами
- `apps/bot/handlers_div/core_handlers.py` - обработка location
- `core/state/user_state_manager.py` - управление состоянием

