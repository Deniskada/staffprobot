# План работ: Мердж feature/rules-tasks-incidents → main

**Дата начала:** 29.10.2025  
**Ветка:** `feature/rules-tasks-incidents`  
**Цель:** Интеграция Rules Engine, Tasks v2, Incidents в основную ветку с синхронизацией изменений из main

---

## 📊 Общий прогресс

**Статус:** 🚧 В работе  
**Готовность:** 0/6 этапов завершено  
**Ориентировочное время:** 8-10 часов

---

## 🎯 Этапы выполнения

### ✅ Этап 0: Подготовка (COMPLETED)
- [x] Анализ различий между main и feature/rules-tasks-incidents
- [x] Выявление критичной проблемы с роутингом payroll-adjustments
- [x] Составление плана работ
- [x] Фиксация плана в документе

**Критичная проблема:**
- В `owner_payroll_adjustments.py`: `prefix="/payroll-adjustments"`
- В `app.py`: `prefix="/owner/payroll/adjustments"`
- Результат: дублирование префикса → `/owner/payroll/adjustments/payroll-adjustments` ❌

**Изменения в main (отсутствуют в feature):**
- ~20 коммитов с улучшениями payroll
- calculation_details для начислений
- Поддержка monthly графиков с payments array
- Исправления в применении корректировок
- Отчёты по выплатам и начислениям

---

### ⏳ Этап 1: Исправление роутинга payroll-adjustments (30 мин)

**Задачи:**
- [ ] Изменить prefix в `apps/web/routes/owner_payroll_adjustments.py` → пустая строка
- [ ] Изменить prefix в `apps/web/routes/manager_payroll_adjustments.py` → пустая строка
- [ ] Проверить корректность путей:
  - `/owner/payroll/adjustments` ✅
  - `/manager/payroll/adjustments` ✅
- [ ] Обновить ссылки в шаблонах (если есть хардкод)

**Acceptance Criteria:**
- Роуты доступны по правильным путям без дублирования
- Старые ссылки не ломаются (редиректы при необходимости)

---

### ⏳ Этап 2: Синхронизация с main (2-3 часа)

**Задачи:**
- [ ] Мердж main → feature/rules-tasks-incidents
- [ ] Разрешение конфликтов:
  - [ ] `apps/web/routes/payroll.py` (логика расчётов)
  - [ ] `core/celery/tasks/payroll_tasks.py` (celery задачи)
  - [ ] `core/celery/tasks/adjustment_tasks.py` (корректировки)
  - [ ] `apps/web/templates/owner/payroll_adjustments/list.html`
  - [ ] `apps/web/templates/manager/payroll_adjustments/list.html`
- [ ] Проверка совместимости:
  - [ ] Rules Engine работает с новой логикой calculation_details
  - [ ] Tasks v2 совместим с обновлённой структурой смен
  - [ ] Fallback на legacy-поля функционирует

**Acceptance Criteria:**
- Все конфликты разрешены корректно
- Новая логика из main сохранена
- Rules Engine и Tasks v2 интегрированы без потери функционала
- Тесты проходят (если есть)

---

### ⏳ Этап 3: Доработка недостающего функционала (4-5 часов)

#### 3.1. Incidents workflow (2 часа)
- [ ] Роутер создания инцидента (POST `/owner/incidents/create`)
- [ ] Форма создания (веб): employee, shift, category, severity, description, media
- [ ] Базовый жизненный цикл:
  - [ ] New → InReview (автоматически)
  - [ ] InReview → Resolved (ручное действие владельца)
  - [ ] InReview → Rejected (отклонение)
- [ ] Связь с корректировками:
  - [ ] Поле `suggested_adjustments` в модели
  - [ ] Кнопка "Применить корректировку" в UI
- [ ] Фильтры в списке: status, category, severity, employee, date_range

#### 3.2. Media Orchestrator интеграция (1 час)
- [ ] Завершить интеграцию в `shift_handlers.py` (закрытие смен с задачами)
- [ ] Добавить в `schedule_handlers.py` (отмена смен с документами)
- [ ] Тестирование flow в боте

#### 3.3. Тесты (1-2 часа)
- [ ] `tests/integration/test_rules_engine_payroll.py` (Rules + расчёты)
- [ ] `tests/integration/test_tasks_v2_shifts.py` (Tasks с shift_id)
- [ ] `tests/unit/test_incident_service.py` (CRUD инцидентов)
- [ ] Покрытие: 60%+ для новых модулей

**Acceptance Criteria:**
- Incidents можно создавать, просматривать, модерировать
- Media Orchestrator полностью работает в боте
- Тесты покрывают критичные сценарии

---

### ✅ Этап 4: Тестирование (COMPLETED)

#### 4.1. Локальное тестирование (docker-compose.dev.yml)
- [x] Проверка роутов:
  - [ ] `/owner/rules` (список, toggle, SEED)
  - [ ] `/owner/tasks/*` (templates, plan, entries)
  - [ ] `/owner/incidents` (список, создание, модерация)
  - [ ] `/owner/payroll/adjustments` (корректный путь)
  - [ ] `/manager/payroll/adjustments` (корректный путь)
