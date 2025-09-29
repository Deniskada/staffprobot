#!/usr/bin/env python3
"""
Скрипт для создания тестовых отзывов и рейтингов
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_async_session
from domain.entities.review import Review, ReviewStatus, Rating
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from sqlalchemy import select
import random
from datetime import datetime, timedelta

async def create_test_reviews():
    """Создает тестовые отзывы для демонстрации системы."""
    async with get_async_session() as session:
        # Получаем пользователей
        users_query = select(User)
        users_result = await session.execute(users_query)
        users = users_result.scalars().all()
        
        # Получаем объекты
        objects_query = select(Object)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        
        # Получаем договоры
        contracts_query = select(Contract)
        contracts_result = await session.execute(contracts_query)
        contracts = contracts_result.scalars().all()
        
        if not users or not objects or not contracts:
            print("❌ Недостаточно данных для создания отзывов")
            return
        
        print(f"📊 Найдено: {len(users)} пользователей, {len(objects)} объектов, {len(contracts)} договоров")
        
        # Создаем тестовые отзывы
        test_reviews = [
            {
                "title": "Отличный сотрудник",
                "content": "Очень ответственный и пунктуальный. Всегда приходит вовремя и качественно выполняет работу.",
                "rating": 5.0,
                "target_type": "employee",
                "is_anonymous": False
            },
            {
                "title": "Хорошие условия работы",
                "content": "Удобное расположение, хорошая атмосфера в коллективе. Рекомендую этот объект для работы.",
                "rating": 4.5,
                "target_type": "object",
                "is_anonymous": True
            },
            {
                "title": "Профессиональный подход",
                "content": "Сотрудник демонстрирует высокий уровень профессионализма и внимательность к деталям.",
                "rating": 4.0,
                "target_type": "employee",
                "is_anonymous": False
            },
            {
                "title": "Удобное место работы",
                "content": "Объект расположен в удобном месте, есть все необходимые условия для комфортной работы.",
                "rating": 4.5,
                "target_type": "object",
                "is_anonymous": True
            },
            {
                "title": "Ответственный работник",
                "content": "Всегда выполняет поставленные задачи в срок и с высоким качеством.",
                "rating": 5.0,
                "target_type": "employee",
                "is_anonymous": False
            }
        ]
        
        created_reviews = []
        
        for i, review_data in enumerate(test_reviews):
            # Выбираем случайного пользователя-владельца для отзывов о сотрудниках
            # или сотрудника для отзывов об объектах
            if review_data["target_type"] == "employee":
                reviewer = random.choice([u for u in users if u.role == "owner"])
                target = random.choice([u for u in users if u.role == "employee"])
            else:
                reviewer = random.choice([u for u in users if u.role == "employee"])
                target = random.choice(objects)
            
            # Выбираем случайный договор
            contract = random.choice(contracts)
            
            # Создаем отзыв
            review = Review(
                reviewer_id=reviewer.id,
                target_type=review_data["target_type"],
                target_id=target.id,
                contract_id=contract.id,
                rating=review_data["rating"],
                title=review_data["title"],
                content=review_data["content"],
                status=ReviewStatus.APPROVED.value,
                is_anonymous=review_data["is_anonymous"],
                created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
                published_at=datetime.now() - timedelta(days=random.randint(1, 25))
            )
            
            session.add(review)
            created_reviews.append(review)
        
        await session.commit()
        
        print(f"✅ Создано {len(created_reviews)} тестовых отзывов")
        
        # Создаем рейтинги
        await create_ratings(session, created_reviews)
        
        print("🎉 Тестовые данные созданы успешно!")

async def create_ratings(session: AsyncSession, reviews):
    """Создает рейтинги на основе отзывов."""
    from shared.services.rating_service import RatingService
    
    rating_service = RatingService(session)
    
    # Группируем отзывы по целям
    targets = {}
    for review in reviews:
        key = (review.target_type, review.target_id)
        if key not in targets:
            targets[key] = []
        targets[key].append(review)
    
    # Создаем рейтинги для каждой цели
    for (target_type, target_id), target_reviews in targets.items():
        # Рассчитываем средний рейтинг
        total_rating = sum(r.rating for r in target_reviews)
        average_rating = total_rating / len(target_reviews)
        
        # Создаем или обновляем рейтинг
        rating = await rating_service.get_or_create_rating(target_type, target_id)
        rating.average_rating = average_rating
        rating.total_reviews = len(target_reviews)
        rating.last_updated = datetime.now()
        
        session.add(rating)
    
    await session.commit()
    print(f"✅ Создано {len(targets)} рейтингов")

if __name__ == "__main__":
    asyncio.run(create_test_reviews())
