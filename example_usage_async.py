"""
Асинхронный пример использования торгового AI-агента
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent))

from src.core.config import config
from src.core.logger import setup_logging
from src.data.adapters import AsyncFundingPipsAdapter, AsyncHashHedgeAdapter, create_test_data
from src.strategies.trend_following_strategy import TrendFollowingStrategy
from src.strategies.indicators import TechnicalIndicators
from src.execution.paper_broker import PaperBroker
from telegram_bot.bot import async_telegram_bot
from loguru import logger


async def example_data_collection():
    """Пример сбора данных"""
    logger.info("=== Пример сбора данных ===")
    
    # Создаем тестовые данные
    test_data = create_test_data("EURUSD", days=7)
    
    logger.info(f"Созданы тестовые данные: {len(test_data)} свечей")
    logger.info(f"Период: {test_data.index[0]} - {test_data.index[-1]}")
    logger.info(f"Цены: {test_data['close'].min():.4f} - {test_data['close'].max():.4f}")
    
    return test_data


async def example_indicators_calculation(data):
    """Пример расчета технических индикаторов"""
    logger.info("=== Пример расчета индикаторов ===")
    
    # Создаем объект для расчета индикаторов
    indicators = TechnicalIndicators(data)
    
    # Рассчитываем различные индикаторы
    sma_20 = indicators.sma(20)
    sma_50 = indicators.sma(50)
    rsi = indicators.rsi(14)
    macd_line, macd_signal, macd_histogram = indicators.macd()
    
    # Выводим последние значения
    logger.info(f"SMA(20): {sma_20.iloc[-1]:.4f}")
    logger.info(f"SMA(50): {sma_50.iloc[-1]:.4f}")
    logger.info(f"RSI(14): {rsi.iloc[-1]:.2f}")
    logger.info(f"MACD: {macd_line.iloc[-1]:.4f}")
    
    return {
        'sma_20': sma_20,
        'sma_50': sma_50,
        'rsi': rsi,
        'macd_line': macd_line,
        'macd_signal': macd_signal,
        'macd_histogram': macd_histogram
    }


async def example_strategy_execution():
    """Пример выполнения стратегии"""
    logger.info("=== Пример выполнения стратегии ===")
    
    # Создаем тестовые данные
    test_data = create_test_data("EURUSD", days=30)
    
    # Создаем адаптеры данных
    fundingpips = AsyncFundingPipsAdapter(test_data)
    hashhedge = AsyncHashHedgeAdapter()
    
    # Подключаемся к источникам данных
    await fundingpips.connect()
    await hashhedge.connect()
    
    # Создаем стратегию
    strategy = TrendFollowingStrategy()
    
    # Настраиваем параметры стратегии
    strategy.set_parameters({
        'sma_short': 20,
        'sma_long': 50,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04
    })
    
    logger.info("Стратегия настроена и готова к работе")
    
    # Тестируем получение данных
    try:
        # Получаем исторические данные
        history = await fundingpips.history("EURUSD", "1h", limit=100)
        logger.info(f"Получено {len(history)} исторических записей")
        
        # Получаем последнюю цену
        latest_price = await fundingpips.get_latest_price("EURUSD")
        logger.info(f"Последняя цена EURUSD: {latest_price:.4f}")
        
    except Exception as e:
        logger.error(f"Ошибка получения данных: {e}")
    
    return strategy


async def example_paper_trading():
    """Пример paper trading"""
    logger.info("=== Пример Paper Trading ===")
    
    # Создаем тестовые данные
    test_data = create_test_data("EURUSD", days=7)
    
    # Создаем адаптеры
    data_feed = AsyncFundingPipsAdapter(test_data)
    paper_broker = PaperBroker(data_feed, initial_balance=10000.0)
    
    # Подключаемся
    await data_feed.connect()
    await paper_broker.connect()
    
    logger.info("Paper broker подключен")
    
    # Тестируем создание ордера
    try:
        order_id = await paper_broker.create_order(
            symbol="EURUSD",
            side="BUY",
            order_type="MARKET",
            quantity=0.01,
            client_id="test_order_1"
        )
        
        logger.info(f"Создан ордер: {order_id}")
        
        # Ждем исполнения
        await asyncio.sleep(2)
        
        # Проверяем статус ордера
        order = await paper_broker.get_order(order_id)
        if order:
            logger.info(f"Статус ордера: {order.status.value}")
            logger.info(f"Исполнено: {order.filled_quantity}")
        
        # Получаем позиции
        positions = await paper_broker.get_positions()
        logger.info(f"Активные позиции: {len(positions)}")
        
        # Получаем баланс
        balance = await paper_broker.get_balance()
        logger.info(f"Баланс: {balance}")
        
        # Получаем сводку по счету
        summary = paper_broker.get_account_summary()
        logger.info(f"Сводка счета: {summary}")
        
    except Exception as e:
        logger.error(f"Ошибка paper trading: {e}")
    
    finally:
        await paper_broker.disconnect()
        await data_feed.disconnect()


async def example_telegram_notifications():
    """Пример уведомлений в Telegram"""
    logger.info("=== Пример Telegram уведомлений ===")
    
    try:
        # Тестируем подключение
        await async_telegram_bot.test_connection()
        
        # Отправляем тестовое сообщение
        await async_telegram_bot.send_alert(
            "Тестовое уведомление",
            "Это тестовое сообщение от торгового AI-агента",
            "INFO"
        )
        
        logger.info("Telegram уведомление отправлено")
        
    except Exception as e:
        logger.error(f"Ошибка отправки Telegram: {e}")


async def main():
    """Главная функция"""
    print("🚀 Асинхронный пример использования торгового AI-агента")
    print("=" * 60)
    
    # Настраиваем логирование
    setup_logging()
    
    try:
        # 1. Сбор данных
        data = await example_data_collection()
        
        # 2. Расчет индикаторов
        indicators = await example_indicators_calculation(data)
        
        # 3. Выполнение стратегии
        strategy = await example_strategy_execution()
        
        # 4. Paper trading
        await example_paper_trading()
        
        # 5. Telegram уведомления
        await example_telegram_notifications()
        
        logger.info("✅ Все примеры выполнены успешно!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в примерах: {e}")


if __name__ == "__main__":
    asyncio.run(main())
