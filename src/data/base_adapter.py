"""
Базовый класс для адаптеров данных
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger


class MarketData:
    """Класс для хранения рыночных данных"""
    
    def __init__(self, symbol: str, timeframe: str, data: pd.DataFrame):
        self.symbol = symbol
        self.timeframe = timeframe
        self.data = data
        self.timestamp = datetime.now()
    
    def __repr__(self):
        return f"MarketData(symbol={self.symbol}, timeframe={self.timeframe}, rows={len(self.data)})"


class BaseMarketAdapter(ABC):
    """Базовый класс для адаптеров рыночных данных"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.is_connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Подключение к источнику данных
        
        Returns:
            bool: True если подключение успешно
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Отключение от источника данных"""
        pass
    
    @abstractmethod
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: datetime, 
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> MarketData:
        """
        Получение исторических данных
        
        Args:
            symbol: Символ инструмента
            timeframe: Таймфрейм (1m, 5m, 1h, 4h, 1d)
            start_date: Начальная дата
            end_date: Конечная дата (если None, то до текущего момента)
            limit: Максимальное количество свечей
            
        Returns:
            MarketData: Объект с данными
        """
        pass
    
    @abstractmethod
    def get_realtime_data(self, symbol: str, timeframe: str) -> MarketData:
        """
        Получение данных в реальном времени
        
        Args:
            symbol: Символ инструмента
            timeframe: Таймфрейм
            
        Returns:
            MarketData: Объект с данными
        """
        pass
    
    @abstractmethod
    def subscribe_to_updates(self, symbol: str, timeframe: str, callback) -> None:
        """
        Подписка на обновления данных
        
        Args:
            symbol: Символ инструмента
            timeframe: Таймфрейм
            callback: Функция обратного вызова для новых данных
        """
        pass
    
    def normalize_data(self, raw_data: pd.DataFrame, symbol: str, timeframe: str) -> MarketData:
        """
        Нормализация данных в единый формат
        
        Args:
            raw_data: Сырые данные
            symbol: Символ инструмента
            timeframe: Таймфрейм
            
        Returns:
            MarketData: Нормализованные данные
        """
        # Стандартные колонки для OHLCV данных
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # Проверяем наличие необходимых колонок
        missing_columns = [col for col in required_columns if col not in raw_data.columns]
        if missing_columns:
            logger.warning(f"Отсутствуют колонки: {missing_columns}")
        
        # Нормализуем данные
        normalized_data = raw_data.copy()
        
        # Приводим к стандартному формату
        if 'timestamp' in normalized_data.columns:
            normalized_data['timestamp'] = pd.to_datetime(normalized_data['timestamp'])
            normalized_data.set_index('timestamp', inplace=True)
        
        # Убеждаемся, что данные отсортированы по времени
        normalized_data.sort_index(inplace=True)
        
        # Удаляем дубликаты
        normalized_data = normalized_data[~normalized_data.index.duplicated(keep='last')]
        
        logger.info(f"Данные нормализованы: {symbol} {timeframe}, {len(normalized_data)} свечей")
        
        return MarketData(symbol, timeframe, normalized_data)
    
    def validate_data(self, data: MarketData) -> bool:
        """
        Валидация данных
        
        Args:
            data: Данные для проверки
            
        Returns:
            bool: True если данные валидны
        """
        if data.data.empty:
            logger.error("Данные пусты")
            return False
        
        # Проверяем наличие OHLC данных
        ohlc_columns = ['open', 'high', 'low', 'close']
        missing_ohlc = [col for col in ohlc_columns if col not in data.data.columns]
        if missing_ohlc:
            logger.error(f"Отсутствуют OHLC колонки: {missing_ohlc}")
            return False
        
        # Проверяем логику OHLC
        invalid_ohlc = data.data[
            (data.data['high'] < data.data['low']) |
            (data.data['high'] < data.data['open']) |
            (data.data['high'] < data.data['close']) |
            (data.data['low'] > data.data['open']) |
            (data.data['low'] > data.data['close'])
        ]
        
        if not invalid_ohlc.empty:
            logger.warning(f"Найдены некорректные OHLC данные: {len(invalid_ohlc)} свечей")
        
        # Проверяем на пропуски во времени
        if len(data.data) > 1:
            time_diff = data.data.index.to_series().diff().dropna()
            expected_interval = self._get_expected_interval(data.timeframe)
            
            if expected_interval:
                unexpected_gaps = time_diff[time_diff > expected_interval * 2]
                if not unexpected_gaps.empty:
                    logger.warning(f"Найдены пропуски во времени: {len(unexpected_gaps)} интервалов")
        
        return True
    
    def _get_expected_interval(self, timeframe: str) -> Optional[timedelta]:
        """Получение ожидаемого интервала для таймфрейма"""
        intervals = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '30m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        return intervals.get(timeframe)

