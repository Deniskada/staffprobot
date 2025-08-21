"""Настройки подключения к базе данных."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Optional
from core.config.settings import settings
from core.logging.logger import logger


class DatabaseManager:
    """Менеджер подключений к базе данных."""
    
    def __init__(self):
        self._sync_engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_session_factory: Optional[sessionmaker] = None
        self._async_session_factory = None  # Убираем типизацию для MVP
    
    @property
    def sync_engine(self) -> Engine:
        """Синхронный движок базы данных."""
        if self._sync_engine is None:
            self._sync_engine = self._create_sync_engine()
        return self._sync_engine
    
    @property
    def async_engine(self) -> AsyncEngine:
        """Асинхронный движок базы данных."""
        if self._async_engine is None:
            self._async_engine = self._create_async_engine()
        return self._async_engine
    
    @property
    def sync_session_factory(self) -> sessionmaker:
        """Фабрика синхронных сессий."""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._sync_session_factory
    
    @property
    def async_session_factory(self):
        """Фабрика асинхронных сессий."""
        if self._async_session_factory is None:
            # Для MVP используем простую заглушку
            self._async_session_factory = None
        return self._async_session_factory
    
    def _create_sync_engine(self) -> Engine:
        """Создание синхронного движка."""
        try:
            engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                echo=settings.database_echo,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            logger.info(
                f"Sync database engine created successfully (pool_size={settings.database_pool_size}, max_overflow={settings.database_max_overflow})"
            )
            
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create sync database engine: {e}")
            raise
    
    def _create_async_engine(self) -> AsyncEngine:
        """Создание асинхронного движка."""
        try:
            # Конвертация URL для async
            async_url = settings.database_url.replace(
                'postgresql://', 'postgresql+asyncpg://'
            )
            
            engine = create_async_engine(
                async_url,
                poolclass=QueuePool,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                echo=settings.database_echo,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            logger.info(
                f"Async database engine created successfully (pool_size={settings.database_pool_size}, max_overflow={settings.database_max_overflow})"
            )
            
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create async database engine: {e}")
            raise
    
    def get_sync_session(self) -> Session:
        """Получение синхронной сессии."""
        return self.sync_session_factory()
    
    async def get_async_session(self) -> AsyncSession:
        """Получение асинхронной сессии."""
        # Для MVP возвращаем заглушку
        raise NotImplementedError("Async sessions not implemented in MVP")
    
    def close(self):
        """Закрытие всех подключений."""
        if self._sync_engine:
            self._sync_engine.dispose()
            logger.info("Sync database engine disposed")
        
        if self._async_engine:
            # Асинхронный движок закроется автоматически
            pass


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()


def get_sync_session() -> Session:
    """Получение синхронной сессии."""
    return db_manager.get_sync_session()


async def get_async_session() -> AsyncSession:
    """Получение асинхронной сессии."""
    # Для MVP возвращаем заглушку
    raise NotImplementedError("Async sessions not implemented in MVP")


def close_db_connections():
    """Закрытие всех подключений к БД."""
    db_manager.close()