- [ ] Проверка бота:
  - [ ] Tasks v2 в "📋 Мои задачи"
  - [ ] Media Orchestrator при закрытии смен
  - [ ] Динамические причины отмены
- [ ] Проверка расчётов:
  - [ ] Rules Engine применяет штрафы за опоздания
  - [ ] Rules Engine применяет штрафы за отмены
  - [ ] Fallback на legacy-поля при отсутствии правил

#### 4.2. Регрессионное тестирование
- [ ] Создание начислений и выплат (основной flow)
- [ ] Применение корректировок (shift_base, bonus, penalty)
- [ ] Отмена смен с правилами (короткий срок, неуважительная причина)
- [ ] Опоздания с правилами
- [ ] Расчёт табелей
- [ ] Отчёты по выплатам и начислениям

**Acceptance Criteria:**
- Все основные функции работают без ошибок
- Регрессий не обнаружено
- Производительность не деградировала

---

### ⏳ Этап 5: Документация (1 час)

**Задачи:**
- [ ] Создать/обновить `doc/vision_v1/features/rules_engine.md`
- [ ] Создать/обновить `doc/vision_v1/features/tasks_v2.md`
- [ ] Создать/обновить `doc/vision_v1/features/incidents.md`
- [ ] Обновить `doc/DOCUMENTATION_RULES.md` (новые роуты)
- [ ] Создать `doc/MIGRATION_GUIDE_RULES_TASKS.md` для владельцев:
  - Как перейти с legacy полей на Rules
  - Как мигрировать shift_tasks на Tasks v2
  - Feature-flags и поэтапное включение
- [ ] Обновить `doc/plans/roadmap.md` (Итерация 36 → Completed)

**Acceptance Criteria:**
- Документация актуальна и полна
- Есть руководство для пользователей
- Roadmap отражает завершение итерации

---

### ⏳ Этап 6: Деплой (после утверждения пользователя)

#### 6.1. Подготовка к мерджу
- [ ] Финальная проверка всех изменений
- [ ] Создание backup БД прода
- [ ] Проверка миграций на dev
- [ ] Получение подтверждения от пользователя

#### 6.2. Мердж в main
```bash
git checkout main
git pull origin main
git merge feature/rules-tasks-incidents
git push origin main
```

#### 6.3. Деплой на prod
```bash
# 1. Обновить код на проде
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && git pull origin main'

# 2. Применить миграции
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml exec web alembic upgrade head'

# 3. Перезапуск с выключенными флагами (безопасно)
ssh staffprobot@staffprobot.ru 'cd /opt/staffprobot && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d'
```

#### 6.4. Поэтапное включение feature-flags
- [ ] **День 1:** `enable_rules_engine = True`
  - Мониторинг расчётов штрафов
  - Проверка fallback на legacy
  - Логи ошибок
- [ ] **День 3:** `enable_tasks_v2 = True` (после проверки правил)
  - Мониторинг создания задач
  - Проверка бота
  - Обратная связь от пользователей
- [ ] **День 7:** `enable_incidents = True` (полный запуск)
  - Обучение владельцев
  - Мониторинг использования
  - Сбор feedback

**Acceptance Criteria:**
- Деплой прошёл без ошибок
- Миграции применены корректно
- Feature-flags включаются поэтапно без проблем
- Мониторинг показывает стабильность

---

## ⚠️ Риски и митигация

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Конфликты при мердже main | Высокая | Среднее | Тщательное разрешение, manual testing |
| Регрессия в расчётах payroll | Средняя | Высокое | Feature-flags, fallback, backup БД |
| Несовместимость Rules Engine с новой логикой | Низкая | Среднее | Fallback на legacy-поля сохранён |
| Баги в Tasks v2 на проде | Средняя | Среднее | Постепенное включение, мониторинг, быстрый откат |
| Потеря данных при миграции | Низкая | Критичное | Backup БД, тестирование миграций на dev |

---

## 📋 Чек-лист готовности к мерджу

- [ ] Роутинг payroll-adjustments исправлен
- [ ] Изменения из main синхронизированы
- [ ] Конфликты разрешены корректно
- [ ] Incidents workflow минимально работает
- [ ] Media Orchestrator полностью интегрирован
- [ ] Тесты покрывают критичные сценарии (60%+)
- [ ] Документация обновлена
- [ ] Локальное тестирование пройдено успешно
- [ ] Регрессионное тестирование пройдено
- [ ] Backup БД создан
- [ ] Получено подтверждение пользователя

---

## 📝 Примечания

### Известные ограничения (после мерджа)
1. **Incidents**: Базовый workflow, нет авто-создания из правил
2. **Rules Engine**: JSON UI, нет визуального редактора условий
3. **Tasks v2**: Нет drag-drop планирования на календаре
4. **Тесты**: Покрытие ~60%, нужно довести до 80%+

### Будущие улучшения (вне скоупа)
- Визуальный редактор правил (condition builder)
- Автосоздание incidents из правил при нарушениях
- UI планирования задач с drag-drop
- Расширенные аналитики по правилам/задачам/инцидентам
- Полное удаление legacy-полей (после миграции всех владельцев)

---

**Автор:** AI Assistant  
**Согласовано:** Den Novikov  
**Статус:** 🚧 В работе


