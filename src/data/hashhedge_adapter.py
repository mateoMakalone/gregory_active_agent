"""
Адаптер для HashHedge API (криптовалюты)
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
import time
from loguru import logger

from .base_adapter import BaseMarketAdapter, MarketData


class HashHedgeAdapter(BaseMarketAdapter):
    """Адаптер для работы с HashHedge API"""
    
    def __init__(self, config: Dict):
        super().__init__("HashHedge", config)
        self.api_key = config.get('api_key')
        self.secret_key = config.get('secret_key')
        self.base_url = config.get('base_url', 'https://api.hashhedge.com')
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Настройка HTTP сессии"""
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'X-Secret-Key': self.secret_key,
            'Content-Type': 'application/json'
        })
    
    def connect(self) -> bool:
        """Подключение к HashHedge API"""
        try:
            # Тестовый запрос для проверки подключения
            response = self.session.get(f"{self.base_url}/v1/account")
            response.raise_for_status()
            
            self.is_connected = True
            logger.info("Успешное подключение к HashHedge API")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка подключения к HashHedge API: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Отключение от API"""
        self.session.close()
        self.is_connected = False
        logger.info("Отключение от HashHedge API")
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: datetime, 
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> MarketData:
        """Получение исторических данных"""
        if not self.is_connected:
            raise ConnectionError("Нет подключения к API")
        
        try:
            # Конвертируем таймфрейм в формат HashHedge
            hh_timeframe = self._convert_timeframe(timeframe)
            
            # Параметры запроса
            params = {
                'symbol': symbol,
                'interval': hh_timeframe,
                'startTime': int(start_date.timestamp() * 1000),
                'limit': limit or 1000
            }
            
            if end_date:
                params['endTime'] = int(end_date.timestamp() * 1000)
            
            # Запрос данных
            response = self.session.get(f"{self.base_url}/v1/klines", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Конвертируем в DataFrame
            df = self._parse_klines_data(data, symbol)
            
            # Нормализуем данные
            market_data = self.normalize_data(df, symbol, timeframe)
            
            # Валидируем данные
            if not self.validate_data(market_data):
                raise ValueError("Данные не прошли валидацию")
            
            logger.info(f"Получены исторические данные: {symbol} {timeframe}, {len(df)} свечей")
            return market_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения данных от HashHedge: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка обработки данных: {e}")
            raise
    
    def get_realtime_data(self, symbol: str, timeframe: str) -> MarketData:
        """Получение данных в реальном времени"""
        if not self.is_connected:
            raise ConnectionError("Нет подключения к API")
        
        try:
            # Получаем последние данные
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)  # Последние 24 часа
            
            return self.get_historical_data(symbol, timeframe, start_date, end_date, limit=100)
            
        except Exception as e:
            logger.error(f"Ошибка получения данных в реальном времени: {e}")
            raise
    
    def subscribe_to_updates(self, symbol: str, timeframe: str, callback: Callable) -> None:
        """Подписка на обновления данных (WebSocket)"""
        # TODO: Реализовать WebSocket подключение для реального времени
        logger.warning("WebSocket подписка не реализована для HashHedge")
        pass
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Конвертация таймфрейма в формат HashHedge"""
        timeframe_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        
        if timeframe not in timeframe_map:
            raise ValueError(f"Неподдерживаемый таймфрейм: {timeframe}")
        
        return timeframe_map[timeframe]
    
    def _parse_klines_data(self, data: list, symbol: str) -> pd.DataFrame:
        """Парсинг данных klines в DataFrame"""
        if not data:
            return pd.DataFrame()
        
        # Создаем DataFrame из массива klines
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades_count', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])
        
        # Конвертируем типы данных
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Устанавливаем timestamp как индекс
        df.set_index('timestamp', inplace=True)
        
        # Оставляем только необходимые колонки
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        return df
    
    def get_ticker_price(self, symbol: str) -> Dict:
        """Получение текущей цены инструмента"""
        if not self.is_connected:
            raise ConnectionError("Нет подключения к API")
        
        try:
            response = self.session.get(f"{self.base_url}/v1/ticker/price", params={'symbol': symbol})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения цены {symbol}: {e}")
            raise
    
    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Получение стакана заявок"""
        if not self.is_connected:
            raise ConnectionError("Нет подключения к API")
        
        try:
            response = self.session.get(f"{self.base_url}/v1/depth", params={'symbol': symbol, 'limit': limit})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения стакана {symbol}: {e}")
            raise
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> list:
        """Получение последних сделок"""
        if not self.is_connected:
            raise ConnectionError("Нет подключения к API")
        
        try:
            response = self.session.get(f"{self.base_url}/v1/trades", params={'symbol': symbol, 'limit': limit})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения сделок {symbol}: {e}")
            raise

