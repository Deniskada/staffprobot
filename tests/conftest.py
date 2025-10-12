"""Корневой conftest для всех тестов с поддержкой БД."""

import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from domain.entities import Base


# Используем тестовую БД (используем dev БД для интеграционных тестов)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@postgres:5432/staffprobot_dev"


@pytest.fixture(scope="session")
def event_loop():
    """Создать event loop для всей сессии тестов."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Создать тестовый движок БД."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Создать все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Удалить все таблицы после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    """Создать сессию БД для каждого теста."""
    async_session_maker = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        # Откат всех изменений после теста
        await session.rollback()

