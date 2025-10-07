import pytest
from httpx import AsyncClient
from apps.web.app import app


@pytest.mark.asyncio
async def test_timeslots_list_no_filters(mocker):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/owner/timeslots/object/1")
        # Страница должна открываться
        assert resp.status_code in (200, 302, 303)


@pytest.mark.asyncio
async def test_timeslots_list_with_date_filters(mocker):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/owner/timeslots/object/1", params={
            "date_from": "2025-01-01",
            "date_to": "2025-12-31",
            "sort_by": "slot_date",
            "sort_order": "asc",
        })
        assert resp.status_code in (200, 302, 303)


