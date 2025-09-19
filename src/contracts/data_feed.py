"""
Контракт DataFeed для получения рыночных данных
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import pandas as pd


@dataclass
class Bar:
    """Структура бара"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str


@dataclass
class Tick:
    """Структура тика"""
    timestamp: datetime
    price: float
    volume: float
    symbol: str
    bid: Optional[float] = None
    ask: Optional[float] = None


class DataFeed(ABC):
    """Абстрактный контракт для получения рыночных данных"""
    
    @abstractmethod
    async def subscribe(
        self, 
        ticker: str, 
        timeframe: str
    ) -> AsyncIterator[Union[Bar, Tick]]:
        """
        Подписка на рыночные данные
        
        Args:
            ticker: Торговый символ (например, 'EURUSD', 'BTCUSDT')
            timeframe: Таймфрейм ('1m', '5m', '1h', '4h', '1d')
            
        Yields:
            Bar или Tick: Рыночные данные
        """
        pass
    
    @abstractmethod
    async def history(
        self, 
        ticker: str, 
        timeframe: str, 
        since: Optional[datetime] = None, 
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Получение исторических данных
        
        Args:
            ticker: Торговый символ
            timeframe: Таймфрейм
            since: Начальная дата (включительно)
            until: Конечная дата (включительно)
            limit: Максимальное количество записей
            
        Returns:
            pd.DataFrame: Исторические данные с колонками [timestamp, open, high, low, close, volume]
        """
        pass
    
    @abstractmethod
    async def get_latest_price(self, ticker: str) -> float:
        """
        Получение последней цены
        
        Args:
            ticker: Торговый символ
            
        Returns:
            float: Последняя цена
        """
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Проверка подключения
        
        Returns:
            bool: True если подключен
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Отключение от источника данных"""
        pass


class DataFeedError(Exception):
    """Ошибка источника данных"""
    pass


class ConnectionError(DataFeedError):
    """Ошибка подключения"""
    pass


class DataError(DataFeedError):
    """Ошибка данных"""
    pass
