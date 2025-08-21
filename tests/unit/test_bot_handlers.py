"""Unit тесты для обработчиков бота."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.bot.handlers import (
    start_command,
    help_command,
    status_command,
    handle_message,
    button_callback
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
        with patch('apps.bot.handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = False
            mock_user_manager.register_user.return_value = {"id": 12345}
            
            await start_command(mock_update, mock_context)
            
            # Проверяем, что пользователь был зарегистрирован
            mock_user_manager.register_user.assert_called_once()
            
            # Проверяем, что сообщение было отправлено
            mock_context.bot.send_message.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_context.bot.send_message.call_args
            assert call_args[1]['chat_id'] == 67890
            assert 'Добро пожаловать в StaffProBot!' in call_args[1]['text']
            assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_start_command_existing_user(self, mock_update, mock_context):
        """Тест команды /start для существующего пользователя."""
        with patch('apps.bot.handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            mock_user_manager.update_user_activity.return_value = None
            
            await start_command(mock_update, mock_context)
            
            # Проверяем, что активность была обновлена
            mock_user_manager.update_user_activity.assert_called_once_with(12345)
            
            # Проверяем, что сообщение было отправлено
            mock_context.bot.send_message.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_context.bot.send_message.call_args
            assert call_args[1]['chat_id'] == 67890
            assert 'С возвращением в StaffProBot!' in call_args[1]['text']
            assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_update, mock_context):
        """Тест команды /help."""
        await help_command(mock_update, mock_context)
        
        # Проверяем, что сообщение было отправлено
        mock_context.bot.send_message.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_context.bot.send_message.call_args
        assert call_args[1]['chat_id'] == 67890
        assert 'Справка по командам' in call_args[1]['text']
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_status_command_registered_user(self, mock_update, mock_context):
        """Тест команды /status для зарегистрированного пользователя."""
        with patch('apps.bot.handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = True
            mock_user_manager.get_user_stats.return_value = {
                "total_shifts": 5,
                "total_hours": 40,
                "total_earnings": 1000.0,
                "registered_at": "2024-01-01T12:00:00",
                "last_activity": "2024-01-01T12:00:00"
            }
            
            await status_command(mock_update, mock_context)
            
            # Проверяем, что сообщение было отправлено
            mock_context.bot.send_message.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_context.bot.send_message.call_args
            assert call_args[1]['chat_id'] == 67890
            assert 'Статус пользователя' in call_args[1]['text']
            assert '5' in call_args[1]['text']  # total_shifts
            assert '40' in call_args[1]['text']  # total_hours
    
    @pytest.mark.asyncio
    async def test_status_command_unregistered_user(self, mock_update, mock_context):
        """Тест команды /status для незарегистрированного пользователя."""
        with patch('apps.bot.handlers.user_manager') as mock_user_manager:
            mock_user_manager.is_user_registered.return_value = False
            mock_user_manager.update_user_activity.return_value = None
            mock_user_manager.get_user_stats.return_value = None
            
            await status_command(mock_update, mock_context)
            
            # Проверяем, что сообщение было отправлено
            mock_context.bot.send_message.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_context.bot.send_message.call_args
            assert call_args[1]['chat_id'] == 67890
            assert 'Пользователь не зарегистрирован' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_handle_message(self, mock_update, mock_context):
        """Тест обработки обычных сообщений."""
        mock_update.message = MagicMock()
        mock_update.message.text = "Привет, как дела?"
        
        await handle_message(mock_update, mock_context)
        
        # Проверяем, что сообщение было отправлено
        mock_context.bot.send_message.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_context.bot.send_message.call_args
        assert call_args[1]['chat_id'] == 67890
        assert 'Используйте кнопки' in call_args[1]['text']
        assert 'parse_mode' in call_args[1]  # Проверяем HTML форматирование


class TestButtonCallbacks:
    """Тесты для обработки нажатий кнопок."""
    
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
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.first_name = "Test"
        update.effective_chat = MagicMock()
        update.effective_chat.id = 67890
        
        # Мокаем callback_query
        update.callback_query = MagicMock()
        update.callback_query.data = "open_shift"
        update.callback_query.answer = AsyncMock()  # Делаем асинхронным
        update.callback_query.edit_message_text = AsyncMock()
        
        # Мокаем query.from_user (используется в button_callback)
        update.callback_query.from_user = MagicMock()
        update.callback_query.from_user.id = 12345
        update.callback_query.from_user.first_name = "Test"
        update.callback_query.from_user.last_name = "User"
        update.callback_query.from_user.username = "test_user"
        update.callback_query.from_user.language_code = "ru"
        
        # Мокаем query.message.chat_id (используется в button_callback)
        update.callback_query.message = MagicMock()
        update.callback_query.message.chat_id = 67890
        
        return update
    
    @pytest.mark.asyncio
    async def test_button_callback_open_shift(self, mock_callback_update, mock_context):
        """Тест нажатия кнопки 'Открыть смену'."""
        mock_callback_update.callback_query.data = "open_shift"
        
        await button_callback(mock_callback_update, mock_context)
        
        # Проверяем, что сообщение было обновлено
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert 'Открытие смены' in call_args[1]['text']
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_button_callback_close_shift(self, mock_callback_update, mock_context):
        """Тест нажатия кнопки 'Закрыть смену'."""
        mock_callback_update.callback_query.data = "close_shift"
        
        await button_callback(mock_callback_update, mock_context)
        
        # Проверяем, что сообщение было обновлено
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert 'Закрытие смены' in call_args[1]['text']
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_button_callback_create_object(self, mock_callback_update, mock_context):
        """Тест нажатия кнопки 'Создать объект'."""
        mock_callback_update.callback_query.data = "create_object"
        
        await button_callback(mock_callback_update, mock_context)
        
        # Проверяем, что сообщение было обновлено
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert 'Создание объекта' in call_args[1]['text']
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_button_callback_get_report(self, mock_callback_update, mock_context):
        """Тест нажатия кнопки 'Отчет'."""
        mock_callback_update.callback_query.data = "get_report"
        
        await button_callback(mock_callback_update, mock_context)
        
        # Проверяем, что сообщение было обновлено
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert 'Отчеты (демо)' in call_args[1]['text']
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_button_callback_help(self, mock_callback_update, mock_context):
        """Тест нажатия кнопки 'Помощь'."""
        mock_callback_update.callback_query.data = "help"
        
        await button_callback(mock_callback_update, mock_context)
        
        # Проверяем, что сообщение было обновлено
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert 'Помощь' in call_args[1]['text']
        assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_button_callback_status(self, mock_callback_update, mock_context):
        """Тест нажатия кнопки 'Статус'."""
        mock_callback_update.callback_query.data = "status"
        
        with patch('apps.bot.handlers.user_manager') as mock_user_manager:
            mock_user_manager.update_user_activity.return_value = None
            mock_user_manager.get_user_stats.return_value = {
                "total_shifts": 5,
                "total_hours": 40,
                "total_earnings": 1000.0,
                "registered_at": "2024-01-01T12:00:00",
                "last_activity": "2024-01-01T12:00:00"
            }
            
            await button_callback(mock_callback_update, mock_context)
            
            # Проверяем, что сообщение было обновлено
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            
            # Проверяем параметры вызова
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert 'Статус пользователя' in call_args[1]['text']
            assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_button_callback_main_menu(self, mock_callback_update, mock_context):
        """Тест нажатия кнопки 'Главное меню'."""
        mock_callback_update.callback_query.data = "main_menu"
        
        await button_callback(mock_callback_update, mock_context)
        
        # Проверяем, что сообщение было обновлено
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert 'Главное меню' in call_args[1]['text']
        assert 'reply_markup' in call_args[1]






