"""
Пример использования торгового AI-агента
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent))

from src.core.config import config
from src.core.logger import setup_logging
from src.data.fundingpips_adapter import FundingPipsAdapter
from src.data.hashhedge_adapter import HashHedgeAdapter
from src.strategies.trend_following_strategy import TrendFollowingStrategy
from src.strategies.indicators import TechnicalIndicators
from telegram_bot.bot import telegram_bot
from loguru import logger


def example_data_collection():
    """Пример сбора данных"""
    logger.info("=== Пример сбора данных ===")
    
    # Создаем тестовые данные
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='H')
    
    # Генерируем тестовые OHLCV данные
    base_price = 1.0850
    price_changes = pd.Series(range(len(dates))) * 0.0001
    
    test_data = pd.DataFrame({
        'timestamp': dates,
        'open': base_price + price_changes,
        'high': base_price + price_changes + 0.001,
        'low': base_price + price_changes - 0.001,
        'close': base_price + price_changes + 0.0005,
        'volume': 1000 + pd.Series(range(len(dates))) * 10
    })
    
    test_data.set_index('timestamp', inplace=True)
    
    logger.info(f"Созданы тестовые данные: {len(test_data)} свечей")
    logger.info(f"Период: {test_data.index[0]} - {test_data.index[-1]}")
    logger.info(f"Цены: {test_data['close'].min():.4f} - {test_data['close'].max():.4f}")
    
    return test_data


def example_indicators_calculation(data):
    """Пример расчета технических индикаторов"""
    logger.info("=== Пример расчета индикаторов ===")
    
    # Создаем объект для расчета индикаторов
    indicators = TechnicalIndicators(data)
    
    # Рассчитываем различные индикаторы
    sma_20 = indicators.sma(20)
    sma_50 = indicators.sma(50)
    rsi = indicators.rsi(14)
    macd_line, macd_signal, macd_histogram = indicators.macd()
    bb_upper, bb_middle, bb_lower = indicators.bollinger_bands()
    
    # Выводим последние значения
    logger.info(f"SMA 20: {sma_20.iloc[-1]:.4f}")
    logger.info(f"SMA 50: {sma_50.iloc[-1]:.4f}")
    logger.info(f"RSI: {rsi.iloc[-1]:.2f}")
    logger.info(f"MACD: {macd_line.iloc[-1]:.6f}")
    logger.info(f"BB Upper: {bb_upper.iloc[-1]:.4f}")
    logger.info(f"BB Lower: {bb_lower.iloc[-1]:.4f}")
    
    return {
        'sma_20': sma_20,
        'sma_50': sma_50,
        'rsi': rsi,
        'macd_line': macd_line,
        'macd_signal': macd_signal,
        'macd_histogram': macd_histogram,
        'bb_upper': bb_upper,
        'bb_middle': bb_middle,
        'bb_lower': bb_lower
    }


def example_strategy_analysis(data):
    """Пример анализа стратегии"""
    logger.info("=== Пример анализа стратегии ===")
    
    # Создаем стратегию
    strategy_config = {
        'trend_sma_period': 20,
        'confirmation_sma_period': 10,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'volume_threshold': 1.2,
        'min_confidence': 0.6,
        'max_signals_per_day': 10,
        'cooldown_minutes': 30
    }
    
    strategy = TrendFollowingStrategy(strategy_config)
    
    # Подготавливаем данные для анализа (симулируем разные таймфреймы)
    data_4h = data.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    data_1h = data.resample('1H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    data_5m = data.resample('5T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Создаем словарь с данными по таймфреймам
    multi_timeframe_data = {
        '4h': data_4h,
        '1h': data_1h,
        '5m': data_5m
    }
    
    # Анализируем данные
    signal = strategy.analyze(multi_timeframe_data)
    
    if signal:
        logger.info(f"Сгенерирован сигнал: {signal}")
        logger.info(f"Тип: {signal.signal_type.value}")
        logger.info(f"Сила: {signal.strength.name}")
        logger.info(f"Уверенность: {signal.confidence:.2%}")
        logger.info(f"Цена: {signal.price:.4f}")
        
        if signal.stop_loss:
            logger.info(f"Стоп-лосс: {signal.stop_loss:.4f}")
        if signal.take_profit:
            logger.info(f"Тейк-профит: {signal.take_profit:.4f}")
    else:
        logger.info("Сигнал не сгенерирован")
    
    return signal


def example_telegram_notification(signal):
    """Пример отправки уведомления в Telegram"""
    logger.info("=== Пример отправки в Telegram ===")
    
    if signal:
        # Отправляем сигнал
        success = telegram_bot.send_signal(signal)
        if success:
            logger.info("Сигнал отправлен в Telegram")
        else:
            logger.warning("Ошибка отправки сигнала в Telegram")
    else:
        # Отправляем тестовое уведомление
        success = telegram_bot.send_alert(
            "🤖 Тестовое уведомление",
            "Торговый AI-агент работает корректно!",
            "INFO"
        )
        if success:
            logger.info("Тестовое уведомление отправлено в Telegram")
        else:
            logger.warning("Ошибка отправки уведомления в Telegram")


def example_performance_analysis(strategy):
    """Пример анализа производительности стратегии"""
    logger.info("=== Пример анализа производительности ===")
    
    # Получаем метрики стратегии
    metrics = strategy.get_performance_metrics()
    
    if metrics:
        logger.info("Метрики производительности:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value}")
    else:
        logger.info("Нет данных для анализа производительности")


def main():
    """Главная функция примера"""
    # Настраиваем логирование
    setup_logging()
    
    logger.info("🚀 Запуск примера использования торгового AI-агента")
    
    try:
        # 1. Сбор данных
        data = example_data_collection()
        
        # 2. Расчет индикаторов
        indicators = example_indicators_calculation(data)
        
        # 3. Анализ стратегии
        signal = example_strategy_analysis(data)
        
        # 4. Отправка в Telegram
        example_telegram_notification(signal)
        
        # 5. Анализ производительности
        if signal:
            strategy = TrendFollowingStrategy({})
            example_performance_analysis(strategy)
        
        logger.info("✅ Пример выполнен успешно!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в примере: {e}")
        raise


if __name__ == "__main__":
    main()

