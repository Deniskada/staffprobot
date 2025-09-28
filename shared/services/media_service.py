"""
Сервис для работы с медиа-файлами в системе отзывов.

Обеспечивает загрузку, валидацию и обработку медиа-файлов для отзывов.
"""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.logging.logger import logger
from domain.entities.review import ReviewMedia


class MediaService:
    """Сервис для работы с медиа-файлами."""
    
    # Ограничения размеров файлов (в байтах)
    MAX_SIZES = {
        'photo': 5 * 1024 * 1024,      # 5MB
        'video': 50 * 1024 * 1024,     # 50MB
        'audio': 20 * 1024 * 1024,     # 20MB
        'document': 10 * 1024 * 1024   # 10MB
    }
    
    # Разрешенные MIME-типы
    ALLOWED_MIME_TYPES = {
        'photo': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'video': ['video/mp4', 'video/avi', 'video/mov', 'video/webm'],
        'audio': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp3'],
        'document': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    }
    
    def __init__(self, upload_dir: str = "uploads/media"):
        """Инициализация сервиса."""
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем подпапки для разных типов файлов
        for file_type in self.MAX_SIZES.keys():
            (self.upload_dir / file_type).mkdir(exist_ok=True)
    
    async def validate_file(self, file: UploadFile, file_type: str) -> bool:
        """
        Валидация файла.
        
        Args:
            file: Загружаемый файл
            file_type: Тип файла (photo, video, audio, document)
            
        Returns:
            bool: True если файл валиден
            
        Raises:
            HTTPException: Если файл не прошел валидацию
        """
        if file_type not in self.MAX_SIZES:
            raise HTTPException(status_code=400, detail=f"Неподдерживаемый тип файла: {file_type}")
        
        # Проверка MIME-типа
        if file.content_type not in self.ALLOWED_MIME_TYPES[file_type]:
            raise HTTPException(
                status_code=400, 
                detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(self.ALLOWED_MIME_TYPES[file_type])}"
            )
        
        # Читаем содержимое файла для проверки размера
        content = await file.read()
        file_size = len(content)
        
        # Проверка размера
        if file_size > self.MAX_SIZES[file_type]:
            max_size_mb = self.MAX_SIZES[file_type] / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"Размер файла превышает максимальный ({max_size_mb:.1f}MB)"
            )
        
        # Возвращаем указатель файла в начало
        await file.seek(0)
        
        return True
    
    async def save_file(self, file: UploadFile, file_type: str, review_id: int) -> Dict[str, Any]:
        """
        Сохранение файла на диск.
        
        Args:
            file: Загружаемый файл
            file_type: Тип файла
            review_id: ID отзыва
            
        Returns:
            Dict с информацией о сохраненном файле
        """
        # Валидация файла
        await self.validate_file(file, file_type)
        
        # Генерируем уникальное имя файла
        file_extension = Path(file.filename).suffix if file.filename else ''
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Путь для сохранения
        file_path = self.upload_dir / file_type / unique_filename
        
        # Сохраняем файл
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Получаем MIME-тип
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = file.content_type
        
        return {
            "file_path": str(file_path),
            "file_size": len(content),
            "mime_type": mime_type,
            "original_filename": file.filename,
            "unique_filename": unique_filename
        }
    
    async def create_review_media(
        self, 
        session: AsyncSession, 
        review_id: int, 
        file_info: Dict[str, Any],
        file_type: str,
        is_primary: bool = False
    ) -> ReviewMedia:
        """
        Создание записи медиа-файла в базе данных.
        
        Args:
            session: Сессия базы данных
            review_id: ID отзыва
            file_info: Информация о файле
            file_type: Тип файла
            is_primary: Является ли файл основным
            
        Returns:
            ReviewMedia: Созданная запись
        """
        review_media = ReviewMedia(
            review_id=review_id,
            file_type=file_type,
            file_path=file_info["file_path"],
            file_size=file_info["file_size"],
            mime_type=file_info["mime_type"],
            is_primary=is_primary
        )
        
        session.add(review_media)
        await session.commit()
        await session.refresh(review_media)
        
        logger.info(f"Created review media: {review_media.id} for review {review_id}")
        
        return review_media
    
    async def upload_files(
        self, 
        session: AsyncSession, 
        files: List[UploadFile], 
        review_id: int
    ) -> List[ReviewMedia]:
        """
        Загрузка множественных файлов.
        
        Args:
            session: Сессия базы данных
            files: Список файлов для загрузки
            review_id: ID отзыва
            
        Returns:
            List[ReviewMedia]: Список созданных записей медиа
        """
        if not files:
            return []
        
        uploaded_media = []
        
        for i, file in enumerate(files):
            # Определяем тип файла по MIME-типу
            file_type = self._get_file_type_from_mime(file.content_type)
            if not file_type:
                logger.warning(f"Unknown file type: {file.content_type}")
                continue
            
            try:
                # Сохраняем файл
                file_info = await self.save_file(file, file_type, review_id)
                
                # Создаем запись в БД
                is_primary = (i == 0)  # Первый файл считается основным
                review_media = await self.create_review_media(
                    session, review_id, file_info, file_type, is_primary
                )
                
                uploaded_media.append(review_media)
                
            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {e}")
                continue
        
        return uploaded_media
    
    def _get_file_type_from_mime(self, mime_type: str) -> Optional[str]:
        """Определение типа файла по MIME-типу."""
        for file_type, allowed_mimes in self.ALLOWED_MIME_TYPES.items():
            if mime_type in allowed_mimes:
                return file_type
        return None
    
    async def delete_file(self, session: AsyncSession, media_id: int) -> bool:
        """
        Удаление медиа-файла.
        
        Args:
            session: Сессия базы данных
            media_id: ID медиа-файла
            
        Returns:
            bool: True если файл успешно удален
        """
        # Получаем информацию о файле
        query = select(ReviewMedia).where(ReviewMedia.id == media_id)
        result = await session.execute(query)
        media = result.scalar_one_or_none()
        
        if not media:
            return False
        
        try:
            # Удаляем файл с диска
            file_path = Path(media.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Удаляем запись из БД
            await session.delete(media)
            await session.commit()
            
            logger.info(f"Deleted media file: {media_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting media file {media_id}: {e}")
            await session.rollback()
            return False
    
    async def get_media_by_review(self, session: AsyncSession, review_id: int) -> List[ReviewMedia]:
        """
        Получение всех медиа-файлов отзыва.
        
        Args:
            session: Сессия базы данных
            review_id: ID отзыва
            
        Returns:
            List[ReviewMedia]: Список медиа-файлов
        """
        query = select(ReviewMedia).where(ReviewMedia.review_id == review_id).order_by(ReviewMedia.is_primary.desc())
        result = await session.execute(query)
        return result.scalars().all()
    
    def get_file_url(self, media: ReviewMedia) -> str:
        """
        Получение URL для доступа к файлу.
        
        Args:
            media: Медиа-файл
            
        Returns:
            str: URL файла
        """
        # Возвращаем относительный путь от корня приложения
        return f"/static/media/{Path(media.file_path).name}"
    
    async def generate_preview(self, media: ReviewMedia) -> Optional[str]:
        """
        Генерация превью для видео и изображений.
        
        Args:
            media: Медиа-файл
            
        Returns:
            Optional[str]: Путь к превью или None
        """
        # TODO: Реализовать генерацию превью
        # Для изображений - создание миниатюры
        # Для видео - извлечение кадра
        return None
