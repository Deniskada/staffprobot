"""
Интеграционные тесты для полного цикла работы бота
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from apps.bot.bot import StaffProBot
from apps.bot.handlers_div.core_handlers import (
    start_command, button_callback
)
from apps.bot.handlers_div.utility_handlers import (
    _handle_help_callback as help_command, 
    _handle_status_callback as status_command
)
from core.auth.user_manager import UserManager


class TestBotIntegration:
    """Интеграционные тесты для бота."""
    
    @pytest.fixture
    def mock_update(self):
        """Мок для Update объекта."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.username = "test_user"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"
        update.effective_user.language_code = "ru"
        update.effective_chat = MagicMock()
        update.effective_chat.id = 67890
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Мок для Context объекта."""
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        return context
    
    @pytest.fixture
    def mock_callback_update(self):
        """Мок для Update с callback_query."""
        update = MagicMock()
        update.callback_query = MagicMock()
        update.callback_query.data = "open_shift"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user = MagicMock()
        update.callback_query.from_user.id = 12345
        update.callback_query.from_user.first_name = "Test"
        update.callback_query.from_user.last_name = "User"
        update.callback_query.from_user.username = "test_user"
        update.callback_query.from_user.language_code = "ru"
        update.callback_query.message = MagicMock()
        update.callback_query.message.chat_id = 67890
        return update
    
    @pytest.mark.asyncio
    async def test_full_user_lifecycle(self, clean_user_data, mock_update, mock_context):
        """Тест полного жизненного цикла пользователя."""
        user_manager = clean_user_data
        
        # 1. Регистрация нового пользователя
        user_data = user_manager.register_user(
            user_id=12345,
            first_name="Test",
            username="test_user",
            last_name="User",
            language_code="ru"
        )
        
        assert user_data["id"] == 12345
        assert user_data["first_name"] == "Test"
        assert user_data["is_active"] is True
        
        # 2. Проверяем, что пользователь зарегистрирован
        assert user_manager.is_user_registered(12345) is True
        
        # 3. Тестируем команду /start для существующего пользователя
        with patch('apps.bot.handlers.user_manager', user_manager):
            await start_command(mock_update, mock_context)
            
            # Проверяем, что сообщение отправлено
            mock_context.bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_button_callback_integration(self, clean_user_data, mock_callback_update, mock_context):
        """Тест интеграции inline-кнопок с UserManager."""
        user_manager = clean_user_data
        
        # Регистрируем пользователя
        user_manager.register_user(
            user_id=12345,
            first_name="Test",
            username="test_user",
            last_name="User",
            language_code="ru"
        )
        
        # Тестируем нажатие кнопки "Открыть смену"
        with patch('apps.bot.handlers.user_manager', user_manager):
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_status_command_integration(self, clean_user_data, mock_update, mock_context):
        """Тест интеграции команды /status с UserManager."""
        user_manager = clean_user_data
        
        # Регистрируем пользователя с данными
        user_manager.register_user(
            user_id=12345,
            first_name="Test",
            username="test_user",
            last_name="User",
            language_code="ru"
        )
        
        # Обновляем статистику пользователя
        user_manager.update_user_stats(12345, shifts=5, hours=40, earnings=1000.0)
        
        # Тестируем команду /status
        with patch('apps.bot.handlers.user_manager', user_manager):
            await status_command(mock_update, mock_context)
            
            # Проверяем, что сообщение отправлено
            mock_context.bot.send_message.assert_called_once()
            
            # Проверяем содержимое сообщения
            call_args = mock_context.bot.send_message.call_args
            assert 'Статус пользователя' in call_args[1]['text']
            assert '5' in call_args[1]['text']  # total_shifts
            assert '40' in call_args[1]['text']  # total_hours
            assert '1000.00' in call_args[1]['text']  # total_earnings
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, clean_user_data, mock_update, mock_context):
        """Тест обработки ошибок в интеграции."""
        user_manager = clean_user_data
        
        # Тестируем команду /status для незарегистрированного пользователя
        with patch('apps.bot.handlers.user_manager', user_manager):
            await status_command(mock_update, mock_context)
            
            # Проверяем, что сообщение отправлено
            mock_context.bot.send_message.assert_called_once()
            
            # Проверяем содержимое сообщения об ошибке
            call_args = mock_context.bot.send_message.call_args
            assert 'Пользователь не зарегистрирован' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_message_flow_integration(self, clean_user_data, mock_update, mock_context):
        """Тест потока обработки сообщений."""
        user_manager = clean_user_data
        
        # Регистрируем пользователя
        user_manager.register_user(
            user_id=12345,
            first_name="Test",
            username="test_user",
            last_name="User",
            language_code="ru"
        )
        
        # Симулируем обычное сообщение
        mock_update.message = MagicMock()
        mock_update.message.text = "Привет, как дела?"
        
        # Тестируем обработку сообщения
        with patch('apps.bot.handlers.user_manager', user_manager):
            await handle_message(mock_update, mock_context)
            
            # Проверяем, что сообщение отправлено
            mock_context.bot.send_message.assert_called_once()
            
            # Проверяем содержимое ответа
            call_args = mock_context.bot.send_message.call_args
            assert 'Используйте кнопки' in call_args[1]['text']
