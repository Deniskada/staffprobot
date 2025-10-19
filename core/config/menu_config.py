"""
Конфигурация меню владельца с привязкой к функциям.

Определяет структуру меню и зависимости от функций системы.
"""

from typing import List, Dict, Any, Optional


class MenuConfig:
    """Конфигурация меню владельца."""
    
    # Маппинг пунктов меню на функции
    # Пункт меню отображается, если хотя бы одна из указанных функций включена
    MENU_ITEMS_FEATURES_MAP = {
        'objects': ['recruitment_and_reviews', 'telegram_bot', 'notifications', 'basic_reports'],
        'employees': ['recruitment_and_reviews', 'telegram_bot', 'notifications', 'basic_reports'],
        'reports': ['recruitment_and_reviews', 'telegram_bot', 'notifications', 'basic_reports'],
        'analytics': ['recruitment_and_reviews', 'telegram_bot', 'notifications', 'basic_reports', 'analytics'],
        'calendar': ['shared_calendar'],
        'planning': ['payroll'],
        'planning_shifts': ['payroll'],
        'planning_departments': ['payroll'],
        'planning_schedule': ['payroll'],
        'planning_contracts': ['contract_templates'],
        'payroll_menu': ['bonuses_and_penalties', 'shift_tasks'],
        'payroll_payouts': ['bonuses_and_penalties'],
        'payroll_accruals': ['bonuses_and_penalties'],
        'moderation_cancellations': ['shift_tasks'],
        'analytics_cancellations': ['shift_tasks'],
        'applications': ['recruitment_and_reviews', 'telegram_bot', 'notifications', 'basic_reports'],
        'reviews': ['recruitment_and_reviews', 'telegram_bot', 'notifications', 'basic_reports'],
        # Настройки всегда видны
        'settings': [],
        'profile': [],
        'tariff': [],
        'limits': [],
    }
    
    @classmethod
    def is_menu_item_visible(
        cls,
        menu_item_key: str,
        enabled_features: List[str]
    ) -> bool:
        """
        Проверить, должен ли пункт меню отображаться.
        
        Args:
            menu_item_key: Ключ пункта меню
            enabled_features: Список включенных функций пользователя
            
        Returns:
            True если пункт меню должен отображаться
        """
        # Если пункт не привязан к функциям, всегда отображаем
        if menu_item_key not in cls.MENU_ITEMS_FEATURES_MAP:
            return True
        
        required_features = cls.MENU_ITEMS_FEATURES_MAP[menu_item_key]
        
        # Если список функций пуст, пункт всегда видим
        if not required_features:
            return True
        
        # Проверяем, включена ли хотя бы одна из требуемых функций
        return any(feature in enabled_features for feature in required_features)
    
    @classmethod
    def get_visible_menu_items(
        cls,
        enabled_features: List[str]
    ) -> List[str]:
        """Получить список видимых пунктов меню."""
        visible = []
        for item_key in cls.MENU_ITEMS_FEATURES_MAP.keys():
            if cls.is_menu_item_visible(item_key, enabled_features):
                visible.append(item_key)
        return visible
    
    @classmethod
    def get_menu_structure(cls, enabled_features: List[str]) -> Dict[str, Any]:
        """
        Получить структуру меню с учётом видимости.
        
        Returns:
            Структура меню для использования в шаблонах
        """
        structure = {}
        
        # Основные пункты меню
        structure['objects'] = cls.is_menu_item_visible('objects', enabled_features)
        structure['employees'] = cls.is_menu_item_visible('employees', enabled_features)
        structure['reports'] = cls.is_menu_item_visible('reports', enabled_features)
        structure['analytics'] = cls.is_menu_item_visible('analytics', enabled_features)
        structure['calendar'] = cls.is_menu_item_visible('calendar', enabled_features)
        structure['applications'] = cls.is_menu_item_visible('applications', enabled_features)
        structure['reviews'] = cls.is_menu_item_visible('reviews', enabled_features)
        
        # Подменю "Планирование"
        planning_submenu = {
            'shifts': cls.is_menu_item_visible('planning_shifts', enabled_features),
            'departments': cls.is_menu_item_visible('planning_departments', enabled_features),
            'schedule': cls.is_menu_item_visible('planning_schedule', enabled_features),
            'contracts': cls.is_menu_item_visible('planning_contracts', enabled_features),
        }
        structure['planning'] = {
            'visible': any(planning_submenu.values()),
            'submenu': planning_submenu
        }
        
        # Подменю "Зарплаты и премии"
        payroll_submenu = {
            'payouts': cls.is_menu_item_visible('payroll_payouts', enabled_features),
            'accruals': cls.is_menu_item_visible('payroll_accruals', enabled_features),
            'moderation': cls.is_menu_item_visible('moderation_cancellations', enabled_features),
            'analytics': cls.is_menu_item_visible('analytics_cancellations', enabled_features),
        }
        structure['payroll'] = {
            'visible': any(payroll_submenu.values()),
            'submenu': payroll_submenu
        }
        
        # Настройки всегда видны
        structure['settings'] = True
        
        return structure

