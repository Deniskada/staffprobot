# Матрица переходов статусов Shift и ShiftSchedule

## Стандартные статусы

### ShiftSchedule (Расписание смен)
- `planned` - запланирована (по умолчанию)
- `confirmed` - подтверждена сотрудником (legacy, практически не используется)
- `completed` - завершена (смена отработана)
- `cancelled` - отменена

### Shift (Фактическая смена)
- `active` - активна (смена открыта)
- `completed` - завершена (смена закрыта)
- `cancelled` - отменена

## Матрица переходов статусов

### ShiftSchedule → Shift синхронизация

| ShiftSchedule | Shift | Условие | Источник |
|---------------|-------|---------|----------|
| `planned` | `active` | Смена открыта из расписания | bot/web |
| `planned` | `cancelled` | Расписание отменено до открытия | bot/web/contract |
| `confirmed` | `active` | Смена открыта (legacy) | bot/web |
| `confirmed` | `cancelled` | Расписание отменено (legacy) | bot/web/contract |
| `completed` | `completed` | Смена закрыта | bot/web/celery |
| `cancelled` | `cancelled` | Расписание отменено, смена тоже отменена | bot/web/contract |

### Shift → ShiftSchedule синхронизация

| Shift | ShiftSchedule | Условие | Источник |
|-------|---------------|---------|----------|
| `active` | `planned` → `planned` | Смена открыта, расписание остается planned | bot/web |
| `active` | `confirmed` → `planned` | Смена открыта (legacy) | bot/web |
| `completed` | `planned` → `completed` | Смена закрыта, расписание завершено | bot/web/celery |
| `completed` | `confirmed` → `completed` | Смена закрыта (legacy) | bot/web/celery |
| `cancelled` | `planned` → `cancelled` | Смена отменена, расписание тоже отменено | bot/web/contract |
| `cancelled` | `confirmed` → `cancelled` | Смена отменена (legacy) | bot/web/contract |

## Правила синхронизации

### 1. Открытие смены из расписания
- **Shift**: создается со статусом `active`
- **ShiftSchedule**: остается `planned` (НЕ меняется на `in_progress` или `active`)
- **Причина**: расписание может использоваться для повторных смен (если смена отменена и переоткрыта)

### 2. Закрытие смены
- **Shift**: меняется на `completed`
- **ShiftSchedule**: меняется на `completed` (если связана с расписанием)
- **Причина**: расписание отработано, больше не может использоваться

### 3. Отмена расписания
- **ShiftSchedule**: меняется на `cancelled`
- **Shift**: все связанные смены меняются на `cancelled` (если не `completed`)
- **Причина**: нельзя отменить завершенную смену

### 4. Отмена фактической смены
- **Shift**: меняется на `cancelled`
- **ShiftSchedule**: меняется на `cancelled` (если связана)
- **Причина**: расписание тоже отменено

## Запрещенные комбинации

❌ **НЕДОПУСТИМО:**
- `ShiftSchedule.status = cancelled` + `Shift.status = active` - отмененное расписание не может иметь активную смену
- `ShiftSchedule.status = cancelled` + `Shift.status = completed` - отмененное расписание не может иметь завершенную смену
- `ShiftSchedule.status = completed` + `Shift.status = active` - завершенное расписание не может иметь активную смену

✅ **ДОПУСТИМО:**
- `ShiftSchedule.status = planned` + `Shift.status = active` - смена открыта, расписание остается planned
- `ShiftSchedule.status = planned` + `Shift.status = completed` - смена закрыта, расписание завершено
- `ShiftSchedule.status = planned` + `Shift.status = cancelled` - смена отменена, расписание тоже отменено
- `ShiftSchedule.status = cancelled` + `Shift.status = cancelled` - оба отменены

## Нестандартные статусы (устаревшие)

⚠️ **УДАЛИТЬ:**
- `in_progress` - не используется в модели, заменен на `planned` (расписание остается planned при открытии смены)
- `active` для ShiftSchedule - не существует, только для Shift

## Автоматические сценарии

### Celery задачи
- **Автозакрытие смен**: `Shift.status = completed` → `ShiftSchedule.status = completed`
- **Автооткрытие последовательных смен**: создается новый `Shift` со статусом `active`, `ShiftSchedule` остается `planned`

### Расторжение договора
- Все `ShiftSchedule` со статусом `planned` → `cancelled`
- Все связанные `Shift` со статусом `active` → `cancelled`
- `Shift` со статусом `completed` НЕ меняются

## Реализация

Все переходы статусов должны проходить через `ShiftStatusSyncService`:
- `sync_on_shift_open()` - при открытии смены
- `sync_on_shift_close()` - при закрытии смены
- `sync_on_schedule_cancel()` - при отмене расписания (уже реализовано как `cancel_linked_shifts`)
- `sync_on_shift_cancel()` - при отмене фактической смены

