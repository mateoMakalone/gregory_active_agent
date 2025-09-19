#!/usr/bin/env python3
"""
Скрипт для запуска API v2 сервера
"""

import sys
import asyncio
import uvicorn
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.api.v2.server import api_server_v2
from src.core.logger import setup_logging
from src.core.config import config
from src.database.connection import db_manager
from loguru import logger


async def main():
    """Основная функция запуска API v2 сервера"""
    try:
        # Настраиваем логирование
        setup_logging()
        
        logger.info("🚀 Запуск API v2 сервера...")
        
        # Подключаемся к базе данных
        if not await db_manager.connect():
            raise ConnectionError("Не удалось подключиться к базе данных")
        
        logger.info("✅ Подключение к базе данных установлено")
        
        # Получаем конфигурацию
        host = config.get('api.host', '0.0.0.0')
        port = config.get('api.port', 8000)
        docs_enabled = config.get('api.docs_enabled', True)
        
        # Запускаем сервер
        logger.info(f"🌐 API v2 сервер запущен на {host}:{port}")
        logger.info(f"📚 Документация: {'http://' + host + ':' + str(port) + '/docs' if docs_enabled else 'отключена'}")
        logger.info("🔒 Включены: веб-хук аутентификация, rate limiting, retry политики")
        logger.info("📊 Endpoints: /runs, /status, /signals, /orders, /positions, /webhooks/execution")
        
        # Запускаем uvicorn
        uvicorn.run(
            api_server_v2.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 API v2 сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска API v2 сервера: {e}")
        sys.exit(1)
    finally:
        await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
