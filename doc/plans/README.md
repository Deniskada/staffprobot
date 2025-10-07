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

