import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.web.services.test_user_service import TestUserService
from domain.entities.user import User, UserRole


@pytest.mark.asyncio
async def test_create_and_delete_test_users(async_session: AsyncSession):
    svc = TestUserService(async_session)
    # Создаем по одному пользователя каждого типа
    u1 = await svc.create_test_user(UserRole.OWNER)
    u2 = await svc.create_test_user(UserRole.MANAGER)
    u3 = await svc.create_test_user(UserRole.EMPLOYEE)

    assert u1.is_test_user and u2.is_test_user and u3.is_test_user

    # Проверяем наличие в БД
    res = await async_session.execute(select(User).where(User.is_test_user == True))
    users = res.scalars().all()
    assert len(users) >= 3

    # Удаляем всех тестовых
    deleted = await svc.delete_all_test_users()
    assert deleted >= 3

    # Проверяем отсутствие
    res2 = await async_session.execute(select(User).where(User.is_test_user == True))
    users2 = res2.scalars().all()
    assert len(users2) == 0


