"""
Скрипт для запуска Telegram-бота
"""

import sys
import os
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent))

from telegram_bot.bot import telegram_bot
from src.core.config import config
from src.core.logger import setup_logging
from loguru import logger

def main():
    """Запуск Telegram-бота"""
    # Настраиваем логирование
    setup_logging()
    
    # Тестируем подключение
    if telegram_bot.test_connection():
        logger.info("Telegram-бот успешно подключен")
        
        # Отправляем тестовое сообщение
        telegram_bot.send_alert(
            "🤖 Система запущена",
            "Торговый AI-агент готов к работе!",
            "INFO"
        )
        
        logger.info("Telegram-бот готов к работе")
        
        # Простой цикл для поддержания работы
        try:
            while True:
                import time
                time.sleep(60)  # Проверяем каждую минуту
        except KeyboardInterrupt:
            logger.info("Telegram-бот остановлен")
    else:
        logger.error("Не удалось подключиться к Telegram API")
        sys.exit(1)

if __name__ == "__main__":
    main()

