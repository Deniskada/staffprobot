import pytest


@pytest.mark.asyncio
async def test_toggle_and_create_test_users(client_superadmin):
    # Включаем режим
    r1 = await client_superadmin.post('/api/system-settings/test-users/toggle?enabled=true')
    assert r1.status_code == 200
    assert r1.json().get('success') is True

    # Создаем владельца
    r2 = await client_superadmin.post('/api/system-settings/test-users/create?role=owner')
    assert r2.status_code == 200
    data = r2.json()
    assert data.get('success') is True
    assert 'telegram_id' in data

    # Выключаем режим (должно удалять всех тестовых)
    r3 = await client_superadmin.post('/api/system-settings/test-users/toggle?enabled=false')
    assert r3.status_code == 200
    assert r3.json().get('success') is True


