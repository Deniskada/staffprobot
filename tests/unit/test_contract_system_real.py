"""Простые unit-тесты для реальных методов системы договоров."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date
from decimal import Decimal

from apps.web.services.contract_service import ContractService


class TestContractServiceReal:
    """Простые тесты для реальных методов ContractService."""
    
    def test_contract_service_init(self):
        """Тест инициализации ContractService."""
        service = ContractService()
        assert service is not None
        assert hasattr(service, 'create_contract')
        assert hasattr(service, 'get_contract_templates')
        assert hasattr(service, 'get_owner_contracts')
    
    @pytest.mark.asyncio
    async def test_create_contract_template_success(self):
        """Тест успешного создания шаблона договора."""
        template_data = {
            "name": "Test Template",
            "content": "Test contract content",
            "created_by": 1220971779
        }
        
        # Мокаем get_async_session
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем запросы к БД
            mock_session_instance.execute.return_value.scalar_one_or_none.return_value = Mock(id=1)
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []
            
            service = ContractService()
            result = await service.create_contract_template(template_data)
            
            # Проверяем что метод был вызван
            assert mock_session_instance.add.called
            assert mock_session_instance.commit.called
    
    @pytest.mark.asyncio
    async def test_get_contract_templates(self):
        """Тест получения списка шаблонов договоров."""
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем пустой результат
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []
            
            service = ContractService()
            result = await service.get_contract_templates()
            
            # Проверяем что возвращается список
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_owner_contracts(self):
        """Тест получения договоров владельца."""
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем пустой результат
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []
            
            service = ContractService()
            result = await service.get_owner_contracts(1)
            
            # Проверяем что возвращается список
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_contract_employees_by_telegram_id(self):
        """Тест получения сотрудников по telegram_id владельца."""
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем пустой результат
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []
            
            service = ContractService()
            result = await service.get_contract_employees_by_telegram_id(1220971779)
            
            # Проверяем что возвращается список
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_owner_objects(self):
        """Тест получения объектов владельца."""
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем пустой результат
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []
            
            service = ContractService()
            result = await service.get_owner_objects(1220971779)
            
            # Проверяем что возвращается список
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_available_employees(self):
        """Тест получения доступных сотрудников."""
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем пустой результат
            mock_session_instance.execute.return_value.scalars.return_value.all.return_value = []
            
            service = ContractService()
            result = await service.get_available_employees(1)
            
            # Проверяем что возвращается список
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_contract_by_id(self):
        """Тест получения договора по ID."""
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем что договор не найден
            mock_session_instance.execute.return_value.scalar_one_or_none.return_value = None
            
            service = ContractService()
            result = await service.get_contract_by_id(1, 1)
            
            # Проверяем что возвращается None
            assert result is None
    
    @pytest.mark.asyncio
    async def test_terminate_contract(self):
        """Тест расторжения договора."""
        with patch('apps.web.services.contract_service.get_async_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Мокаем что договор не найден
            mock_session_instance.execute.return_value.scalar_one_or_none.return_value = None
            
            service = ContractService()
            result = await service.terminate_contract(1, 1, "Test reason")
            
            # Проверяем что возвращается False
            assert result is False


class TestContractServiceValidation:
    """Тесты для валидации данных в ContractService."""
    
    def test_extract_fields_schema_from_content(self):
        """Тест извлечения схемы полей из контента."""
        service = ContractService()
        
        # Тест с простым контентом
        content = "Договор между {employee_name} и {company_name}"
        result = service._extract_fields_schema_from_content(content)
        
        # Проверяем что возвращается список
        assert isinstance(result, list)
        
        # Проверяем что найдены поля
        field_names = [field['name'] for field in result]
        assert 'employee_name' in field_names
        assert 'company_name' in field_names
    
    def test_extract_fields_schema_empty_content(self):
        """Тест извлечения схемы полей из пустого контента."""
        service = ContractService()
        
        content = "Простой текст без полей"
        result = service._extract_fields_schema_from_content(content)
        
        # Проверяем что возвращается пустой список
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_extract_fields_schema_complex_content(self):
        """Тест извлечения схемы полей из сложного контента."""
        service = ContractService()
        
        content = """
        Договор № {contract_number}
        Дата: {contract_date}
        Сотрудник: {employee_name} {employee_surname}
        Компания: {company_name}
        Адрес: {company_address}
        """
        
        result = service._extract_fields_schema_from_content(content)
        
        # Проверяем что возвращается список
        assert isinstance(result, list)
        
        # Проверяем что найдены все поля
        field_names = [field['name'] for field in result]
        expected_fields = [
            'contract_number', 'contract_date', 'employee_name', 
            'employee_surname', 'company_name', 'company_address'
        ]
        
        for field in expected_fields:
            assert field in field_names
