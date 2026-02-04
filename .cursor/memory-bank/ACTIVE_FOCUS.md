# Active Focus - Текущий фокус работы

## Текущая задача

**Источник**: `doc/plans/roadmap.md`  
**Итерация**: 54 (Конструктор шаблонов договоров)  
**Статус**: В работе (Фаза 1 завершена)

## Текущий контекст

Работа над конструктором шаблонов договоров - универсальный движок создания шаблона договора через пошаговый мастер.

## Активные файлы

- `apps/web/routes/constructor_api.py`
- `apps/web/services/constructor_service.py`
- `domain/entities/constructor_flow.py`
- `domain/entities/contract_type.py`
- `doc/vision_v1/contract_constructor.md`

## Последние изменения

- Создана структура для режимов и workflows Supercode.sh
- Подготовлен план интеграции фреймворков (memory-bank, OpenSpec, spec-kit, TaskMaster)

## Следующие шаги

1. Установить cursor-memory-bank
2. Настроить OpenSpec структуру
3. Интегрировать spec-kit команды
4. Настроить TaskMaster через MCP

## Блокеры

Нет

## Заметки

- Все инструменты должны работать вместе, не дублируя функциональность
- Приоритет: Memory Bank → OpenSpec/spec-kit → TaskMaster

---

**Последнее обновление**: 2026-02-04
