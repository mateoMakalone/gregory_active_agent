"""
Контракт Portfolio Manager - единый источник правды по балансам/позициям/PnL
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .broker import Position, Order, Execution


class PortfolioStatus(Enum):
    """Статус портфеля"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


@dataclass
class Balance:
    """Баланс по валюте"""
    currency: str
    free: float  # Свободные средства
    used: float  # Использованные средства
    total: float  # Общий баланс
    updated_at: datetime


@dataclass
class PortfolioSnapshot:
    """Снимок портфеля"""
    timestamp: datetime
    total_value: float
    cash_value: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    total_pnl: float
    positions: List[Position]
    balances: List[Balance]


@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    total_return: float  # Общая доходность
    daily_return: float  # Дневная доходность
    sharpe_ratio: float  # Коэффициент Шарпа
    max_drawdown: float  # Максимальная просадка
    win_rate: float  # Процент выигрышных сделок
    profit_factor: float  # Профит-фактор
    avg_trade_duration: float  # Средняя длительность сделки
    total_trades: int  # Общее количество сделок


class PortfolioManager(ABC):
    """Абстрактный контракт для управления портфелем"""
    
    @abstractmethod
    async def get_balance(self, currency: str = "USD") -> Balance:
        """
        Получение баланса по валюте
        
        Args:
            currency: Валюта
            
        Returns:
            Balance: Баланс
        """
        pass
    
    @abstractmethod
    async def get_all_balances(self) -> List[Balance]:
        """
        Получение всех балансов
        
        Returns:
            List[Balance]: Список балансов
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
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Получение позиции по символу
        
        Args:
            symbol: Торговый символ
            
        Returns:
            Position или None: Позиция или None если не найдена
        """
        pass
    
    @abstractmethod
    async def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """
        Получение снимка портфеля
        
        Returns:
            PortfolioSnapshot: Снимок портфеля
        """
        pass
    
    @abstractmethod
    async def get_performance_metrics(
        self, 
        days: int = 30
    ) -> PerformanceMetrics:
        """
        Получение метрик производительности
        
        Args:
            days: Количество дней для расчета
            
        Returns:
            PerformanceMetrics: Метрики производительности
        """
        pass
    
    @abstractmethod
    async def update_position(
        self, 
        symbol: str, 
        quantity: float, 
        price: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Обновление позиции
        
        Args:
            symbol: Торговый символ
            quantity: Количество (положительное для покупки, отрицательное для продажи)
            price: Цена
            timestamp: Время обновления
        """
        pass
    
    @abstractmethod
    async def update_balance(
        self, 
        currency: str, 
        free: float, 
        used: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Обновление баланса
        
        Args:
            currency: Валюта
            free: Свободные средства
            used: Использованные средства
            timestamp: Время обновления
        """
        pass
    
    @abstractmethod
    async def process_execution(self, execution: Execution):
        """
        Обработка исполнения ордера
        
        Args:
            execution: Исполнение ордера
        """
        pass
    
    @abstractmethod
    async def calculate_unrealized_pnl(
        self, 
        symbol: str, 
        current_price: float
    ) -> float:
        """
        Расчет нереализованного PnL
        
        Args:
            symbol: Торговый символ
            current_price: Текущая цена
            
        Returns:
            float: Нереализованный PnL
        """
        pass
    
    @abstractmethod
    async def get_total_value(self, base_currency: str = "USD") -> float:
        """
        Получение общей стоимости портфеля
        
        Args:
            base_currency: Базовая валюта
            
        Returns:
            float: Общая стоимость
        """
        pass
    
    @abstractmethod
    async def get_available_margin(self, currency: str = "USD") -> float:
        """
        Получение доступной маржи
        
        Args:
            currency: Валюта
            
        Returns:
            float: Доступная маржа
        """
        pass
    
    @abstractmethod
    async def get_margin_used(self, currency: str = "USD") -> float:
        """
        Получение использованной маржи
        
        Args:
            currency: Валюта
            
        Returns:
            float: Использованная маржа
        """
        pass
    
    @abstractmethod
    async def is_margin_sufficient(
        self, 
        required_margin: float, 
        currency: str = "USD"
    ) -> bool:
        """
        Проверка достаточности маржи
        
        Args:
            required_margin: Требуемая маржа
            currency: Валюта
            
        Returns:
            bool: True если маржи достаточно
        """
        pass
    
    @abstractmethod
    async def get_portfolio_status(self) -> PortfolioStatus:
        """
        Получение статуса портфеля
        
        Returns:
            PortfolioStatus: Статус портфеля
        """
        pass
    
    @abstractmethod
    async def set_portfolio_status(self, status: PortfolioStatus):
        """
        Установка статуса портфеля
        
        Args:
            status: Новый статус
        """
        pass
    
    @abstractmethod
    async def reset_daily_metrics(self):
        """Сброс дневных метрик (вызывается в начале дня)"""
        pass
    
    @abstractmethod
    async def get_trade_history(
        self, 
        symbol: Optional[str] = None,
        days: int = 30
    ) -> List[Execution]:
        """
        Получение истории сделок
        
        Args:
            symbol: Фильтр по символу
            days: Количество дней
            
        Returns:
            List[Execution]: История сделок
        """
        pass


class PortfolioError(Exception):
    """Ошибка портфеля"""
    pass


class InsufficientFundsError(PortfolioError):
    """Недостаточно средств"""
    pass


class PositionNotFoundError(PortfolioError):
    """Позиция не найдена"""
    pass


class InvalidPortfolioStateError(PortfolioError):
    """Невалидное состояние портфеля"""
    pass
