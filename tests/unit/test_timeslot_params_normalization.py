from apps.web.services.object_service import TimeSlotService


def test_normalize_sort_defaults(mocker):
    svc = TimeSlotService(db_session=mocker.Mock())
    # доступ к приватным не нужен, проверим, что некорректные значения не падают
    # и что метод строит запрос без выброса исключений
    mocker.patch.object(svc, "_get_user_internal_id", return_value=1)
    # мок проверки объекта
    mocker_db = svc.db
    mocker_db.execute = mocker.AsyncMock()
    mocker_db.execute.return_value.scalar_one_or_none = lambda: True
    # второй вызов select(TimeSlot) — вернём пустой список
    class R:
        def scalars(self):
            class C:
                def all(self):
                    return []
            return C()
    mocker_db.execute.return_value = R()

    # не должно падать при мусорных параметрах
    import asyncio

    asyncio.run(svc.get_timeslots_by_object(
        object_id=1,
        telegram_id=122,
        date_from="  ",
        date_to="",
        sort_by="unknown",
        sort_order="bad"
    ))


