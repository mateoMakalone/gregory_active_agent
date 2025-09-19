#!/usr/bin/env python3
"""
Скрипт для тестирования базы данных
"""

import sys
import asyncio
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import db_manager
from src.database.services import SignalService, PositionService, MetricsService
from src.database.models import SignalType, SignalStrength, PositionSide
from src.core.logger import setup_logging
from loguru import logger


async def test_database():
    """Тестирование базы данных"""
    try:
        # Настраиваем логирование
        setup_logging()
        
        logger.info("🧪 Начинаем тестирование базы данных...")
        
        # Подключаемся к БД
        if not await db_manager.connect():
            logger.error("❌ Не удалось подключиться к базе данных")
            return False
        
        logger.info("✅ Подключение к базе данных установлено")
        
        # Тест 1: Создание сигнала
        logger.info("📊 Тест 1: Создание сигнала")
        signal = await SignalService.create_signal(
            strategy_id="test_strategy",
            symbol="EURUSD",
            timeframe="1h",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MEDIUM,
            price=1.1000,
            confidence=0.75,
            stop_loss=1.0950,
            take_profit=1.1100
        )
        logger.info(f"✅ Создан сигнал: {signal.signal_id}")
        
        # Тест 2: Создание позиции
        logger.info("📊 Тест 2: Создание позиции")
        position = await PositionService.create_position(
            strategy_id="test_strategy",
            symbol="EURUSD",
            side=PositionSide.LONG,
            size=0.01,
            entry_price=1.1000,
            signal_id=signal.signal_id,
            stop_loss=1.0950,
            take_profit=1.1100
        )
        logger.info(f"✅ Создана позиция: {position.position_id}")
        
        # Тест 3: Обновление цен позиции
        logger.info("📊 Тест 3: Обновление цен позиции")
        await position.update_pnl(1.1050)
        logger.info(f"✅ Обновлен PnL позиции: {position.unrealized_pnl}")
        
        # Тест 4: Запись метрик
        logger.info("📊 Тест 4: Запись метрик")
        await MetricsService.record_live_metrics(
            strategy_id="test_strategy",
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.65,
            profit_factor=1.8,
            latency_ms=150,
            positions_count=1,
            pnl_daily=50.0,
            pnl_total=150.0,
            data_staleness_minutes=5,
            error_count=0,
            success_rate=0.95
        )
        logger.info("✅ Метрики записаны")
        
        # Тест 5: Получение статистики
        logger.info("📊 Тест 5: Получение статистики")
        signal_stats = await SignalService.get_signal_stats("test_strategy")
        position_stats = await PositionService.get_position_stats("test_strategy")
        
        logger.info(f"📈 Статистика сигналов: {signal_stats}")
        logger.info(f"📈 Статистика позиций: {position_stats}")
        
        # Тест 6: Получение открытых позиций
        logger.info("📊 Тест 6: Получение открытых позиций")
        open_positions = await PositionService.get_open_positions("test_strategy")
        logger.info(f"📈 Открытых позиций: {len(open_positions)}")
        
        # Тест 7: Получение последних метрик
        logger.info("📊 Тест 7: Получение последних метрик")
        latest_metrics = await MetricsService.get_latest_metrics("test_strategy")
        if latest_metrics:
            logger.info(f"📈 Последние метрики: {latest_metrics}")
        else:
            logger.warning("⚠️ Метрики не найдены")
        
        logger.info("✅ Все тесты базы данных прошли успешно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        return False
    finally:
        await db_manager.disconnect()


async def main():
    """Основная функция"""
    print("🧪 Тестирование базы данных торгового AI-агента")
    print("=" * 50)
    
    success = await test_database()
    
    if success:
        print("\n✅ Тестирование базы данных завершено успешно!")
        print("\n📋 База данных готова к использованию")
    else:
        print("\n❌ Ошибка тестирования базы данных")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
