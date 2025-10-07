# Система планирования (plans)

## Структура
- `doc/plans/roadmap.md` — мигрированный @tasklist.md (все задачи, включая завершенные)
- `doc/plans/tracks/*.md` — треки по ролям
- `doc/plans/entities/*.md` — планы по сущностям

## Как ставить задачу
- Добавьте в `roadmap.md` под соответствующей итерацией строку чеклиста:
  - Пример: `- [ ] TASK: Добавить drag&drop сотрудников (manager)`
- Дублируйте ссылку на задачу в профильный `tracks/<role>.md` и при необходимости в `entities/<entity>.md`.
- Укажите: Type (feature|bug|refactor|doc), Files, Acceptance, Owner, Estimate, Links.

## Как вести выполнение
- Держите WIP ≤ 2 задачи на разработчика. Используйте колонки в PR/issue-трекере (Backlog→Ready→In Progress→Review→Done).
- Любая правка роутов/shared/бота/шаблонов — синхронизируйте `doc/vision_v1/*` и `doc/DOCUMENTATION_RULES.md`.
- Перед PR: все pre-commit проверки (включая `static_version` в шаблонах) должны проходить.

## Как завершать
- Отметьте задачу `[x]` в `roadmap.md` и синхронизируйте отражение в `tracks/*` и `entities/*`.
- Обновите прогресс в шапке roadmap (сводные цифры) и добавьте ссылку на PR/релиз.
- Проверьте деплой по `workflow.mdc` и наличие `?v=` у статики на проде.


## Выполненные работы: Тайм-слоты владельца — фильтрация и сортировка

- [x] Устранили дублирование маршрутов, используем `apps/web/routes/owner_timeslots.py` с префиксом `/owner/timeslots`
- [x] Добавили GET-параметры через Query: `date_from`, `date_to`, `sort_by`, `sort_order`
- [x] Реализовали нормализацию и whitelist параметров в `TimeSlotService.get_timeslots_by_object`
- [x] Обновили шаблон `owner/timeslots/list.html`:
  - ссылки сортировки без пустых `date_from/date_to`
  - инверсия `sort_order` при повторном клике на тот же столбец
  - визуальные индикаторы направления сортировки (стрелки)
- [x] Убрали автосабмит по изменению дат; фильтры применяются кнопкой
- [x] Добавили документацию-паттерн: `docs/README_TABLE_FILTERING_SORTING.md`
- [x] Добавили тесты:
  - unit: нормализация/whitelist параметров
  - integration: GET со сценариями фильтрации и сортировки
- [x] Выполнили деплой на прод (git → build → up, миграции), проверили логи веб-сервиса

