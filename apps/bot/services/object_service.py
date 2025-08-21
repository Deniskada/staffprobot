"""Сервис для работы с объектами."""

from typing import List, Dict, Any, Optional
from datetime import time
from core.logging.logger import logger
from core.database.connection import get_sync_session
from core.geolocation.location_validator import LocationValidator
from domain.entities.object import Object
from domain.entities.user import User
from sqlalchemy import select


class ObjectService:
    """Сервис для работы с объектами."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self.location_validator = LocationValidator()
        logger.info("ObjectService initialized")
    
    def create_object(
        self,
        name: str,
        address: str,
        coordinates: str,
        opening_time: str,
        closing_time: str,
        hourly_rate: float,
        owner_id: int
    ) -> Dict[str, Any]:
        """
        Создает новый объект.
        
        Args:
            name: Название объекта
            address: Адрес объекта
            coordinates: Координаты в формате 'lat,lon'
            opening_time: Время открытия в формате 'HH:MM'
            closing_time: Время закрытия в формате 'HH:MM'
            hourly_rate: Часовая ставка
            owner_id: ID владельца объекта (telegram_id)
            
        Returns:
            Результат создания объекта
        """
        try:
            # Валидируем координаты
            coord_validation = self.location_validator.validate_coordinates(coordinates)
            if not coord_validation['valid']:
                return {
                    'success': False,
                    'error': f"Ошибка координат: {coord_validation['error']}"
                }
            
            # Валидируем время
            try:
                opening_time_obj = time.fromisoformat(opening_time)
                closing_time_obj = time.fromisoformat(closing_time)
            except ValueError:
                return {
                    'success': False,
                    'error': 'Неверный формат времени. Используйте HH:MM (например: 09:00)'
                }
            
            # Проверяем, что время закрытия после времени открытия
            if closing_time_obj <= opening_time_obj:
                return {
                    'success': False,
                    'error': 'Время закрытия должно быть позже времени открытия'
                }
            
            with get_sync_session() as session:
                # Находим пользователя по telegram_id для получения его id в БД
                
                user_query = select(User).where(User.telegram_id == owner_id)
                user_result = session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден в базе данных. Обратитесь к администратору.'
                    }
                
                # Создаем объект
                new_object = Object(
                    name=name,
                    address=address,
                    coordinates=coordinates,
                    opening_time=opening_time_obj,
                    closing_time=closing_time_obj,
                    hourly_rate=hourly_rate,
                    owner_id=db_user.id,  # Используем id из БД, а не telegram_id
                    is_active=True
                )
                
                session.add(new_object)
                session.commit()
                session.refresh(new_object)
                
                logger.info(
                    f"Object created successfully: {name} (ID: {new_object.id}, owner: {owner_id})"
                )
                
                return {
                    'success': True,
                    'object_id': new_object.id,
                    'message': f'Объект "{name}" успешно создан!'
                }
                
        except Exception as e:
            logger.error(f"Error creating object: {e}")
            return {
                'success': False,
                'error': f'Ошибка при создании объекта: {str(e)}'
            }
    
    def get_all_objects(self) -> List[Dict[str, Any]]:
        """
        Получает все объекты из базы данных.
        
        Returns:
            Список объектов
        """
        try:
            with get_sync_session() as session:
                # Получаем все объекты
                query = select(Object).where(Object.is_active == True)
                result = session.execute(query)
                objects = result.scalars().all()
                
                # Преобразуем в словари
                objects_list = []
                for obj in objects:
                    objects_list.append({
                        'id': obj.id,
                        'name': obj.name,
                        'address': obj.address,
                        'coordinates': obj.coordinates,
                        'hourly_rate': float(obj.hourly_rate) if obj.hourly_rate else 0.0,
                        'opening_time': obj.opening_time.strftime('%H:%M') if obj.opening_time else None,
                        'closing_time': obj.closing_time.strftime('%H:%M') if obj.closing_time else None,
                        'is_active': obj.is_active,
                        'created_at': obj.created_at.isoformat() if obj.created_at else None,
                        'max_distance_meters': obj.max_distance_meters or 500
                    })
                
                logger.info(
                    f"Objects retrieved successfully: {len(objects_list)} objects"
                )
                
                return objects_list
                
        except Exception as e:
            logger.error(f"Error retrieving objects: {e}")
        return []
    
    def get_object_by_id(self, object_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает объект по ID.
        
        Args:
            object_id: ID объекта
            
        Returns:
            Данные объекта или None
        """
        try:
            with get_sync_session() as session:
                query = select(Object).where(Object.id == object_id)
                result = session.execute(query)
                obj = result.scalar_one_or_none()
                
                if not obj:
                    return None
                
                return {
                    'id': obj.id,
                    'name': obj.name,
                    'address': obj.address,
                    'coordinates': obj.coordinates,
                    'hourly_rate': float(obj.hourly_rate) if obj.hourly_rate else 0.0,
                    'opening_time': obj.opening_time.strftime('%H:%M') if obj.opening_time else None,
                    'closing_time': obj.closing_time.strftime('%H:%M') if obj.closing_time else None,
                    'is_active': obj.is_active,
                    'created_at': obj.created_at.isoformat() if obj.created_at else None,
                    'max_distance_meters': obj.max_distance_meters or 500
                }
                
        except Exception as e:
            logger.error(f"Error retrieving object {object_id}: {e}")
        return None
    
    def get_user_objects(self, owner_id: int) -> List[Dict[str, Any]]:
        """
        Получает все объекты пользователя.
        
        Args:
            owner_id: Telegram ID владельца
            
        Returns:
            Список объектов пользователя
        """
        try:
            with get_sync_session() as session:
                
                # Получаем пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == owner_id)
                user_result = session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    logger.warning(f"User {owner_id} not found in database")
                    return []
                
                # Получаем объекты пользователя
                query = select(Object).where(
                    Object.owner_id == db_user.id,
                    Object.is_active == True
                )
                result = session.execute(query)
                objects = result.scalars().all()
                
                # Преобразуем в словари
                objects_list = []
                for obj in objects:
                    objects_list.append({
                        'id': obj.id,
                        'name': obj.name,
                        'address': obj.address,
                        'coordinates': obj.coordinates,
                        'hourly_rate': float(obj.hourly_rate) if obj.hourly_rate else 0.0,
                        'opening_time': obj.opening_time.strftime('%H:%M') if obj.opening_time else None,
                        'closing_time': obj.closing_time.strftime('%H:%M') if obj.closing_time else None,
                        'is_active': obj.is_active,
                        'created_at': obj.created_at.isoformat() if obj.created_at else None,
                        'max_distance_meters': obj.max_distance_meters or 500
                    })
                
                logger.info(f"User objects retrieved: user_id={owner_id}, count={len(objects_list)}")
                return objects_list
                
        except Exception as e:
            logger.error(f"Error retrieving user objects for {owner_id}: {e}")
        return []
    
    def update_object_field(self, object_id: int, field_name: str, field_value, owner_id: int) -> Dict[str, Any]:
        """
        Обновляет конкретное поле объекта.
        
        Args:
            object_id: ID объекта
            field_name: Название поля для обновления
            field_value: Новое значение поля
            owner_id: ID владельца (для проверки прав)
            
        Returns:
            Результат обновления
        """
        try:
            with get_sync_session() as session:
                # Получаем пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == owner_id)
                user_result = session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    return {
                        'success': False,
                        'error': 'Пользователь не найден в базе данных'
                    }
                
                # Получаем объект
                query = select(Object).where(Object.id == object_id)
                result = session.execute(query)
                obj = result.scalar_one_or_none()
                
                if not obj:
                    return {
                        'success': False,
                        'error': 'Объект не найден'
                    }
                
                # Проверяем права доступа
                if obj.owner_id != db_user.id:
                    return {
                        'success': False,
                        'error': 'У вас нет прав для редактирования этого объекта'
                    }
                
                # Обновляем поле
                if field_name == 'max_distance_meters':
                    try:
                        distance = int(field_value)
                        if distance < 10 or distance > 5000:
                            return {
                                'success': False,
                                'error': 'Максимальное расстояние должно быть от 10 до 5000 метров'
                            }
                        obj.max_distance_meters = distance
                    except ValueError:
                        return {
                            'success': False,
                            'error': 'Неверное значение расстояния. Введите число.'
                        }
                elif field_name == 'name':
                    if not field_value or len(field_value.strip()) < 1:
                        return {
                            'success': False,
                            'error': 'Название объекта не может быть пустым'
                        }
                    obj.name = field_value.strip()
                elif field_name == 'address':
                    obj.address = field_value.strip() if field_value else None
                elif field_name == 'hourly_rate':
                    try:
                        rate = float(field_value)
                        if rate <= 0:
                            return {
                                'success': False,
                                'error': 'Часовая ставка должна быть больше 0'
                            }
                        obj.hourly_rate = rate
                    except ValueError:
                        return {
                            'success': False,
                            'error': 'Неверное значение часовой ставки. Введите число.'
                        }
                else:
                    return {
                        'success': False,
                        'error': f'Поле "{field_name}" не поддерживается для редактирования'
                    }
                
                session.commit()
                
                logger.info(f"Object {object_id} field {field_name} updated to {field_value} by user {owner_id}")
                
                return {
                    'success': True,
                    'message': f'Поле "{field_name}" успешно обновлено',
                    'object_id': object_id,
                    'field_name': field_name,
                    'new_value': field_value
                }
                
        except Exception as e:
            logger.error(f"Error updating object {object_id}: {e}")
            return {
                'success': False,
                'error': f'Ошибка при обновлении объекта: {str(e)}'
            }







