"""
Главный модуль торгового AI-агента
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from .core.config import config
from .core.logger import setup_logging
from .data.fundingpips_adapter import FundingPipsAdapter
from .data.hashhedge_adapter import HashHedgeAdapter
from .strategies.trend_following_strategy import TrendFollowingStrategy
from .strategies.indicators import TechnicalIndicators
from telegram_bot.bot import telegram_bot


class TradingAgent:
    """Основной класс торгового агента"""
    
    def __init__(self):
        """Инициализация агента"""
        self.setup_logging()
        self.setup_data_adapters()
        self.setup_strategies()
        self.is_running = False
        
        logger.info("Торговый AI-агент инициализирован")
    
    def setup_logging(self):
        """Настройка логирования"""
        setup_logging()
        logger.info("Система логирования настроена")
    
    def setup_data_adapters(self):
        """Настройка адаптеров данных"""
        self.adapters = {}
        
        # FundingPips для форекс/акций
        fp_config = config.get('api.fundingpips', {})
        if fp_config.get('api_key'):
            self.adapters['fundingpips'] = FundingPipsAdapter(fp_config)
            logger.info("Адаптер FundingPips настроен")
        
        # HashHedge для криптовалют
        hh_config = config.get('api.hashhedge', {})
        if hh_config.get('api_key'):
            self.adapters['hashhedge'] = HashHedgeAdapter(hh_config)
            logger.info("Адаптер HashHedge настроен")
        
        if not self.adapters:
            logger.warning("Нет настроенных адаптеров данных")
    
    def setup_strategies(self):
        """Настройка торговых стратегий"""
        self.strategies = []
        
        # Стратегия следования за трендом
        trend_config = {
            'trend_sma_period': 50,
            'confirmation_sma_period': 20,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'volume_threshold': 1.2,
            'min_confidence': 0.6,
            'max_signals_per_day': 10,
            'cooldown_minutes': 30
        }
        
        self.strategies.append(TrendFollowingStrategy(trend_config))
        logger.info(f"Настроено {len(self.strategies)} стратегий")
    
    def connect_adapters(self) -> bool:
        """Подключение к источникам данных"""
        connected = 0
        
        for name, adapter in self.adapters.items():
            if adapter.connect():
                connected += 1
                logger.info(f"Адаптер {name} подключен")
            else:
                logger.error(f"Ошибка подключения адаптера {name}")
        
        if connected == 0:
            logger.error("Не удалось подключиться ни к одному источнику данных")
            return False
        
        logger.info(f"Подключено {connected} адаптеров из {len(self.adapters)}")
        return True
    
    def disconnect_adapters(self):
        """Отключение от источников данных"""
        for name, adapter in self.adapters.items():
            adapter.disconnect()
            logger.info(f"Адаптер {name} отключен")
    
    def collect_data(self, symbols: List[str], timeframes: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Сбор данных для анализа
        
        Args:
            symbols: Список символов для анализа
            timeframes: Список таймфреймов
            
        Returns:
            Словарь с данными {symbol: {timeframe: DataFrame}}
        """
        data = {}
        
        for symbol in symbols:
            data[symbol] = {}
            
            # Определяем, какой адаптер использовать
            adapter = self._get_adapter_for_symbol(symbol)
            if not adapter:
                logger.warning(f"Нет адаптера для символа {symbol}")
                continue
            
            for timeframe in timeframes:
                try:
                    # Получаем данные за последние 24 часа
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=1)
                    
                    market_data = adapter.get_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date,
                        limit=1000
                    )
                    
                    if market_data and not market_data.data.empty:
                        data[symbol][timeframe] = market_data.data
                        logger.debug(f"Получены данные: {symbol} {timeframe}, {len(market_data.data)} свечей")
                    else:
                        logger.warning(f"Пустые данные для {symbol} {timeframe}")
                        
                except Exception as e:
                    logger.error(f"Ошибка получения данных {symbol} {timeframe}: {e}")
        
        return data
    
    def _get_adapter_for_symbol(self, symbol: str):
        """Получение адаптера для символа"""
        # Простая логика выбора адаптера
        if 'USDT' in symbol or 'BTC' in symbol or 'ETH' in symbol:
            return self.adapters.get('hashhedge')
        else:
            return self.adapters.get('fundingpips')
    
    def analyze_markets(self, data: Dict[str, Dict[str, pd.DataFrame]]) -> List:
        """
        Анализ рынков и генерация сигналов
        
        Args:
            data: Собранные данные
            
        Returns:
            Список сгенерированных сигналов
        """
        all_signals = []
        
        for symbol, symbol_data in data.items():
            logger.info(f"Анализ символа {symbol}")
            
            for strategy in self.strategies:
                if not strategy.is_active:
                    continue
                
                try:
                    # Проверяем, есть ли все необходимые таймфреймы
                    required_timeframes = strategy.get_required_timeframes()
                    missing_timeframes = [tf for tf in required_timeframes if tf not in symbol_data]
                    
                    if missing_timeframes:
                        logger.warning(f"Стратегия {strategy.name}: отсутствуют таймфреймы {missing_timeframes} для {symbol}")
                        continue
                    
                    # Анализируем данные
                    signal = strategy.analyze(symbol_data)
                    
                    if signal:
                        all_signals.append(signal)
                        logger.info(f"Сгенерирован сигнал: {signal}")
                    
                except Exception as e:
                    logger.error(f"Ошибка анализа стратегии {strategy.name} для {symbol}: {e}")
        
        return all_signals
    
    def send_signals(self, signals: List):
        """Отправка сигналов в Telegram"""
        if not signals:
            return
        
        for signal in signals:
            try:
                if telegram_bot.send_signal(signal):
                    logger.info(f"Сигнал отправлен в Telegram: {signal}")
                else:
                    logger.error(f"Ошибка отправки сигнала в Telegram: {signal}")
            except Exception as e:
                logger.error(f"Ошибка отправки сигнала: {e}")
    
    def run_cycle(self):
        """Выполнение одного цикла анализа"""
        try:
            logger.info("Начало цикла анализа")
            
            # Получаем конфигурацию торговли
            trading_config = config.trading_config
            symbols = []
            
            # Собираем символы из конфигурации
            for asset_type, asset_symbols in trading_config.get('assets', {}).items():
                symbols.extend(asset_symbols)
            
            if not symbols:
                logger.warning("Нет символов для анализа")
                return
            
            # Получаем таймфреймы
            timeframes = trading_config.get('timeframes', ['4h', '1h', '5m'])
            
            # Собираем данные
            data = self.collect_data(symbols, timeframes)
            
            if not data:
                logger.warning("Не удалось собрать данные")
                return
            
            # Анализируем рынки
            signals = self.analyze_markets(data)
            
            # Отправляем сигналы
            if signals:
                self.send_signals(signals)
                logger.info(f"Обработано {len(signals)} сигналов")
            else:
                logger.info("Сигналы не сгенерированы")
            
            logger.info("Цикл анализа завершен")
            
        except Exception as e:
            logger.error(f"Ошибка в цикле анализа: {e}")
    
    def run(self, interval_minutes: int = 5):
        """
        Запуск агента
        
        Args:
            interval_minutes: Интервал между циклами в минутах
        """
        logger.info(f"Запуск торгового агента (интервал: {interval_minutes} минут)")
        
        # Подключаемся к источникам данных
        if not self.connect_adapters():
            logger.error("Не удалось подключиться к источникам данных")
            return
        
        # Тестируем Telegram-бота
        if telegram_bot.test_connection():
            logger.info("Telegram-бот подключен")
        else:
            logger.warning("Telegram-бот недоступен")
        
        self.is_running = True
        
        try:
            while self.is_running:
                start_time = time.time()
                
                # Выполняем цикл анализа
                self.run_cycle()
                
                # Ждем до следующего цикла
                elapsed_time = time.time() - start_time
                sleep_time = max(0, interval_minutes * 60 - elapsed_time)
                
                if sleep_time > 0:
                    logger.info(f"Ожидание {sleep_time:.1f} секунд до следующего цикла")
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка агента"""
        logger.info("Остановка торгового агента")
        self.is_running = False
        self.disconnect_adapters()
        logger.info("Агент остановлен")
    
    def get_status(self) -> Dict:
        """Получение статуса агента"""
        return {
            'is_running': self.is_running,
            'adapters_connected': sum(1 for adapter in self.adapters.values() if adapter.is_connected),
            'total_adapters': len(self.adapters),
            'active_strategies': sum(1 for strategy in self.strategies if strategy.is_active),
            'total_strategies': len(self.strategies),
            'telegram_available': telegram_bot.is_available
        }


def main():
    """Главная функция"""
    # Создаем агента
    agent = TradingAgent()
    
    # Запускаем агента
    try:
        agent.run(interval_minutes=5)
    except Exception as e:
        logger.error(f"Ошибка запуска агента: {e}")
    finally:
        agent.stop()


if __name__ == "__main__":
    main()

