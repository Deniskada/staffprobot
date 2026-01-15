# Правила фильтрации и сортировки таблиц в веб-интерфейсе

## Кратко
- Параметры из URL всегда принимаем через Query с дефолтами
- Нормализуем входы: trim, lower, пустые строки → None
- Бэкенд обязан валидировать и приводить sort_by/sort_order к whitelisted значениям
- В шаблонах формируем ссылки так, чтобы не подставлять пустые параметры
- JS не должен авто-сабмитить форму при изменении дат, только по кнопке

## Типовые ошибки (root causes)
1. Смешение дубликатов роутов и несовпадающих префиксов → 404/разная логика
2. Неправильное получение query-параметров (без Query), пустые строки ломают фильтр
3. Жёсткая подстановка `date_from=&date_to=` в ссылки сортировки
4. Автосабмит JS при изменении дат мешает выбрать обе даты
5. Отсутствие нормализации sort_by/sort_order и whitelist-а

## Обязательный контракт бэкенда (FastAPI)
```python
@router.get("/object/{object_id}")
async def list_timeslots(
    object_id: int,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort_by: str = Query("slot_date"),
    sort_order: str = Query("desc"),
):
    # нормализация на уровне сервиса
```

Сервис:
```python
allowed_sort_by = {"slot_date", "start_time", "hourly_rate"}
sort_by = (sort_by or "slot_date").strip().lower()
if sort_by not in allowed_sort_by: sort_by = "slot_date"
sort_order = (sort_order or "desc").strip().lower()
if sort_order not in {"asc","desc"}: sort_order = "desc"

date_from = (date_from or "").strip() or None
date_to = (date_to or "").strip() or None
```

## Правила шаблонов (Jinja2)
- Не подставлять пустые параметры в ссылки:
```jinja2
?{% if date_from %}date_from={{ date_from }}&{% endif %}{% if date_to %}date_to={{ date_to }}&{% endif %}sort_by=...
```
- Сортировка только по клику на заголовок; порядок переключаем по текущему `sort_order`

## Правила JavaScript
- Не использовать авто-submit на change для дат
- Позволять пользователю выбрать обе даты и нажать "Применить"

## Чек-лист PR
- [ ] Параметры читаются через Query
- [ ] Нормализация/whitelist на бэкенде
- [ ] Нет пустых параметров в ссылках шаблона
- [ ] Нет автосабмита фильтров дат
- [ ] Логи фиксируют применённые фильтры/сортировку
- [ ] Есть базовые тесты: юнит нормализации и интеграционный GET со всеми сценариями

## План действий при сбоях
1. Проверить, какой роут реально обрабатывает запрос (префиксы include_router)
2. В логах увидеть применённые `date_from/date_to/sort_by/sort_order`
3. Убедиться, что ссылки не содержат пустых `date_from=&date_to=`
4. Убедиться, что нет авто-сабмита в JS
5. Протестировать 4 сценария: без дат; только `from`; только `to`; оба


