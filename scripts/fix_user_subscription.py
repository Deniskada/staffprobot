#!/usr/bin/env python3
"""Скрипт для исправления подписки пользователя на дэве."""

import asyncio
import sys
from datetime import datetime, timezone

# Добавляем корневую директорию в путь
sys.path.insert(0, '/opt/staffprobot')

from core.database.session import get_async_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from domain.entities.user import User
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.tariff_plan import TariffPlan
from core.logging.logger import logger


async def fix_user_subscription(telegram_id: int):
    """Исправление подписки пользователя."""
    async with get_async_session() as session:
        # Получаем пользователя
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            print(f"Пользователь с telegram_id={telegram_id} не найден")
            return
        
        user_id = user.id
        print(f"Обрабатываю пользователя id={user_id}, telegram_id={telegram_id}")
        
        # Получаем все подписки пользователя
        subscriptions_result = await session.execute(
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .options(selectinload(UserSubscription.tariff_plan))
            .order_by(UserSubscription.created_at.desc())
        )
        subscriptions = subscriptions_result.scalars().all()
        
        if not subscriptions:
            print("Подписки не найдены")
            return
        
        print(f"Найдено подписок: {len(subscriptions)}")
        
        # Находим истекшие подписки со статусом ACTIVE
        now = datetime.now(timezone.utc)
        expired_active = []
        
        for sub in subscriptions:
            print(f"  Подписка id={sub.id}: status={sub.status.value}, expires_at={sub.expires_at}")
            if sub.status == SubscriptionStatus.ACTIVE and sub.expires_at and sub.expires_at < now:
                expired_active.append(sub)
        
        # Обновляем статус истекших подписок
        if expired_active:
            print(f"\nОбновляю статус {len(expired_active)} истекших подписок:")
            for sub in expired_active:
                print(f"  Подписка id={sub.id}: ACTIVE -> EXPIRED (истекла {sub.expires_at})")
                sub.status = SubscriptionStatus.EXPIRED
                sub.updated_at = now
            await session.commit()
            print("Статус обновлен")
        
        # Проверяем наличие активной подписки
        active_result = await session.execute(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
            .options(selectinload(UserSubscription.tariff_plan))
        )
        active_subscription = active_result.scalar_one_or_none()
        
        if active_subscription:
            print(f"\nАктивная подписка найдена: id={active_subscription.id}")
            print(f"  Тариф: {active_subscription.tariff_plan.name}")
            print(f"  expires_at: {active_subscription.expires_at}")
            if active_subscription.is_expired():
                print(f"  ⚠️  Подписка истекла! Обновляю статус...")
                active_subscription.status = SubscriptionStatus.EXPIRED
                active_subscription.updated_at = now
                await session.commit()
                print("  Статус обновлен на EXPIRED")
        else:
            print("\n❌ Активной подписки не найдено")
        
        # Проверяем features для тарифа "Стандартный" (id=2)
        tariff_result = await session.execute(
            select(TariffPlan).where(TariffPlan.id == 2)
        )
        tariff = tariff_result.scalar_one_or_none()
        
        if tariff:
            print(f"\nТариф 'Стандартный' (id=2):")
            print(f"  features: {tariff.features}")
            if not tariff.features or len(tariff.features) == 0:
                print("  ⚠️  features пустой! Заполняю базовыми функциями...")
                # Базовые функции для стандартного тарифа
                tariff.features = [
                    "basic_reports",
                    "telegram_bot",
                    "basic_support",
                    "shared_calendar",
                    "notifications"
                ]
                await session.commit()
                print(f"  ✅ features обновлен: {tariff.features}")
        
        print("\n✅ Исправление завершено")


if __name__ == "__main__":
    # telegram_id пользователя на дэве
    telegram_id = 1220971779
    
    asyncio.run(fix_user_subscription(telegram_id))





