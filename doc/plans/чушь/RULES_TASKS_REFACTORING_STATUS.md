# Статус рефакторинга: Rules Engine, Tasks v2, Incidents

**Дата:** 24.10.2025  
**Ветка:** `feature/rules-tasks-incidents`  
**Цель:** Унификация правил/задач/инцидентов через shared-компоненты для всех ролей

---

## ✅ Завершённые этапы

### 1. База данных и миграции
- ✅ Таблицы: `rules`, `task_templates_v2`, `task_plans_v2`, `task_entries_v2`, `incidents`, `cancellation_reasons`
- ✅ Миграции применены: `20251022_001_add_cancellation_reasons.py`, `20251023_001_rules_tasks_incidents.py`
- ✅ SEED глобальных причин отмены (11 штук: medical_cert, illness, family и т.д.)
- ✅ Миграция данных: `Object.shift_tasks` JSONB → `TaskTemplateV2` (8 шаблонов созданы)

### 2. Rules Engine
- ✅ Модель: `domain/entities/rule.py` (owner_id, code, scope, condition_json, action_json, priority)
- ✅ Сервис: `shared/services/rules_engine.py` (evaluate, get_active_rules, owner overrides)
- ✅ Интеграция:
  - `core/celery/tasks/adjustment_tasks.py` (late penalties) — try Rules, fallback legacy
  - `shared/services/shift_cancellation_service.py` (cancel fines) — try Rules, fallback legacy
- ✅ UI: `/owner/rules` (список, toggle активности, SEED 3 дефолтных правил)
- ✅ SEED endpoint: `POST /owner/rules/seed` (late 50₽, cancel_short 500₽, cancel_invalid 1000₽)

### 3. Tasks v2 (Shared-архитектура)
- ✅ Модели: `TaskTemplateV2`, `TaskPlanV2`, `TaskEntryV2`
- ✅ Shared-сервис: `shared/services/task_service.py`
  - `get_templates_for_role()` — фильтр по owner/manager (allowed_objects)/employee (contracts)
  - `create_template()` — CRUD шаблонов
  - `get_entries_for_role()` — выполнение задач с фильтрами
- ✅ Роутеры (через TaskService):
  - `apps/web/routes/owner_tasks.py` → `/owner/tasks/*`
  - `apps/web/routes/manager_tasks.py` → `/manager/tasks/*`
  - `apps/web/routes/employee_tasks.py` → `/employee/tasks/my`
- ✅ UI:
  - `/owner/tasks` (главная с навигацией)
  - `/owner/tasks/templates` (список + модал создания)
  - `/owner/tasks/plan`, `/owner/tasks/entries` (заглушки)
  - Аналогично для manager/employee
- ✅ Депрекация: `Object.shift_tasks` в формах → readonly + алерт "Используйте /owner/tasks/templates"

### 4. Cancellation Reasons (DB-driven)
- ✅ Модель: `domain/entities/cancellation_reason.py`
- ✅ Сервис: `shared/services/cancellation_policy_service.py`
- ✅ UI: `/owner/cancellations/reasons` (управление причинами, owner overrides)
- ✅ Бот интеграция: динамическая загрузка причин из БД (убран хардкод)

### 5. Incidents
- ✅ Модель: `domain/entities/incident.py` (category, severity, status, evidence_media_json)
- ✅ Роутер: `apps/web/routes/owner_incidents.py` → `/owner/incidents`
- ✅ UI заглушка: `/owner/incidents` (список)

### 6. Media Orchestrator
- ✅ Сервис: `shared/services/media_orchestrator.py` (begin_flow, handle_text/photo, skip)
- ✅ UserAction.MEDIA_FLOW добавлен в `core/state/user_state_manager.py`
- ⏳ TODO: Интеграция в бот handlers

### 7. Депрекация legacy-полей
- ✅ `Object.late_*` и `cancellation_*` в формах → readonly + алерт "Перенесено в /owner/rules"
- ✅ `Object.shift_tasks` в формах → readonly + алерт "Используйте /owner/tasks/templates"
- ✅ UI визуально показывает переход на новую систему

---

## 🔄 В процессе

### Media Orchestrator интеграция
- ⏳ Рефактор `apps/bot/handlers_div/schedule_handlers.py` (отмена смен → media flow)
- ⏳ Рефактор `apps/bot/handlers_div/shift_handlers.py` (закрытие смен → media flow)

### Incident жизненный цикл
- ⏳ Workflow: New → InReview → Resolved/Rejected
- ⏳ Создание вручную (веб/бот) и авто (из правил)
- ⏳ Аналитика `/owner/analytics/incidents`

---

## 📋 Осталось

### Критичные
1. **Рефактор бота** (media flow, единый state-machine)
2. **Incident full workflow** (создание, модерация, связь с payroll)
3. **Feature-flags** (`enable_rules_engine`, `tasks_v2`, `incidents_v1`)
4. **Тесты** (Rules Engine, TaskService, MediaOrchestrator)

### Опциональные
5. UI: редактирование правил (JSON-редактор условий/действий)
6. UI: планирование задач (drag-drop на календаре)
7. Полная депрекация legacy-полей (удаление после миграции всех владельцев)
8. Автогенерация incidents из правил

### Документация
9. Обновить `doc/vision_v1/features/*` (rules, tasks_v2, incidents)
10. Обновить `doc/plans/roadmap.md` (новая итерация "Рефакторинг автоправил/задач")

---

## 🎯 Критерии готовности к мердж

- [x] Миграции применены и работают
- [x] Rules Engine интегрирован в расчёты (late/cancel) с fallback
- [x] Tasks v2 shared-архитектура работает для всех ролей
- [x] UI правил/задач доступен и функционален (базовый CRUD)
- [x] Legacy-поля визуально помечены как deprecated
- [ ] Бот использует MediaOrchestrator (отмена/закрытие смен)
- [ ] Incident workflow минимально работает
- [ ] Тесты покрывают критичные сценарии (70%+)
- [ ] Документация обновлена
- [ ] Ручное тестирование на dev подтвердило отсутствие регрессий

---

## 📝 Известные ограничения

1. **Rules Engine**: только базовые условия (AND), нет OR/NOT/вложенности
2. **Tasks v2**: нет UI планирования (drag-drop), только список шаблонов
3. **Incidents**: нет авто-создания из правил, только ручное
4. **Media Orchestrator**: не интегрирован в бота (в процессе)
5. **Legacy-поля**: readonly, но не удалены (для совместимости)

---

## 🔗 Ключевые файлы

**Модели:**
- `domain/entities/rule.py`
- `domain/entities/task_template.py` (TaskTemplateV2)
- `domain/entities/task_plan.py` (TaskPlanV2)
- `domain/entities/task_entry.py` (TaskEntryV2)
- `domain/entities/incident.py`
- `domain/entities/cancellation_reason.py`

**Сервисы:**
- `shared/services/rules_engine.py`
- `shared/services/task_service.py`
- `shared/services/cancellation_policy_service.py`
- `shared/services/media_orchestrator.py`

**Роутеры:**
- `apps/web/routes/owner_rules.py`
- `apps/web/routes/owner_tasks.py`
- `apps/web/routes/manager_tasks.py`
- `apps/web/routes/employee_tasks.py`
- `apps/web/routes/owner_incidents.py`
- `apps/web/routes/owner_cancellation_reasons.py`

**Миграции:**
- `migrations/versions/20251022_001_add_cancellation_reasons.py`
- `migrations/versions/20251023_001_rules_tasks_incidents.py`

---

**Автор:** AI Assistant  
**Статус:** В разработке (ветка feature/rules-tasks-incidents)

