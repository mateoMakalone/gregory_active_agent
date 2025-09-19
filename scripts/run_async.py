"""
Скрипт для запуска асинхронной версии торгового AI-агента
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent))

from src.main import main
from src.core.logger import setup_logging
from loguru import logger

async def run_async_agent():
    """Запуск асинхронного агента"""
    # Настраиваем логирование
    setup_logging()
    
    logger.info("🚀 Запуск асинхронного торгового AI-агента")
    logger.info("=" * 50)
    
    try:
        # Запускаем асинхронный агент
        await main()
        
    except KeyboardInterrupt:
        logger.info("📡 Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска асинхронного агента: {e}")
        raise
    finally:
        logger.info("✅ Асинхронный агент остановлен")

def main_sync():
    """Синхронная обертка для запуска асинхронного кода"""
    try:
        asyncio.run(run_async_agent())
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_sync()
