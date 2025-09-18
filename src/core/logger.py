"""
Настройка системы логирования
"""

import sys
from pathlib import Path
from loguru import logger
from .config import config


def setup_logging():
    """Настройка системы логирования"""
    
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Получаем конфигурацию логирования
    log_config = config.logging_config
    
    # Настройка формата
    log_format = log_config.get('format', 
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}")
    
    # Настройка уровня логирования
    log_level = log_config.get('level', 'INFO')
    
    # Консольный вывод
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # Файловый вывод
    log_file = log_config.get('file', 'logs/trading_agent.log')
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    max_size = log_config.get('max_size', '10 MB')
    retention = log_config.get('retention', '30 days')
    
    logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation=max_size,
        retention=retention,
        compression="zip"
    )
    
    logger.info("Система логирования настроена")


# Инициализация логирования при импорте модуля
setup_logging()

