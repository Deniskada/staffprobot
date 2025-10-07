# [BUG] Дубликаты маршрутов в manager.py и system_settings_api.py

- Дата: 2025-10-07
- Версии: (см. git log)
- Компонент: web
- Теги: routes, web

## Симптомы
- Два обработчика `@router.get("/")` в `manager.py` (разные редиректы).
- Два `POST /initialize` в `system_settings_api.py`.

## Шаги воспроизведения
1. Открыть файлы и найти совпадающие декораторы.

## Ожидаемое поведение
- Один канонический обработчик на путь (метод+путь) в модуле.

## Фактическое поведение
- Дубли приводят к неоднозначности и риску конфликтов.

## Логи/скриншоты
```
manager.py: @router.get("/") ... @router.get("/")
system_settings_api.py: @router.post("/initialize") ... @router.post("/initialize")
```

## Диагностика (root cause)
- Исторический наслоившийся код, пропущенные ревью проверки.

## Решение (fix)
- Оставлен единый редирект `/manager/` → `/manager/dashboard`, второй удален.
- Объединён `POST /initialize` в `system_settings_api.py` в один канонический endpoint.
- Добавлены правила в conventions и pre-commit grep на дубли.

## Регрессии/риски
- Минимальные; проверить ссылки/редиректы в UI менеджера.

## Связи
- Задача: doc/plans/roadmap.md
- Документация: doc/vision_v1/roles/manager.md; doc/vision_v1/entities/employees.md
- PR: (см. текущие изменения)
