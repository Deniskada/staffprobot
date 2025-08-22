"""Тесты для сервиса экспорта."""

import pytest
import io
from apps.analytics.export_service import ExportService


class TestExportService:
    """Тесты для ExportService."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.export_service = ExportService()
        
        # Тестовые данные отчета по объекту
        self.object_report_data = {
            "object": {
                "name": "Тестовый объект",
                "address": "Тестовый адрес",
                "working_hours": "09:00 - 18:00",
                "hourly_rate": 500.0
            },
            "period": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "days": 31
            },
            "summary": {
                "total_shifts": 10,
                "completed_shifts": 9,
                "active_shifts": 1,
                "total_hours": 80.0,
                "total_payment": 40000.0,
                "avg_shift_duration": 8.0,
                "avg_daily_hours": 2.58
            },
            "employees": [
                {
                    "name": "Иван Иванов",
                    "shifts": 5,
                    "hours": 40.0,
                    "payment": 20000.0
                }
            ],
            "daily_breakdown": [
                {
                    "date": "2024-01-01",
                    "shifts": 1,
                    "hours": 8.0,
                    "payment": 4000.0
                }
            ]
        }
        
        # Тестовые данные персонального отчета
        self.personal_report_data = {
            "user": {
                "name": "Иван Иванов",
                "username": "ivanov",
                "telegram_id": 123456789
            },
            "period": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "days": 31
            },
            "summary": {
                "total_shifts": 15,
                "completed_shifts": 14,
                "active_shifts": 1,
                "total_hours": 120.0,
                "total_earnings": 60000.0,
                "avg_shift_duration": 8.0,
                "avg_daily_earnings": 1935.48
            },
            "objects": [
                {
                    "name": "Объект А",
                    "shifts": 8,
                    "hours": 64.0,
                    "earnings": 32000.0
                }
            ],
            "recent_shifts": [
                {
                    "id": 1,
                    "object_name": "Объект А",
                    "date": "2024-01-31",
                    "start_time": "09:00",
                    "end_time": "18:00",
                    "duration_hours": 8.0,
                    "payment": 4000.0,
                    "status": "completed"
                }
            ]
        }
    
    def test_export_object_report_to_pdf(self):
        """Тест экспорта отчета по объекту в PDF."""
        # Выполнение
        pdf_data = self.export_service.export_object_report_to_pdf(self.object_report_data)
        
        # Проверка
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0
        assert pdf_data.startswith(b'%PDF')  # PDF файл должен начинаться с %PDF
    
    def test_export_personal_report_to_pdf(self):
        """Тест экспорта персонального отчета в PDF."""
        # Выполнение
        pdf_data = self.export_service.export_personal_report_to_pdf(self.personal_report_data)
        
        # Проверка
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0
        assert pdf_data.startswith(b'%PDF')  # PDF файл должен начинаться с %PDF
    
    def test_export_object_report_to_excel(self):
        """Тест экспорта отчета по объекту в Excel."""
        # Выполнение
        excel_data = self.export_service.export_object_report_to_excel(self.object_report_data)
        
        # Проверка
        assert isinstance(excel_data, bytes)
        assert len(excel_data) > 0
        # Excel файл должен начинаться с PK (ZIP архив)
        assert excel_data.startswith(b'PK')
    
    def test_export_personal_report_to_excel(self):
        """Тест экспорта персонального отчета в Excel."""
        # Выполнение
        excel_data = self.export_service.export_personal_report_to_excel(self.personal_report_data)
        
        # Проверка
        assert isinstance(excel_data, bytes)
        assert len(excel_data) > 0
        # Excel файл должен начинаться с PK (ZIP архив)
        assert excel_data.startswith(b'PK')
    
    def test_export_object_report_to_pdf_empty_employees(self):
        """Тест экспорта отчета по объекту в PDF без сотрудников."""
        # Подготовка данных без сотрудников
        test_data = self.object_report_data.copy()
        test_data["employees"] = []
        
        # Выполнение
        pdf_data = self.export_service.export_object_report_to_pdf(test_data)
        
        # Проверка
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0
        assert pdf_data.startswith(b'%PDF')
    
    def test_export_personal_report_to_pdf_empty_objects(self):
        """Тест экспорта персонального отчета в PDF без объектов."""
        # Подготовка данных без объектов
        test_data = self.personal_report_data.copy()
        test_data["objects"] = []
        test_data["recent_shifts"] = []
        
        # Выполнение
        pdf_data = self.export_service.export_personal_report_to_pdf(test_data)
        
        # Проверка
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0
        assert pdf_data.startswith(b'%PDF')
    
    def test_export_object_report_to_excel_minimal_data(self):
        """Тест экспорта минимального отчета по объекту в Excel."""
        # Подготовка минимальных данных
        minimal_data = {
            "object": {
                "name": "Минимальный объект",
                "address": None,
                "working_hours": "09:00 - 18:00",
                "hourly_rate": 500.0
            },
            "period": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "days": 1
            },
            "summary": {
                "total_shifts": 0,
                "completed_shifts": 0,
                "active_shifts": 0,
                "total_hours": 0.0,
                "total_payment": 0.0,
                "avg_shift_duration": 0.0,
                "avg_daily_hours": 0.0
            }
        }
        
        # Выполнение
        excel_data = self.export_service.export_object_report_to_excel(minimal_data)
        
        # Проверка
        assert isinstance(excel_data, bytes)
        assert len(excel_data) > 0
        assert excel_data.startswith(b'PK')
    
    def test_export_personal_report_to_excel_minimal_data(self):
        """Тест экспорта минимального персонального отчета в Excel."""
        # Подготовка минимальных данных
        minimal_data = {
            "user": {
                "name": "Тестовый пользователь",
                "username": None,
                "telegram_id": 123456789
            },
            "period": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "days": 1
            },
            "summary": {
                "total_shifts": 0,
                "completed_shifts": 0,
                "active_shifts": 0,
                "total_hours": 0.0,
                "total_earnings": 0.0,
                "avg_shift_duration": 0.0,
                "avg_daily_earnings": 0.0
            }
        }
        
        # Выполнение
        excel_data = self.export_service.export_personal_report_to_excel(minimal_data)
        
        # Проверка
        assert isinstance(excel_data, bytes)
        assert len(excel_data) > 0
        assert excel_data.startswith(b'PK')
