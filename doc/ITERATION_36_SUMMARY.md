# Итерация 36: Рефакторинг Rules, Tasks, Incidents

**Статус:** ✅ Завершена (95%)  
**Ветка:** `feature/rules-tasks-incidents`  
**Дата:** 27-28 октября 2025  

## Цель

Унификация системы правил, задач и инцидентов через shared-компоненты для устранения дублирования кода и упрощения поддержки.

---

## Выполненные задачи

### 1. ✅ Rules Engine (MVP)
- **Модель**: `domain/entities/rule.py` (scope: late/cancellation/task/incident)
- **Сервис**: `shared/services/rules_engine.py` с приоритетами и fallback
- **Интеграция**: 
  - `shared/services/payroll_adjustment_service.py` (опоздания)
  - `shared/services/shift_cancellation_service.py` (отмена смен)
- **UI**: `/owner/rules` — список, toggle, SEED
- **Feature-flag**: `settings.enable_rules_engine`

### 2. ✅ Tasks v2 (shared-архитектура)
- **Модели**: 
  - `TaskTemplateV2` — шаблоны задач (code, title, is_mandatory, requires_media, default_bonus_amount)
  - `TaskPlanV2` — планирование (object_ids, recurrence_type, planned_time_start)
  - `TaskEntryV2` — выполнение (shift_id, is_completed, completion_media)
- **Сервис**: `shared/services/task_service.py` (права по ролям owner/manager/employee)
- **Роутеры**: 
  - `/owner/tasks/*` (templates, plan, entries)
  - `/manager/tasks/*` (аналогично)
  - `/employee/tasks/my` (просмотр своих)
- **Бот**: 
  - Интеграция в "📋 Мои задачи"
  - Callback `complete_task_v2:{entry_id}`
  - Фото-отчёты через Media Orchestrator
- **Celery**: 
  - `auto_assign_tasks` (4:00 MSK ежедневно)
  - `process_task_bonuses` (каждые 10 мин)
- **UI улучшения**:
  - Авто-генерация кода шаблона
  - Toggle переключатели для активности
  - Множественный выбор объектов
  - Периодичность (weekdays, day_interval)
- **Feature-flag**: `settings.enable_tasks_v2`
- **Миграция данных**: `shift_tasks` JSONB → `TaskTemplateV2` (8 шаблонов)
- **Депрекация**: `Object.shift_tasks` → readonly + алерт

**Архитектурное исправление (критичное)**:
- Добавлен `shift_id` в `TaskEntryV2` для унификации запланированных и спонтанных смен
- Решена проблема ленивой загрузки (добавлен `selectinload(TaskPlanV2.template)`)
- Упрощён `_collect_shift_tasks` — одна загрузка для всех типов смен

### 3. ✅ Cancellation Reasons (DB-driven)
- **Модель**: `CancellationReason` (global + owner-overrides)
- **Сервис**: `CancellationPolicyService` (treated_as_valid logic)
- **UI**: `/owner/cancellations/reasons` (CRUD)
- **SEED**: 11 глобальных причин (больничный, отпуск, семья, etc)
- **Интеграция**: Бот динамически загружает причины

### 4. ✅ Incidents (заглушки MVP)
- **Модель**: `Incident` (category, severity, status, evidence_media, suggested_adjustments)
- **Сервис**: `shared/services/incident_service.py` (CRUD)
- **UI**: `/owner/incidents` — список с фильтрами
- **Feature-flag**: `settings.enable_incidents`

### 5. ✅ Media Orchestrator
- **Сервис**: `shared/services/media_orchestrator.py`
  - State machine в Redis
  - Конфигурируемые требования (require_text, require_photo, max_photos)
  - Методы: `begin_flow`, `add_text`, `add_photo`, `finish`, `cancel`
- **Интеграция**:
  - Tasks v2 фото-отчёты
  - Отмена смены (документы)
- **Feature-flag**: `settings.enable_media_orchestrator` (частично)

### 6. ✅ Feature-flags
- **Определение**: `core/config/settings.py`
- **Глобальный доступ**: `apps/web/jinja.py` → `templates.env.globals['settings']`
- **Проверки**: HTTPException(404) в роутах при выключенном флаге
- **UI**: Условный рендеринг в sidebar (`{% if settings.enable_tasks_v2 %}`)

### 7. ✅ Автотесты
- `tests/unit/test_rules_engine.py` — тесты Rules Engine
- `tests/unit/test_task_service.py` — тесты TaskService
- `tests/unit/test_media_orchestrator.py` — тесты Media Orchestrator

---

## Технические детали

### Миграции
1. `20251023_001_rules_tasks_incidents.py` — создание таблиц Rule, TaskTemplateV2, TaskPlanV2, TaskEntryV2, Incident
2. `6fc973252b64_add_object_ids_to_task_plan.py` — множественный выбор объектов
3. `5056deff776a_add_completion_fields_to_task_entry.py` — поля выполнения задач
4. `78851600b877_add_shift_id_to_task_entry_v2.py` — унификация через shift_id
5. `e73e979cde11_create_shift_tasks_table.py` — legacy shift_tasks

### Ключевые файлы
- **Backend**: `shared/services/{rules_engine,task_service,incident_service,media_orchestrator}.py`
- **Routes**: `apps/web/routes/{owner_rules,owner_tasks,owner_incidents}.py`
- **Templates**: `apps/web/templates/owner/{rules,tasks,incidents}/*`
- **Bot**: `apps/bot/handlers_div/shift_handlers.py` (Tasks v2 интеграция)
- **Celery**: `core/celery/tasks/{task_assignment,task_bonuses}.py`

### Commits
- 15+ коммитов в ветке `feature/rules-tasks-incidents`
- Последний: "Добавление: интеграция Media Orchestrator"

---

## Acceptance Criteria

- [x] Rules Engine работает с fallback на legacy ✅
- [x] Tasks v2 доступны для owner/manager/employee ✅
- [x] UI правил/задач/инцидентов функционален ✅
- [x] Legacy-поля помечены deprecated (readonly + алерты) ✅
- [x] Бот использует Tasks v2 с shift_id унификацией ✅
- [x] Media Orchestrator интегрирован в Tasks v2 и отмену смен ✅
- [x] Feature-flags проверяются в роутах и UI ✅
- [x] Тесты покрывают критичные компоненты ✅
- [ ] Документация обновлена (в процессе)

---

## Известные ограничения

1. **Incidents**: Только UI заглушки, workflow не реализован
2. **Media Orchestrator**: Не интегрирован в legacy закрытие смен с задачами
3. **Rules Engine**: UI показывает JSON, нет визуального редактора
4. **Тесты**: Покрытие ~30%, нужны интеграционные тесты

---

## Следующие шаги

1. ✅ Завершить документацию
2. Протестировать на prod (через feature-flags)
3. Расширить Incidents workflow
4. Мигрировать оставшиеся медиа-потоки на Orchestrator
5. Добавить визуальный редактор правил

---

## Прогресс итерации

**Общий:** 95% завершено  
**Готово к деплою:** Да (с включенными флагами на dev)  
**Рекомендация:** Merge в main → деплой на prod с включением флагов поэтапно

