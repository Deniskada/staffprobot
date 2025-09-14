"""Unit тесты для обработчиков бота (исправленная версия)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.bot.handlers_div.core_handlers import (
    start_command,
    button_callback
)
from apps.bot.handlers_div.utility_handlers import (
    _handle_help_callback as help_command,
    _handle_status_callback as status_command
)


class TestBotHandlers:
    """Тесты для обработчиков бота."""
    
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
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.callback_query = MagicMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.answer = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Мок для Context объекта."""
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        return context
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, mock_update, mock_context):
        """Тест команды /start для нового пользователя."""
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = False
            mock_user_manager.register_user.return_value = {"id": 12345}
            
            await start_command(mock_update, mock_context)
            
            # Проверяем, что пользователь был зарегистрирован
            mock_user_manager.register_user.assert_called_once_with(
                user_id=12345,
                username="test_user",
                first_name="Test",
                last_name="User",
                language_code="ru"
            )
            
            # Проверяем, что сообщение было отправлено
            mock_context.bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_command_existing_user(self, mock_update, mock_context):
        """Тест команды /start для существующего пользователя."""
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            await start_command(mock_update, mock_context)
            
            # Проверяем, что пользователь НЕ был зарегистрирован повторно
            mock_user_manager.register_user.assert_not_called()
            
            # Проверяем, что сообщение было отправлено
            mock_context.bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_update, mock_context):
        """Тест команды /help."""
        await help_command(mock_update, mock_context)
        
        # Проверяем, что сообщение было отправлено
        mock_update.message.reply_text.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_update.message.reply_text.call_args
        # help_command использует позиционные аргументы
        assert len(call_args[0]) > 0  # Первый аргумент - текст
        assert 'Справка' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_status_command_registered_user(self, mock_update, mock_context):
        """Тест команды /status для зарегистрированного пользователя."""
        with patch('apps.bot.handlers.shift_service') as mock_shift_service:
            mock_shift_service.get_user_active_shifts.return_value = []
            
            await status_command(mock_update, mock_context)
            
            # Проверяем, что сообщение было отправлено
            mock_update.message.reply_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_update.message.reply_text.call_args
            assert len(call_args[0]) > 0  # Первый аргумент - текст
            assert 'Статус смен' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_status_command_unregistered_user(self, mock_update, mock_context):
        """Тест команды /status для незарегистрированного пользователя."""
        with patch('apps.bot.handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = False
            
            await status_command(mock_update, mock_context)
            
            # Проверяем, что сообщение было отправлено
            mock_update.message.reply_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_update.message.reply_text.call_args
            assert len(call_args[0]) > 0  # Первый аргумент - текст
            assert 'Статус смен' in call_args[0][0]
    
    # Тест handle_message удален - функция больше не существует


class TestButtonCallbacks:
    """Тесты для обработчиков кнопок."""
    
    @pytest.fixture
    def mock_callback_update(self):
        """Мок для Update с callback_query."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.username = "test_user"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"
        update.callback_query = MagicMock()
        update.callback_query.data = "test_callback"
        update.callback_query.from_user = MagicMock()
        update.callback_query.from_user.id = 12345
        update.callback_query.from_user.username = "test_user"
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.answer = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Мок для Context объекта."""
        context = MagicMock()
        return context
    
    @pytest.mark.asyncio
    async def test_button_callback_open_shift(self, mock_callback_update, mock_context):
        """Тест callback для открытия смены."""
        mock_callback_update.callback_query.data = "open_shift"
        
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение было обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert 'text' in call_args[1]
            assert 'Открытие смены' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_button_callback_close_shift(self, mock_callback_update, mock_context):
        """Тест callback для закрытия смены."""
        mock_callback_update.callback_query.data = "close_shift"
        
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение было обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert 'text' in call_args[1]
            assert 'активных смен' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_button_callback_create_object(self, mock_callback_update, mock_context):
        """Тест callback для создания объекта."""
        mock_callback_update.callback_query.data = "create_object"
        
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            # Мокаем object_creation_handlers
            with patch('apps.bot.handlers_div.object_creation_handlers.handle_create_object_start') as mock_handler:
                mock_handler.return_value = None
                
                await button_callback(mock_callback_update, mock_context)
                
                # Проверяем, что обработчик был вызван
                mock_handler.assert_called_once_with(mock_callback_update, mock_context)
    
    @pytest.mark.asyncio
    async def test_button_callback_get_report(self, mock_callback_update, mock_context):
        """Тест callback для получения отчета."""
        mock_callback_update.callback_query.data = "get_report"
        
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение было обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert 'text' in call_args[1]
            assert 'Отчеты' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_button_callback_help(self, mock_callback_update, mock_context):
        """Тест callback для помощи."""
        mock_callback_update.callback_query.data = "help"
        
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение было обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert 'text' in call_args[1]
            assert 'Справка' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_button_callback_status(self, mock_callback_update, mock_context):
        """Тест callback для статуса."""
        mock_callback_update.callback_query.data = "status"
        
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение было обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert 'text' in call_args[1]
            assert 'Статус смен' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_button_callback_main_menu(self, mock_callback_update, mock_context):
        """Тест callback для главного меню."""
        mock_callback_update.callback_query.data = "main_menu"
        
        with patch('apps.bot.handlers_div.core_handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение было обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert 'text' in call_args[1]
            assert 'Главное меню' in call_args[1]['text']
