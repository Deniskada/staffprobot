"""Сервис для логики входа и переключения интерфейсов на основе ролей."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from shared.services.role_service import RoleService
from domain.entities.user import UserRole
from core.logging.logger import logger


class RoleBasedLoginService:
    """Сервис для логики входа и переключения интерфейсов."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.role_service = RoleService(session)
    
    async def get_available_interfaces(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение доступных интерфейсов для пользователя."""
        try:
            interfaces = await self.role_service.get_available_interfaces(user_id)
            
            interface_info = []
            for interface in interfaces:
                info = self._get_interface_info(interface)
                if info:
                    interface_info.append(info)
            
            return interface_info
            
        except Exception as e:
            logger.error(f"Failed to get available interfaces for user {user_id}: {e}")
            return []
    
    def _get_interface_info(self, interface: str) -> Optional[Dict[str, Any]]:
        """Получение информации об интерфейсе."""
        interface_map = {
            "admin": {
                "name": "admin",
                "title": "Администратор",
                "description": "Полный доступ к системе",
                "icon": "👑",
                "url": "/admin/dashboard",
                "priority": 1
            },
            "owner": {
                "name": "owner",
                "title": "Владелец",
                "description": "Управление объектами и сотрудниками",
                "icon": "🏢",
                "url": "/owner/dashboard",
                "priority": 2
            },
            "manager": {
                "name": "manager",
                "title": "Управляющий",
                "description": "Управление по правам",
                "icon": "👨‍💼",
                "url": "/manager/dashboard",
                "priority": 3
            },
            "employee": {
                "name": "employee",
                "title": "Сотрудник",
                "description": "Работа на объектах",
                "icon": "👷",
                "url": "/employee/",
                "priority": 4
            }
        }
        
        return interface_map.get(interface)
    
    async def get_primary_interface(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение основного интерфейса для пользователя."""
        try:
            primary_interface = await self.role_service.get_primary_interface(user_id)
            if primary_interface:
                return self._get_interface_info(primary_interface)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get primary interface for user {user_id}: {e}")
            return None
    
    async def can_switch_to_interface(self, user_id: int, interface: str) -> bool:
        """Проверка возможности переключения на интерфейс."""
        try:
            available_interfaces = await self.role_service.get_available_interfaces(user_id)
            return interface in available_interfaces
            
        except Exception as e:
            logger.error(f"Failed to check interface switch for user {user_id}: {e}")
            return False
    
    async def get_interface_switcher_data(self, user_id: int, current_interface: str) -> Dict[str, Any]:
        """Получение данных для компонента переключения интерфейсов."""
        try:
            available_interfaces = await self.get_available_interfaces(user_id)
            primary_interface = await self.get_primary_interface(user_id)
            
            return {
                "current_interface": current_interface,
                "available_interfaces": available_interfaces,
                "primary_interface": primary_interface,
                "can_switch": len(available_interfaces) > 1
            }
            
        except Exception as e:
            logger.error(f"Failed to get interface switcher data for user {user_id}: {e}")
            return {
                "current_interface": current_interface,
                "available_interfaces": [],
                "primary_interface": None,
                "can_switch": False
            }
    
    async def get_role_based_navigation(self, user_id: int, current_interface: str) -> List[Dict[str, Any]]:
        """Получение навигации на основе роли пользователя."""
        try:
            user_roles = await self.role_service.get_user_roles(user_id)
            
            navigation_items = []
            
            # Администратор
            if UserRole.SUPERADMIN.value in user_roles:
                navigation_items.extend([
                    {"name": "Пользователи", "url": "/admin/users", "icon": "👥"},
                    {"name": "Система", "url": "/admin/system", "icon": "⚙️"},
                    {"name": "Мониторинг", "url": "/admin/monitoring", "icon": "📊"}
                ])
            
            # Владелец
            if UserRole.OWNER.value in user_roles:
                navigation_items.extend([
                    {"name": "Объекты", "url": "/owner/objects", "icon": "🏢"},
                    {"name": "Сотрудники", "url": "/owner/employees", "icon": "👥"},
                    {"name": "Календарь", "url": "/owner/calendar", "icon": "📅"},
                    {"name": "Отчеты", "url": "/owner/reports", "icon": "📊"},
                    {"name": "Договоры", "url": "/owner/contracts", "icon": "📋"}
                ])
            
            # Управляющий
            if UserRole.MANAGER.value in user_roles:
                navigation_items.extend([
                    {"name": "Объекты", "url": "/manager/objects", "icon": "🏢"},
                    {"name": "Сотрудники", "url": "/manager/employees", "icon": "👥"},
                    {"name": "Календарь", "url": "/manager/calendar", "icon": "📅"},
                    {"name": "Отчеты", "url": "/manager/reports", "icon": "📊"}
                ])
            
            # Сотрудник/Соискатель
            if UserRole.EMPLOYEE.value in user_roles or UserRole.APPLICANT.value in user_roles:
                navigation_items.extend([
                    {"name": "Мои смены", "url": "/employee/shifts", "icon": "⏰"},
                    {"name": "Объекты", "url": "/employee/objects", "icon": "🏢"},
                    {"name": "Отчеты", "url": "/employee/reports", "icon": "📊"}
                ])
            
            return navigation_items
            
        except Exception as e:
            logger.error(f"Failed to get role-based navigation for user {user_id}: {e}")
            return []
    
    async def get_user_dashboard_data(self, user_id: int, interface: str) -> Dict[str, Any]:
        """Получение данных для дашборда пользователя."""
        try:
            user_roles = await self.role_service.get_user_roles(user_id)
            
            dashboard_data = {
                "user_id": user_id,
                "roles": user_roles,
                "interface": interface,
                "available_interfaces": await self.get_available_interfaces(user_id),
                "navigation": await self.get_role_based_navigation(user_id, interface)
            }
            
            # Добавляем специфичные данные для каждого интерфейса
            if interface == "admin":
                dashboard_data.update(await self._get_admin_dashboard_data(user_id))
            elif interface == "owner":
                dashboard_data.update(await self._get_owner_dashboard_data(user_id))
            elif interface == "manager":
                dashboard_data.update(await self._get_manager_dashboard_data(user_id))
            elif interface == "employee":
                dashboard_data.update(await self._get_employee_dashboard_data(user_id))
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data for user {user_id}: {e}")
            return {}
    
    async def _get_admin_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Данные для дашборда администратора."""
        # Здесь можно добавить специфичные данные для админа
        return {
            "title": "Панель администратора",
            "description": "Управление системой"
        }
    
    async def _get_owner_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Данные для дашборда владельца."""
        # Здесь можно добавить специфичные данные для владельца
        return {
            "title": "Панель владельца",
            "description": "Управление объектами и сотрудниками"
        }
    
    async def _get_manager_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Данные для дашборда управляющего."""
        # Здесь можно добавить специфичные данные для управляющего
        return {
            "title": "Панель управляющего",
            "description": "Управление по правам"
        }
    
    async def _get_employee_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Данные для дашборда сотрудника."""
        # Здесь можно добавить специфичные данные для сотрудника
        return {
            "title": "Панель сотрудника",
            "description": "Работа на объектах"
        }
