#!/usr/bin/env python3
"""
E2E тест торгового AI-агента в paper режиме
"""

import sys
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.logger import setup_logging
from src.data.adapters import AsyncFundingPipsAdapter, create_test_data
from src.execution.paper_broker import PaperBroker
from src.database.connection import db_manager
from src.database.services import SignalService, PositionService, RunService
from src.database.models import SignalType, SignalStrength, PositionSide
from loguru import logger


async def test_e2e_pipeline():
    """E2E тест полного пайплайна"""
    logger.info("🧪 Запуск E2E теста торгового AI-агента")
    
    try:
        # 1. Подключаемся к базе данных
        logger.info("1️⃣ Подключение к базе данных...")
        if not await db_manager.connect():
            raise Exception("Не удалось подключиться к базе данных")
        logger.info("✅ База данных подключена")
        
        # 2. Создаем тестовые данные
        logger.info("2️⃣ Создание тестовых данных...")
        test_data = create_test_data("EURUSD", days=7)
        logger.info(f"✅ Создано {len(test_data)} записей данных")
        
        # 3. Создаем адаптеры и брокера
        logger.info("3️⃣ Создание адаптеров и брокера...")
        data_feed = AsyncFundingPipsAdapter(test_data)
        paper_broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await data_feed.connect()
        await paper_broker.connect()
        logger.info("✅ Адаптеры и брокер подключены")
        
        # 4. Создаем тестовый запуск
        logger.info("4️⃣ Создание тестового запуска...")
        run = await RunService.create_run(
            strategy_id="test_strategy",
            stage="running",
            model_id="test_model",
            created_by="e2e_test"
        )
        logger.info(f"✅ Создан запуск: {run.run_id}")
        
        # 5. Тестируем получение исторических данных
        logger.info("5️⃣ Тестирование получения исторических данных...")
        history = await data_feed.history("EURUSD", "1h", limit=50)
        logger.info(f"✅ Получено {len(history)} исторических записей")
        
        # 6. Тестируем создание сигнала
        logger.info("6️⃣ Тестирование создания сигнала...")
        signal = await SignalService.create_signal(
            strategy_id="test_strategy",
            symbol="EURUSD",
            timeframe="1h",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MEDIUM,
            price=1.1000,
            confidence=0.75,
            stop_loss=1.0950,
            take_profit=1.1100,
            reason="E2E test signal"
        )
        logger.info(f"✅ Создан сигнал: {signal.signal_id}")
        
        # 7. Тестируем создание ордера
        logger.info("7️⃣ Тестирование создания ордера...")
        order_id = await paper_broker.create_order(
            symbol="EURUSD",
            side="BUY",
            order_type="MARKET",
            quantity=0.01,
            client_id="e2e_test_order"
        )
        logger.info(f"✅ Создан ордер: {order_id}")
        
        # 8. Ждем исполнения ордера
        logger.info("8️⃣ Ожидание исполнения ордера...")
        await asyncio.sleep(3)  # Ждем исполнения
        
        # 9. Проверяем статус ордера
        logger.info("9️⃣ Проверка статуса ордера...")
        order = await paper_broker.get_order(order_id)
        if order:
            logger.info(f"✅ Статус ордера: {order.status.value}")
            logger.info(f"✅ Исполнено: {order.filled_quantity}")
        
        # 10. Проверяем позиции
        logger.info("🔟 Проверка позиций...")
        positions = await paper_broker.get_positions()
        logger.info(f"✅ Активные позиции: {len(positions)}")
        for pos in positions:
            logger.info(f"   - {pos.symbol}: {pos.quantity} @ {pos.average_price}")
        
        # 11. Проверяем баланс
        logger.info("1️⃣1️⃣ Проверка баланса...")
        balance = await paper_broker.get_balance()
        logger.info(f"✅ Баланс: {balance}")
        
        # 12. Получаем сводку по счету
        logger.info("1️⃣2️⃣ Получение сводки по счету...")
        summary = paper_broker.get_account_summary()
        logger.info(f"✅ Сводка счета: {summary}")
        
        # 13. Тестируем получение сигналов из БД
        logger.info("1️⃣3️⃣ Тестирование получения сигналов из БД...")
        signals = await SignalService.get_recent_signals("test_strategy", hours=24)
        logger.info(f"✅ Получено {len(signals)} сигналов из БД")
        
        # 14. Тестируем получение позиций из БД
        logger.info("1️⃣4️⃣ Тестирование получения позиций из БД...")
        db_positions = await PositionService.get_open_positions("test_strategy")
        logger.info(f"✅ Получено {len(db_positions)} позиций из БД")
        
        # 15. Тестируем live подписку (несколько баров)
        logger.info("1️⃣5️⃣ Тестирование live подписки...")
        bar_count = 0
        async for bar in data_feed.subscribe("EURUSD", "1h"):
            bar_count += 1
            logger.info(f"   Получен бар {bar_count}: {bar.timestamp} - {bar.close:.4f}")
            if bar_count >= 5:  # Ограничиваем количество для теста
                break
        
        logger.info(f"✅ Получено {bar_count} live баров")
        
        # 16. Очистка
        logger.info("1️⃣6️⃣ Очистка ресурсов...")
        await paper_broker.disconnect()
        await data_feed.disconnect()
        await db_manager.disconnect()
        logger.info("✅ Ресурсы очищены")
        
        logger.info("🎉 E2E тест завершен успешно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка в E2E тесте: {e}")
        return False


async def main():
    """Главная функция"""
    print("🧪 E2E тест торгового AI-агента")
    print("=" * 50)
    
    # Настраиваем логирование
    setup_logging()
    
    success = await test_e2e_pipeline()
    
    if success:
        print("✅ E2E тест прошел успешно!")
        sys.exit(0)
    else:
        print("❌ E2E тест не прошел!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
