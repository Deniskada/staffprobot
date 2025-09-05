"""Утилиты для обработчиков бота."""

from telegram import KeyboardButton, ReplyKeyboardMarkup


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру для запроса геопозиции."""
    keyboard = [
        [KeyboardButton("📍 Отправить геопозицию", request_location=True)],
        [KeyboardButton("❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
