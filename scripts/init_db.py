#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""

import sys
import asyncio
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import db_manager
from src.core.logger import setup_logging
from loguru import logger


async def init_database():
    """Инициализация базы данных"""
    try:
        # Настраиваем логирование
        setup_logging()
        
        logger.info("🚀 Инициализация базы данных...")
        
        # Подключаемся к БД
        if await db_manager.connect():
            logger.info("✅ Подключение к базе данных установлено")
            
            # Проверяем подключение
            if db_manager.is_connected():
                logger.info("✅ База данных готова к работе")
                
                # Тестируем создание таблиц
                await test_database()
                
            else:
                logger.error("❌ Не удалось подключиться к базе данных")
                return False
        else:
            logger.error("❌ Ошибка подключения к базе данных")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        return False
    finally:
        await db_manager.disconnect()
    
    return True


async def test_database():
    """Тестирование базы данных"""
    try:
        logger.info("🧪 Тестирование базы данных...")
        
        # Проверяем таблицы
        tables = await db_manager.execute("SELECT name FROM sqlite_master WHERE type='table'")
        logger.info(f"📊 Найдено таблиц: {len(tables)}")
        
        for table in tables:
            logger.info(f"  - {table['name']}")
        
        # Тестируем вставку данных
        from src.database.services import SignalService, PositionService, RunService
        from src.database.models import SignalType, SignalStrength, PositionSide, RunStatus
        
        # Создаем тестовый сигнал
        signal = await SignalService.create_signal(
            strategy_id="test_strategy",
            symbol="EURUSD",
            timeframe="1h",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MEDIUM,
            price=1.1000,
            confidence=0.75
        )
        logger.info(f"✅ Создан тестовый сигнал: {signal.signal_id}")
        
        # Создаем тестовую позицию
        position = await PositionService.create_position(
            strategy_id="test_strategy",
            symbol="EURUSD",
            side=PositionSide.LONG,
            size=0.01,
            entry_price=1.1000,
            signal_id=signal.signal_id
        )
        logger.info(f"✅ Создана тестовая позиция: {position.position_id}")
        
        # Создаем тестовый запуск
        run = await RunService.create_run(
            strategy_id="test_strategy",
            stage="test",
            created_by="init_script"
        )
        logger.info(f"✅ Создан тестовый запуск: {run.run_id}")
        
        # Получаем статистику
        signal_stats = await SignalService.get_signal_stats("test_strategy")
        position_stats = await PositionService.get_position_stats("test_strategy")
        
        logger.info(f"📈 Статистика сигналов: {signal_stats}")
        logger.info(f"📈 Статистика позиций: {position_stats}")
        
        logger.info("✅ Тестирование базы данных завершено успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        raise


async def main():
    """Основная функция"""
    print("🗄️  Инициализация базы данных торгового AI-агента")
    print("=" * 50)
    
    success = await init_database()
    
    if success:
        print("\n✅ База данных успешно инициализирована!")
        print("\n📋 Доступные команды:")
        print("  make run          # Запуск агента")
        print("  make run-dashboard # Запуск дашборда")
        print("  make run-bot      # Запуск бота")
    else:
        print("\n❌ Ошибка инициализации базы данных")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
