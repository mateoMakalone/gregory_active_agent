#!/usr/bin/env python3
"""
Скрипт для запуска безопасного API сервера
"""

import sys
import asyncio
import uvicorn
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.api.secure_server import secure_server
from src.core.logger import setup_logging
from src.core.config import config
from loguru import logger


async def main():
    """Основная функция запуска API сервера"""
    try:
        # Настраиваем логирование
        setup_logging()
        
        logger.info("🚀 Запуск безопасного API сервера...")
        
        # Получаем конфигурацию
        host = config.get('api.host', '0.0.0.0')
        port = config.get('api.port', 8000)
        docs_enabled = config.get('api.docs_enabled', True)
        
        # Запускаем задачи очистки
        await secure_server.start_cleanup_tasks()
        
        # Запускаем сервер
        logger.info(f"🌐 API сервер запущен на {host}:{port}")
        logger.info(f"📚 Документация: {'http://' + host + ':' + str(port) + '/docs' if docs_enabled else 'отключена'}")
        logger.info("🔒 Включены: веб-хук аутентификация, rate limiting, backpressure, retry политики")
        
        # Запускаем uvicorn
        uvicorn.run(
            secure_server.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 API сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска API сервера: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
