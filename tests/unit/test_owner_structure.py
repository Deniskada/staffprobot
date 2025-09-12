"""Простые тесты для структуры owner.py после миграции."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from apps.web.routes.owner import router


class TestOwnerStructure:
    """Тесты для структуры owner.py после миграции."""
    
    def test_router_exists(self):
        """Тест что роутер owner существует."""
        assert router is not None
        assert hasattr(router, 'routes')
        assert len(router.routes) > 0
    
    def test_router_has_owner_routes(self):
        """Тест что роутер содержит роуты владельца."""
        route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
        
        # Проверяем основные роуты владельца
        expected_routes = [
            "/",
            "/dashboard", 
            "/objects",
            "/calendar",
            "/employees",
            "/shifts",
            "/reports",
            "/profile"
        ]
        
        for expected_route in expected_routes:
            assert expected_route in route_paths, f"Route {expected_route} not found in {route_paths}"
    
    def test_router_has_api_routes(self):
        """Тест что роутер содержит API роуты."""
        route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
        
        # Проверяем API роуты
        api_routes = [
            "/calendar/api/objects",
            "/calendar/api/timeslots-status"
        ]
        
        for api_route in api_routes:
            assert api_route in route_paths, f"API route {api_route} not found in {route_paths}"
    
    def test_router_has_timeslot_routes(self):
        """Тест что роутер содержит роуты тайм-слотов."""
        route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
        
        # Проверяем роуты тайм-слотов (реальные пути из owner.py)
        timeslot_routes = [
            "/timeslots/object/{object_id}",
            "/timeslots/object/{object_id}/create"
        ]
        
        for timeslot_route in timeslot_routes:
            assert timeslot_route in route_paths, f"Timeslot route {timeslot_route} not found in {route_paths}"
    
    def test_router_has_contract_routes(self):
        """Тест что роутер содержит роуты договоров."""
        route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
        
        # Проверяем роуты договоров (реальные пути из owner.py)
        contract_routes = [
            "/employees/contract/{contract_id}",
            "/employees/create"
        ]
        
        for contract_route in contract_routes:
            assert contract_route in route_paths, f"Contract route {contract_route} not found in {route_paths}"


class TestOwnerImports:
    """Тесты для импортов в owner.py."""
    
    def test_owner_imports_work(self):
        """Тест что все импорты в owner.py работают."""
        try:
            from apps.web.routes.owner import router
            assert router is not None
        except ImportError as e:
            pytest.fail(f"Failed to import owner router: {e}")
    
    def test_owner_has_required_functions(self):
        """Тест что owner.py содержит необходимые функции."""
        from apps.web.routes import owner
        
        # Проверяем основные функции (реальные имена из owner.py)
        required_functions = [
            'owner_dashboard',
            'owner_objects', 
            'owner_calendar',
            'owner_employees_list',  # Реальное имя функции
            'owner_shifts_list',     # Реальное имя функции
            'owner_reports',
            'owner_profile'
        ]
        
        for func_name in required_functions:
            assert hasattr(owner, func_name), f"Function {func_name} not found in owner module"
    
    def test_owner_has_api_functions(self):
        """Тест что owner.py содержит API функции."""
        from apps.web.routes import owner
        
        # Проверяем API функции
        api_functions = [
            'owner_calendar_api_objects',
            'owner_calendar_api_timeslots_status'
        ]
        
        for func_name in api_functions:
            assert hasattr(owner, func_name), f"API function {func_name} not found in owner module"


class TestOwnerServices:
    """Тесты для сервисов, используемых в owner.py."""
    
    def test_contract_service_import(self):
        """Тест импорта ContractService."""
        try:
            from apps.web.services.contract_service import ContractService
            assert ContractService is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ContractService: {e}")
    
    def test_object_service_import(self):
        """Тест импорта ObjectService."""
        try:
            from apps.web.services.object_service import ObjectService
            assert ObjectService is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ObjectService: {e}")
    
    def test_timeslot_service_import(self):
        """Тест импорта TimeSlotService из правильного места."""
        try:
            from apps.bot.services.time_slot_service import TimeSlotService
            assert TimeSlotService is not None
        except ImportError as e:
            pytest.fail(f"Failed to import TimeSlotService: {e}")
    
    def test_shift_service_import(self):
        """Тест импорта ShiftService."""
        try:
            from apps.web.services.shift_service import ShiftService
            assert ShiftService is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ShiftService: {e}")


class TestOwnerTemplates:
    """Тесты для шаблонов owner."""
    
    def test_owner_templates_exist(self):
        """Тест что шаблоны owner существуют."""
        import os
        
        template_dir = "apps/web/templates/owner"
        assert os.path.exists(template_dir), f"Owner templates directory not found: {template_dir}"
        
        # Проверяем основные шаблоны (реальные пути)
        required_templates = [
            "base_owner.html",
            "dashboard.html",
            "objects/list.html",
            "calendar/index.html",     # Реальный путь
            "employees/list.html",
            "shifts/list.html",
            "reports/index.html",      # Реальный путь
            "profile/index.html"       # Реальный путь
        ]
        
        for template in required_templates:
            template_path = os.path.join(template_dir, template)
            assert os.path.exists(template_path), f"Template not found: {template_path}"
