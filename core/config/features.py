"""
Централизованный справочник функций системы.

Определяет все дополнительные функции, которые могут быть включены/выключены
владельцем и привязаны к тарифным планам.
"""

from typing import Dict, List, TypedDict


class FeatureDefinition(TypedDict):
    """Определение функции системы."""
    name: str
    description: str
    menu_items: List[str]
    form_elements: List[str]
    sort_order: int


# Централизованный реестр функций системы
SYSTEM_FEATURES_REGISTRY: Dict[str, FeatureDefinition] = {
    'recruitment_and_reviews': {
        'name': 'Найм сотрудников, отзывы и рейтинги',
        'description': 'Публикация вакансий, приём откликов, система отзывов и рейтингов сотрудников. Привлекайте лучших кандидатов и управляйте репутацией.',
        'menu_items': ['applications', 'reviews'],
        'form_elements': [],
        'sort_order': 1
    },
    'telegram_bot': {
        'name': 'Telegram-бот',
        'description': 'Полнофункциональный бот для управления сменами и коммуникации с сотрудниками. Доступ к системе прямо из мессенджера.',
        'menu_items': [],
        'form_elements': [],
        'sort_order': 2
    },
    'notifications': {
        'name': 'Уведомления',
        'description': 'Система уведомлений о важных событиях: начало смены, опоздания, отмены. Будьте в курсе всего происходящего.',
        'menu_items': [],
        'form_elements': [],
        'sort_order': 3
    },
    'basic_reports': {
        'name': 'Базовые отчёты',
        'description': 'Отчёты по сменам, сотрудникам и объектам. Контролируйте основные показатели работы.',
        'menu_items': ['reports'],
        'form_elements': [],
        'sort_order': 4
    },
    'shared_calendar': {
        'name': 'Общий календарь',
        'description': 'Календарное представление смен и событий. Визуализация расписания для удобного планирования.',
        'menu_items': ['calendar'],
        'form_elements': [],
        'sort_order': 5
    },
    'payroll': {
        'name': 'Штатное расписание, начисления, выплаты',
        'description': 'Управление штатным расписанием, автоматические начисления и выплаты. Полный контроль финансов персонала.',
        'menu_items': ['planning_shifts', 'planning_departments', 'planning_schedule'],
        'form_elements': ['employee_time_slot'],
        'sort_order': 6
    },
    'contract_templates': {
        'name': 'Шаблоны договоров',
        'description': 'Создание и управление шаблонами договоров с динамическими полями. Автоматизируйте оформление документов.',
        'menu_items': ['planning_contracts'],
        'form_elements': ['object_contract_template'],
        'sort_order': 7
    },
    'bonuses_and_penalties': {
        'name': 'Начисления премий и штрафов',
        'description': 'Система начисления премий и штрафов сотрудникам. Мотивируйте команду и контролируйте дисциплину.',
        'menu_items': ['payroll_payouts', 'payroll_accruals'],
        'form_elements': ['employee_bonus_penalty'],
        'sort_order': 8
    },
    'shift_tasks': {
        'name': 'Задачи сотрудникам на смену',
        'description': 'Назначение и контроль выполнения задач на смене. Управляйте рабочими процессами и отслеживайте отмены.',
        'menu_items': ['moderation_cancellations', 'analytics_cancellations'],
        'form_elements': ['shift_tasks_section'],
        'sort_order': 9
    },
    'analytics': {
        'name': 'Аналитика',
        'description': 'Расширенная аналитика и визуализация данных. Принимайте решения на основе статистики.',
        'menu_items': ['analytics'],
        'form_elements': [],
        'sort_order': 10
    }
}


def get_feature_by_key(key: str) -> FeatureDefinition:
    """Получить определение функции по ключу."""
    return SYSTEM_FEATURES_REGISTRY.get(key)


def get_all_features() -> Dict[str, FeatureDefinition]:
    """Получить все функции системы."""
    return SYSTEM_FEATURES_REGISTRY


def get_features_sorted() -> List[tuple[str, FeatureDefinition]]:
    """Получить функции, отсортированные по sort_order."""
    return sorted(
        SYSTEM_FEATURES_REGISTRY.items(),
        key=lambda x: x[1]['sort_order']
    )


def get_feature_keys() -> List[str]:
    """Получить список всех ключей функций."""
    return list(SYSTEM_FEATURES_REGISTRY.keys())


def is_valid_feature_key(key: str) -> bool:
    """Проверить, является ли ключ валидным."""
    return key in SYSTEM_FEATURES_REGISTRY

