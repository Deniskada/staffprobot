"""Тесты для сервиса аналитики."""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch
from apps.analytics.analytics_service import AnalyticsService


class TestAnalyticsService:
    """Тесты для AnalyticsService."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.analytics_service = AnalyticsService()
    
    @patch('apps.analytics.analytics_service.get_sync_session')
    def test_get_dashboard_metrics_no_user(self, mock_session):
        """Тест получения метрик дашборда для несуществующего пользователя."""
        # Настройка мока
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Выполнение
        result = self.analytics_service.get_dashboard_metrics(99999)
        
        # Проверка
        assert "error" in result
        assert "Пользователь не найден" in result["error"]
    
    @patch('apps.analytics.analytics_service.get_sync_session')
    def test_get_dashboard_metrics_no_objects(self, mock_session):
        """Тест получения метрик дашборда для пользователя без объектов."""
        # Настройка мока
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Мокаем пользователя
        mock_user = Mock()
        mock_user.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Мокаем пустой список объектов
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Выполнение
        result = self.analytics_service.get_dashboard_metrics(123456)
        
        # Проверка
        assert result["objects_count"] == 0
        assert result["active_shifts"] == 0
        assert result["today_stats"]["shifts"] == 0
        assert result["week_stats"]["shifts"] == 0
        assert result["month_stats"]["shifts"] == 0
    
    @patch('apps.analytics.analytics_service.get_sync_session')
    def test_get_object_report_no_access(self, mock_session):
        """Тест получения отчета по объекту без прав доступа."""
        # Настройка мока
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Выполнение
        result = self.analytics_service.get_object_report(
            object_id=1,
            start_date=date.today(),
            end_date=date.today(),
            owner_id=123456
        )
        
        # Проверка
        assert "error" in result
        assert "не найден или нет прав доступа" in result["error"]
    
    @patch('apps.analytics.analytics_service.get_sync_session')
    def test_get_personal_report_no_user(self, mock_session):
        """Тест получения персонального отчета для несуществующего пользователя."""
        # Настройка мока
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Выполнение
        result = self.analytics_service.get_personal_report(
            user_id=99999,
            start_date=date.today(),
            end_date=date.today()
        )
        
        # Проверка
        assert "error" in result
        assert "Пользователь не найден" in result["error"]
    
    def test_calculate_daily_stats(self):
        """Тест расчета ежедневной статистики."""
        # Подготовка данных
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 3)
        
        # Мокаем смены
        mock_shifts = []
        
        # Выполнение
        result = self.analytics_service._calculate_daily_stats(mock_shifts, start_date, end_date)
        
        # Проверка
        assert len(result) == 3  # 3 дня
        assert all(day["shifts"] == 0 for day in result)
        assert all(day["hours"] == 0 for day in result)
        assert all(day["payment"] == 0 for day in result)
    
    def test_calculate_employee_stats_empty(self):
        """Тест расчета статистики сотрудников с пустым списком."""
        # Подготовка
        mock_db = Mock()
        
        # Выполнение
        result = self.analytics_service._calculate_employee_stats([], mock_db)
        
        # Проверка
        assert result == []
    
    def test_calculate_object_stats_for_user_empty(self):
        """Тест расчета статистики объектов для пользователя с пустым списком."""
        # Подготовка
        mock_db = Mock()
        
        # Выполнение
        result = self.analytics_service._calculate_object_stats_for_user([], mock_db)
        
        # Проверка
        assert result == []
    
    @patch('apps.analytics.analytics_service.get_sync_session')
    def test_get_period_stats_empty(self, mock_session):
        """Тест получения статистики за период с пустыми данными."""
        # Настройка мока
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Выполнение
        result = self.analytics_service._get_period_stats(
            mock_db, [1, 2, 3], date.today(), date.today()
        )
        
        # Проверка
        assert result["shifts"] == 0
        assert result["hours"] == 0
        assert result["earnings"] == 0
    
    @patch('apps.analytics.analytics_service.get_sync_session')
    def test_get_top_objects_empty(self, mock_session):
        """Тест получения топ объектов с пустыми данными."""
        # Настройка мока
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        # Выполнение
        result = self.analytics_service._get_top_objects(
            mock_db, [1, 2, 3], date.today(), date.today()
        )
        
        # Проверка
        assert result == []
