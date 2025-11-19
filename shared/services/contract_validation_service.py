"""Сервис для валидации активности контрактов с учётом даты увольнения."""

from datetime import date
from typing import Optional

from domain.entities.contract import Contract
from sqlalchemy import and_, or_


def is_contract_active_for_work(contract: Contract, check_date: Optional[date] = None) -> bool:
    """
    Проверяет, активен ли контракт для работы (открытие смен, планирование).
    
    Контракт активен, если:
    - status == 'active'
    - is_active == True
    - termination_date IS NULL ИЛИ termination_date > check_date
    
    Args:
        contract: Объект Contract
        check_date: Дата для проверки (по умолчанию сегодня)
    
    Returns:
        True, если контракт активен для работы
    """
    if check_date is None:
        check_date = date.today()
    
    if contract.status != 'active' or not contract.is_active:
        return False
    
    # Если termination_date не указан - контракт активен
    if contract.termination_date is None:
        return True
    
    # Если termination_date указан - контракт активен только до этой даты
    return contract.termination_date > check_date


def is_contract_terminated_for_payroll(contract: Contract) -> bool:
    """
    Проверяет, считается ли контракт уволенным для расчётного листа.
    
    Контракт считается уволенным, если:
    - status == 'terminated' ИЛИ
    - (status == 'active' И termination_date IS NOT NULL)
    
    Args:
        contract: Объект Contract
    
    Returns:
        True, если контракт считается уволенным
    """
    if contract.status == 'terminated':
        return True
    
    if contract.status == 'active' and contract.termination_date is not None:
        return True
    
    return False


def build_active_contract_filter(check_date: Optional[date] = None):
    """
    Создаёт SQLAlchemy фильтр для активных контрактов (для работы).
    
    Args:
        check_date: Дата для проверки (по умолчанию сегодня)
    
    Returns:
        SQLAlchemy условие для фильтрации
    """
    if check_date is None:
        check_date = date.today()
    
    return and_(
        Contract.status == 'active',
        Contract.is_active == True,
        or_(
            Contract.termination_date.is_(None),
            Contract.termination_date > check_date
        )
    )

