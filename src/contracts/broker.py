"""
Контракт Broker/Execution для торговых операций
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import uuid


class OrderSide(Enum):
    """Сторона ордера"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Тип ордера"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    """Статус ордера"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class Order:
    """Структура ордера"""
    id: str
    client_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    exchange_order_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at


@dataclass
class Position:
    """Структура позиции"""
    symbol: str
    quantity: float
    average_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class Execution:
    """Структура исполнения"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class Broker(ABC):
    """Абстрактный контракт для торговых операций"""
    
    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_id: Optional[str] = None
    ) -> str:
        """
        Создание ордера
        
        Args:
            symbol: Торговый символ
            side: Сторона ордера
            order_type: Тип ордера
            quantity: Количество
            price: Цена (для лимитных ордеров)
            stop_price: Стоп-цена (для стоп-ордеров)
            client_id: ID клиента для идемпотентности
            
        Returns:
            str: ID ордера
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Отмена ордера
        
        Args:
            order_id: ID ордера
            
        Returns:
            bool: True если отменен успешно
        """
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        Получение ордера по ID
        
        Args:
            order_id: ID ордера
            
        Returns:
            Order или None: Ордер или None если не найден
        """
        pass
    
    @abstractmethod
    async def get_orders(
        self, 
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100
    ) -> List[Order]:
        """
        Получение списка ордеров
        
        Args:
            symbol: Фильтр по символу
            status: Фильтр по статусу
            limit: Максимальное количество
            
        Returns:
            List[Order]: Список ордеров
        """
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Получение позиций
        
        Args:
            symbol: Фильтр по символу
            
        Returns:
            List[Position]: Список позиций
        """
        pass
    
    @abstractmethod
    async def get_executions(
        self, 
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Execution]:
        """
        Получение исполнений
        
        Args:
            order_id: Фильтр по ID ордера
            symbol: Фильтр по символу
            limit: Максимальное количество
            
        Returns:
            List[Execution]: Список исполнений
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """
        Получение баланса
        
        Returns:
            Dict[str, float]: Баланс по валютам
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
        """Отключение от брокера"""
        pass


class BrokerError(Exception):
    """Ошибка брокера"""
    pass


class OrderError(BrokerError):
    """Ошибка ордера"""
    pass


class InsufficientFundsError(OrderError):
    """Недостаточно средств"""
    pass


class InvalidOrderError(OrderError):
    """Невалидный ордер"""
    pass
