#!/usr/bin/env python3
"""
Чистый скрипт запуска API v2 сервера без asyncio.run()
"""

import sys
import uvicorn
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.api.v2.clean_server import app
from src.core.config import config
from src.core.logger import setup_logging
from loguru import logger


def main():
    """Основная функция запуска API v2 сервера"""
    try:
        # Настраиваем логирование
        setup_logging()
        
        logger.info("🚀 Запуск чистого API v2 сервера...")
        
        # Получаем конфигурацию
        host = config.get('api.host', '0.0.0.0')
        port = config.get('api.port', 8000)
        docs_enabled = config.get('api.docs_enabled', True)
        
        # Запускаем сервер
        logger.info(f"🌐 API v2 сервер запущен на {host}:{port}")
        logger.info(f"📚 Документация: {'http://' + host + ':' + str(port) + '/docs' if docs_enabled else 'отключена'}")
        logger.info("🔒 Включены: веб-хук аутентификация, rate limiting, retry политики")
        logger.info("📊 Endpoints: /runs, /status, /signals, /orders, /positions, /webhooks/execution")
        
        # Запускаем uvicorn напрямую - никаких asyncio.run()!
        uvicorn.run(
            app,
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


if __name__ == "__main__":
    main()
