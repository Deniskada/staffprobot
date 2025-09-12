"""Unit тесты для системы договоров."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date
from decimal import Decimal

from apps.web.services.contract_service import ContractService
from domain.entities.contract import Contract, ContractTemplate, ContractVersion
from domain.entities.user import User
from domain.entities.object import Object


class TestContractService:
    """Тесты для ContractService."""
    
    @pytest.fixture
    def mock_session(self):
        """Мок сессии БД."""
        return AsyncMock()
    
    @pytest.fixture
    def contract_service(self, mock_session):
        """Экземпляр ContractService для тестов."""
        return ContractService(mock_session)
    
    @pytest.fixture
    def sample_user(self):
        """Тестовый пользователь."""
        user = Mock(spec=User)
        user.id = 1
        user.telegram_id = 1220971779
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.role = "owner"
        return user
    
    @pytest.fixture
    def sample_employee(self):
        """Тестовый сотрудник."""
        employee = Mock(spec=User)
        employee.id = 2
        employee.telegram_id = 5577223137
        employee.username = "employee"
        employee.first_name = "Employee"
        employee.last_name = "Test"
        employee.role = "employee"
        return employee
    
    @pytest.fixture
    def sample_object(self):
        """Тестовый объект."""
        obj = Mock(spec=Object)
        obj.id = 1
        obj.name = "Test Object"
        obj.owner_id = 1
        return obj
    
    @pytest.fixture
    def sample_contract_template(self):
        """Тестовый шаблон договора."""
        template = Mock(spec=ContractTemplate)
        template.id = 1
        template.name = "Test Template"
        template.content = "Test contract content"
        template.owner_id = 1
        template.is_active = True
        return template
    
    @pytest.fixture
    def sample_contract(self):
        """Тестовый договор."""
        contract = Mock(spec=Contract)
        contract.id = 1
        contract.employee_id = 2
        contract.object_id = 1
        contract.template_id = 1
        contract.title = "Test Contract"
        contract.status = "active"
        contract.start_date = date(2025, 1, 1)
        contract.end_date = None
        contract.hourly_rate = Decimal("100.00")
        contract.created_at = datetime.now()
        return contract


class TestContractCreation:
    """Тесты для создания договоров."""
    
    @pytest.mark.asyncio
    async def test_create_contract_success(self, contract_service, mock_session, sample_user, sample_employee, sample_object, sample_contract_template):
        """Тест успешного создания договора."""
        # Подготовка данных
        contract_data = {
            "employee_id": 2,
            "object_id": 1,
            "template_id": 1,
            "title": "Test Contract",
            "hourly_rate": "100.00",
            "start_date": "2025-01-01"
        }
        
        # Мокаем запросы к БД
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_employee,  # get_user_by_telegram_id
            sample_object,    # get_object_by_id
            sample_contract_template  # get_template_by_id
        ]
        
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        # Мокаем создание договора
        with patch('apps.web.services.contract_service.Contract') as mock_contract_class:
            mock_contract = Mock(spec=Contract)
            mock_contract.id = 1
            mock_contract_class.return_value = mock_contract
            
            # Выполняем тест
            result = await contract_service.create_contract(contract_data, sample_user["telegram_id"])
            
            # Проверяем результат
            assert result is not None
            assert result.id == 1
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_contract_employee_not_found(self, contract_service, mock_session, sample_user):
        """Тест создания договора с несуществующим сотрудником."""
        contract_data = {
            "employee_id": 999,
            "object_id": 1,
            "template_id": 1,
            "title": "Test Contract"
        }
        
        # Мокаем что сотрудник не найден
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Выполняем тест и проверяем исключение
        with pytest.raises(ValueError, match="Сотрудник не найден"):
            await contract_service.create_contract(contract_data, sample_user["telegram_id"])
    
    @pytest.mark.asyncio
    async def test_create_contract_object_not_found(self, contract_service, mock_session, sample_user, sample_employee):
        """Тест создания договора с несуществующим объектом."""
        contract_data = {
            "employee_id": 2,
            "object_id": 999,
            "template_id": 1,
            "title": "Test Contract"
        }
        
        # Мокаем что сотрудник найден, но объект нет
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_employee,  # get_user_by_telegram_id
            None  # get_object_by_id
        ]
        
        # Выполняем тест и проверяем исключение
        with pytest.raises(ValueError, match="Объект не найден"):
            await contract_service.create_contract(contract_data, sample_user["telegram_id"])


class TestContractManagement:
    """Тесты для управления договорами."""
    
    @pytest.mark.asyncio
    async def test_get_contracts_by_owner(self, contract_service, mock_session, sample_user, sample_contract):
        """Тест получения договоров владельца."""
        # Мокаем запрос к БД
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_contract]
        
        # Выполняем тест
        result = await contract_service.get_contracts_by_owner(sample_user["telegram_id"])
        
        # Проверяем результат
        assert len(result) == 1
        assert result[0].id == 1
    
    @pytest.mark.asyncio
    async def test_get_contract_by_id(self, contract_service, mock_session, sample_contract):
        """Тест получения договора по ID."""
        # Мокаем запрос к БД
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_contract
        
        # Выполняем тест
        result = await contract_service.get_contract_by_id(1, 1220971779)
        
        # Проверяем результат
        assert result is not None
        assert result.id == 1
    
    @pytest.mark.asyncio
    async def test_terminate_contract(self, contract_service, mock_session, sample_contract):
        """Тест расторжения договора."""
        # Мокаем получение договора
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_contract
        
        # Выполняем тест
        result = await contract_service.terminate_contract(1, 1220971779, "Test reason")
        
        # Проверяем результат
        assert result is True
        assert sample_contract.status == "terminated"
        assert sample_contract.end_date is not None
        mock_session.commit.assert_called_once()


class TestContractTemplates:
    """Тесты для шаблонов договоров."""
    
    @pytest.mark.asyncio
    async def test_get_templates_by_owner(self, contract_service, mock_session, sample_user, sample_contract_template):
        """Тест получения шаблонов владельца."""
        # Мокаем запрос к БД
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_contract_template]
        
        # Выполняем тест
        result = await contract_service.get_templates_by_owner(sample_user["telegram_id"])
        
        # Проверяем результат
        assert len(result) == 1
        assert result[0].id == 1
    
    @pytest.mark.asyncio
    async def test_create_template(self, contract_service, mock_session, sample_user):
        """Тест создания шаблона договора."""
        template_data = {
            "name": "New Template",
            "content": "New contract content"
        }
        
        # Мокаем создание шаблона
        with patch('apps.web.services.contract_service.ContractTemplate') as mock_template_class:
            mock_template = Mock(spec=ContractTemplate)
            mock_template.id = 2
            mock_template_class.return_value = mock_template
            
            # Выполняем тест
            result = await contract_service.create_template(template_data, sample_user["telegram_id"])
            
            # Проверяем результат
            assert result is not None
            assert result.id == 2
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()


class TestContractValidation:
    """Тесты для валидации договоров."""
    
    def test_validate_contract_data_success(self, contract_service):
        """Тест успешной валидации данных договора."""
        contract_data = {
            "employee_id": 2,
            "object_id": 1,
            "template_id": 1,
            "title": "Test Contract",
            "hourly_rate": "100.00",
            "start_date": "2025-01-01"
        }
        
        # Выполняем тест
        result = contract_service._validate_contract_data(contract_data)
        
        # Проверяем результат
        assert result is True
    
    def test_validate_contract_data_missing_fields(self, contract_service):
        """Тест валидации с отсутствующими полями."""
        contract_data = {
            "employee_id": 2,
            # Отсутствуют обязательные поля
        }
        
        # Выполняем тест и проверяем исключение
        with pytest.raises(ValueError, match="Не все обязательные поля заполнены"):
            contract_service._validate_contract_data(contract_data)
    
    def test_validate_contract_data_invalid_hourly_rate(self, contract_service):
        """Тест валидации с неверной ставкой."""
        contract_data = {
            "employee_id": 2,
            "object_id": 1,
            "template_id": 1,
            "title": "Test Contract",
            "hourly_rate": "invalid_rate",
            "start_date": "2025-01-01"
        }
        
        # Выполняем тест и проверяем исключение
        with pytest.raises(ValueError, match="Неверный формат ставки"):
            contract_service._validate_contract_data(contract_data)
