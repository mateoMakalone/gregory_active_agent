"""
Асинхронная версия главного модуля торгового AI-агента
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from .core.config import config
from .core.logger import setup_logging
from .data.adapters import AsyncFundingPipsAdapter, AsyncHashHedgeAdapter
from .strategies.trend_following_strategy import TrendFollowingStrategy
from .strategies.indicators import TechnicalIndicators
from .database.connection import db_manager
from .database.services import SignalService, PositionService, MetricsService
from .database.models import SignalType, SignalStrength, PositionSide
from telegram_bot.bot import async_telegram_bot


class AsyncTradingAgent:
    """Асинхронная версия торгового агента"""
    
    def __init__(self):
        """Инициализация агента"""
        self.setup_logging()
        self.setup_data_adapters()
        self.setup_strategies()
        self.is_running = False
        self.session = None
        self.db_connected = False
        
        logger.info("Асинхронный торговый AI-агент инициализирован")
    
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
            self.adapters['fundingpips'] = AsyncFundingPipsAdapter(fp_config)
            logger.info("Адаптер FundingPips настроен")
        
        # HashHedge для криптовалют
        hh_config = config.get('api.hashhedge', {})
        if hh_config.get('api_key'):
            self.adapters['hashhedge'] = AsyncHashHedgeAdapter(hh_config)
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
    
    async def connect_database(self):
        """Подключение к базе данных"""
        try:
            self.db_connected = await db_manager.connect()
            if self.db_connected:
                logger.info("✅ Подключение к базе данных установлено")
            else:
                logger.warning("⚠️ Не удалось подключиться к базе данных")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            self.db_connected = False
    
    async def disconnect_database(self):
        """Отключение от базы данных"""
        try:
            await db_manager.disconnect()
            self.db_connected = False
            logger.info("🔌 Отключение от базы данных")
        except Exception as e:
            logger.error(f"❌ Ошибка отключения от БД: {e}")
    
    async def save_signal(self, strategy_id: str, symbol: str, timeframe: str, 
                         signal_type: str, strength: str, price: float, 
                         confidence: float, **kwargs) -> Optional[str]:
        """Сохранение торгового сигнала в БД"""
        if not self.db_connected:
            logger.warning("База данных не подключена, сигнал не сохранен")
            return None
        
        try:
            # Преобразуем строки в enum
            signal_type_enum = SignalType(signal_type.upper())
            strength_enum = SignalStrength(strength.upper())
            
            signal = await SignalService.create_signal(
                strategy_id=strategy_id,
                symbol=symbol,
                timeframe=timeframe,
                signal_type=signal_type_enum,
                strength=strength_enum,
                price=price,
                confidence=confidence,
                **kwargs
            )
            
            logger.info(f"💾 Сигнал сохранен: {signal.signal_id}")
            return signal.signal_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сигнала: {e}")
            return None
    
    async def save_position(self, strategy_id: str, symbol: str, side: str, 
                           size: float, entry_price: float, signal_id: str = None, 
                           **kwargs) -> Optional[str]:
        """Сохранение торговой позиции в БД"""
        if not self.db_connected:
            logger.warning("База данных не подключена, позиция не сохранена")
            return None
        
        try:
            # Преобразуем строку в enum
            side_enum = PositionSide(side.upper())
            
            position = await PositionService.create_position(
                strategy_id=strategy_id,
                symbol=symbol,
                side=side_enum,
                size=size,
                entry_price=entry_price,
                signal_id=signal_id,
                **kwargs
            )
            
            logger.info(f"💾 Позиция сохранена: {position.position_id}")
            return position.position_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения позиции: {e}")
            return None
    
    async def update_position_prices(self, symbol: str, current_price: float):
        """Обновление цен для позиций по символу"""
        if not self.db_connected:
            return
        
        try:
            await PositionService.update_position_prices(symbol, current_price)
        except Exception as e:
            logger.error(f"❌ Ошибка обновления цен позиций: {e}")
    
    async def record_metrics(self, strategy_id: str, **metrics):
        """Запись метрик в БД"""
        if not self.db_connected:
            return
        
        try:
            await MetricsService.record_live_metrics(strategy_id, **metrics)
        except Exception as e:
            logger.error(f"❌ Ошибка записи метрик: {e}")
    
    async def connect_adapters(self) -> bool:
        """Асинхронное подключение к источникам данных"""
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
    
    async def disconnect_adapters(self):
        """Асинхронное отключение от источников данных"""
        for name, adapter in self.adapters.items():
            adapter.disconnect()
            logger.info(f"Адаптер {name} отключен")
    
    async def collect_data_async(self, symbols: List[str], timeframes: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Асинхронный сбор данных для анализа
        
        Args:
            symbols: Список символов для анализа
            timeframes: Список таймфреймов
            
        Returns:
            Словарь с данными {symbol: {timeframe: DataFrame}}
        """
        data = {}
        
        # Создаем задачи для параллельного сбора данных
        tasks = []
        for symbol in symbols:
            data[symbol] = {}
            for timeframe in timeframes:
                task = self._collect_symbol_data(symbol, timeframe)
                tasks.append((symbol, timeframe, task))
        
        # Выполняем все задачи параллельно
        results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
        
        # Обрабатываем результаты
        for i, (symbol, timeframe, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Ошибка получения данных {symbol} {timeframe}: {result}")
            elif result and not result.data.empty:
                data[symbol][timeframe] = result.data
                logger.debug(f"Получены данные: {symbol} {timeframe}, {len(result.data)} свечей")
            else:
                logger.warning(f"Пустые данные для {symbol} {timeframe}")
        
        return data
    
    async def _collect_symbol_data(self, symbol: str, timeframe: str):
        """Асинхронный сбор данных для одного символа"""
        try:
            # Определяем, какой адаптер использовать
            adapter = self._get_adapter_for_symbol(symbol)
            if not adapter:
                logger.warning(f"Нет адаптера для символа {symbol}")
                return None
            
            # Получаем данные за последние 24 часа
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            # Запускаем в отдельном потоке, чтобы не блокировать event loop
            loop = asyncio.get_running_loop()
            market_data = await loop.run_in_executor(
                None,
                lambda: adapter.get_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    limit=1000
                )
            )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Ошибка получения данных {symbol} {timeframe}: {e}")
            return None
    
    def _get_adapter_for_symbol(self, symbol: str):
        """Получение адаптера для символа"""
        # Простая логика выбора адаптера
        if 'USDT' in symbol or 'BTC' in symbol or 'ETH' in symbol:
            return self.adapters.get('hashhedge')
        else:
            return self.adapters.get('fundingpips')
    
    async def analyze_markets_async(self, data: Dict[str, Dict[str, pd.DataFrame]]) -> List:
        """
        Асинхронный анализ рынков и генерация сигналов
        
        Args:
            data: Собранные данные
            
        Returns:
            Список сгенерированных сигналов
        """
        all_signals = []
        
        # Создаем задачи для параллельного анализа
        tasks = []
        for symbol, symbol_data in data.items():
            for strategy in self.strategies:
                if strategy.is_active:
                    task = self._analyze_symbol_strategy(symbol, symbol_data, strategy)
                    tasks.append(task)
        
        # Выполняем анализ параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Ошибка анализа: {result}")
            elif result:
                all_signals.append(result)
                logger.info(f"Сгенерирован сигнал: {result}")
        
        return all_signals
    
    async def _analyze_symbol_strategy(self, symbol: str, symbol_data: Dict[str, pd.DataFrame], strategy):
        """Асинхронный анализ одного символа одной стратегией"""
        try:
            # Проверяем, есть ли все необходимые таймфреймы
            required_timeframes = strategy.get_required_timeframes()
            missing_timeframes = [tf for tf in required_timeframes if tf not in symbol_data]
            
            if missing_timeframes:
                logger.warning(f"Стратегия {strategy.name}: отсутствуют таймфреймы {missing_timeframes} для {symbol}")
                return None
            
            # Запускаем анализ в отдельном потоке
            loop = asyncio.get_running_loop()
            signal = await loop.run_in_executor(
                None,
                lambda: strategy.analyze(symbol_data)
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка анализа стратегии {strategy.name} для {symbol}: {e}")
            return None
    
    async def send_signals_async(self, signals: List):
        """Асинхронная отправка сигналов в Telegram"""
        if not signals:
            return
        
        # Создаем задачи для параллельной отправки
        tasks = []
        for signal in signals:
            # Сохраняем сигнал в БД
            signal_id = await self.save_signal(
                strategy_id=signal.get('strategy_id', 'default'),
                symbol=signal.get('symbol', ''),
                timeframe=signal.get('timeframe', '1h'),
                signal_type=signal.get('signal_type', 'HOLD'),
                strength=signal.get('strength', 'MEDIUM'),
                price=signal.get('price', 0.0),
                confidence=signal.get('confidence', 0.5),
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit'),
                metadata=signal.get('metadata', {})
            )
            
            # Добавляем signal_id к сигналу
            if signal_id:
                signal['signal_id'] = signal_id
            
            # Отправляем в Telegram
            task = async_telegram_bot.send_signal(signal)
            tasks.append(task)
        
        # Отправляем все сигналы параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка отправки сигнала {i}: {result}")
            elif result:
                logger.info(f"Сигнал {i} отправлен в Telegram")
            else:
                logger.error(f"Ошибка отправки сигнала {i}")
    
    async def run_cycle_async(self):
        """Выполнение одного асинхронного цикла анализа"""
        try:
            logger.info("Начало асинхронного цикла анализа")
            
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
            
            # Собираем данные асинхронно
            data = await self.collect_data_async(symbols, timeframes)
            
            if not data:
                logger.warning("Не удалось собрать данные")
                return
            
            # Анализируем рынки асинхронно
            signals = await self.analyze_markets_async(data)
            
            # Отправляем сигналы асинхронно
            if signals:
                await self.send_signals_async(signals)
                logger.info(f"Обработано {len(signals)} сигналов")
            else:
                logger.info("Сигналы не сгенерированы")
            
            # Записываем метрики
            await self.record_metrics(
                strategy_id="default",
                positions_count=len(await PositionService.get_open_positions()),
                latency_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )
            
            logger.info("Асинхронный цикл анализа завершен")
            
        except Exception as e:
            logger.error(f"Ошибка в асинхронном цикле анализа: {e}")
    
    async def run_async(self, interval_minutes: int = 5):
        """
        Асинхронный запуск агента
        
        Args:
            interval_minutes: Интервал между циклами в минутах
        """
        logger.info(f"Запуск асинхронного торгового агента (интервал: {interval_minutes} минут)")
        
        # Подключаемся к базе данных
        await self.connect_database()
        
        # Подключаемся к источникам данных
        if not await self.connect_adapters():
            logger.error("Не удалось подключиться к источникам данных")
            return
        
        # Тестируем Telegram-бота
        if await async_telegram_bot.test_connection():
            logger.info("Telegram-бот подключен")
        else:
            logger.warning("Telegram-бот недоступен")
        
        self.is_running = True
        
        try:
            while self.is_running:
                start_time = asyncio.get_event_loop().time()
                
                # Выполняем цикл анализа
                await self.run_cycle_async()
                
                # Ждем до следующего цикла
                elapsed_time = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, interval_minutes * 60 - elapsed_time)
                
                if sleep_time > 0:
                    logger.info(f"Ожидание {sleep_time:.1f} секунд до следующего цикла")
                    await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        finally:
            await self.stop_async()
    
    async def stop_async(self):
        """Асинхронная остановка агента"""
        logger.info("Остановка асинхронного торгового агента")
        self.is_running = False
        await self.disconnect_adapters()
        await self.disconnect_database()
        logger.info("Агент остановлен")
    
    def get_status(self) -> Dict:
        """Получение статуса агента"""
        return {
            'is_running': self.is_running,
            'adapters_connected': sum(1 for adapter in self.adapters.values() if adapter.is_connected),
            'total_adapters': len(self.adapters),
            'active_strategies': sum(1 for strategy in self.strategies if strategy.is_active),
            'total_strategies': len(self.strategies),
            'telegram_available': async_telegram_bot.is_available
        }


async def main():
    """Главная асинхронная функция"""
    # Создаем агента
    agent = AsyncTradingAgent()
    
    # Запускаем агента
    try:
        await agent.run_async(interval_minutes=5)
    except Exception as e:
        logger.error(f"Ошибка запуска агента: {e}")
    finally:
        await agent.stop_async()


if __name__ == "__main__":
    asyncio.run(main())
