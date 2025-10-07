"""Сервис для создания/удаления тестовых пользователей."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from core.logging.logger import logger
from domain.entities.user import User, UserRole
from domain.entities.contract import Contract
from domain.entities.user_subscription import UserSubscription
from domain.entities.manager_object_permission import ManagerObjectPermission

import secrets


class TestUserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _generate_unique_telegram_id(self) -> int:
        """Генерирует уникальный telegram_id, не занятый в БД."""
        while True:
            tg_id = int("5" + str(secrets.randbelow(10**9)).zfill(9))  # 10-значный, начинается с 5
            result = await self.session.execute(select(User).where(User.telegram_id == tg_id))
            if result.scalar_one_or_none() is None:
                return tg_id

    async def create_test_user(self, role: UserRole) -> User:
        """Создает тестового пользователя с указанной ролью."""
        tg_id = await self._generate_unique_telegram_id()
        user = User(
            telegram_id=tg_id,
            username=f"test_{role.value}_{tg_id}",
            first_name="Тест",
            last_name=role.value.capitalize(),
            role=role.value,
            roles=[role.value],
            is_active=True,
            is_test_user=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        logger.info(f"Created test user {user.id} with role {role.value} and telegram_id {tg_id}")
        return user

    async def delete_all_test_users(self) -> int:
        """Удаляет всех тестовых пользователей и связанные записи."""
        # Получаем тестовых пользователей
        res = await self.session.execute(select(User.id).where(User.is_test_user == True))
        user_ids: List[int] = [row[0] for row in res.fetchall()]
        if not user_ids:
            return 0

        # Удаляем связанные записи (контракты, разрешения, подписки)
        # Сначала привязанные разрешения менеджеров через контракты
        res_c = await self.session.execute(select(Contract.id).where(Contract.owner_id.in_(user_ids)))
        owner_contract_ids = [row[0] for row in res_c.fetchall()]
        res_c2 = await self.session.execute(select(Contract.id).where(Contract.employee_id.in_(user_ids)))
        employee_contract_ids = [row[0] for row in res_c2.fetchall()]
        all_contract_ids = owner_contract_ids + employee_contract_ids
        if all_contract_ids:
            await self.session.execute(
                delete(ManagerObjectPermission).where(ManagerObjectPermission.contract_id.in_(all_contract_ids))
            )
            await self.session.execute(delete(Contract).where(Contract.id.in_(all_contract_ids)))

        # Подписки
        await self.session.execute(delete(UserSubscription).where(UserSubscription.user_id.in_(user_ids)))

        # Удаляем пользователей
        await self.session.execute(delete(User).where(User.id.in_(user_ids)))
        await self.session.commit()
        logger.info(f"Deleted {len(user_ids)} test users and related records")
        return len(user_ids)


