"""
Фабрика для создания сессий базы данных
"""

import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from core.config.settings import settings
from core.logging.logger import logger


class DatabaseManager:
    """Менеджер базы данных для создания сессий."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Инициализирует подключение к базе данных."""
        if self._initialized:
            return
        
        try:
            # Создаем async engine
            database_url = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            
            self.engine = create_async_engine(
                database_url,
                echo=settings.debug,
                poolclass=NullPool,  # Отключаем пул для простоты
                future=True
            )
            
            # Создаем фабрику сессий
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self._initialized = True
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    async def close(self):
        """Закрывает подключение к базе данных."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connection closed")
    
    def get_session(self) -> AsyncSession:
        """Возвращает новую сессию базы данных."""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.session_factory()
    
    async def get_session_async(self) -> AsyncGenerator[AsyncSession, None]:
        """Асинхронный генератор для получения сессий."""
        session = self.get_session()
        try:
            yield session
        finally:
            await session.close()


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД."""
    async for session in db_manager.get_session_async():
        yield session


async def init_database():
    """Инициализирует базу данных."""
    await db_manager.initialize()


async def close_database():
    """Закрывает подключение к базе данных."""
    await db_manager.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Асинхронный контекстный менеджер для получения сессии БД.

    Обеспечивает ленивую инициализацию подключения и корректное закрытие сессии.
    Использование:
        async with get_async_session() as session:
            ...
    """
    if not db_manager._initialized:  # type: ignore[attr-defined]
        await db_manager.initialize()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        await session.close()
