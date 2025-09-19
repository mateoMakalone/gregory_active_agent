"""
Контракт Risk Engine для управления рисками
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd

from .broker import Order, Position, OrderSide, OrderType


class RiskLevel(Enum):
    """Уровень риска"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskLimits:
    """Лимиты риска"""
    max_daily_loss: float = 0.02  # 2% от капитала
    max_position_size: float = 0.1  # 10% от капитала
    max_correlation: float = 0.7  # Максимальная корреляция позиций
    max_drawdown: float = 0.15  # 15% максимальная просадка
    max_leverage: float = 1.0  # Максимальное плечо
    stop_loss_pct: float = 0.01  # 1% стоп-лосс по умолчанию
    take_profit_pct: float = 0.02  # 2% тейк-профит по умолчанию


@dataclass
class RiskMetrics:
    """Метрики риска"""
    current_drawdown: float
    daily_pnl: float
    portfolio_value: float
    max_position_value: float
    correlation_risk: float
    leverage_used: float
    risk_score: float  # 0-100


class RiskEngine(ABC):
    """Абстрактный контракт для управления рисками"""
    
    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.daily_pnl = 0.0
        self.peak_value = 0.0
        self.positions_history: List[Position] = []
    
    @abstractmethod
    async def check_order_risk(
        self, 
        order: Order, 
        current_positions: List[Position],
        portfolio_value: float
    ) -> tuple[bool, str, RiskLevel]:
        """
        Проверка риска ордера
        
        Args:
            order: Ордер для проверки
            current_positions: Текущие позиции
            portfolio_value: Стоимость портфеля
            
        Returns:
            tuple[bool, str, RiskLevel]: (разрешен, причина, уровень риска)
        """
        pass
    
    @abstractmethod
    async def calculate_position_size(
        self,
        symbol: str,
        side: OrderSide,
        current_price: float,
        stop_loss: Optional[float] = None,
        portfolio_value: float = 0.0,
        volatility: Optional[float] = None
    ) -> float:
        """
        Расчет размера позиции
        
        Args:
            symbol: Торговый символ
            side: Сторона позиции
            current_price: Текущая цена
            stop_loss: Стоп-лосс
            portfolio_value: Стоимость портфеля
            volatility: Волатильность (опционально)
            
        Returns:
            float: Рекомендуемый размер позиции
        """
        pass
    
    @abstractmethod
    async def calculate_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        side: OrderSide,
        volatility: Optional[float] = None
    ) -> float:
        """
        Расчет стоп-лосса
        
        Args:
            symbol: Торговый символ
            entry_price: Цена входа
            side: Сторона позиции
            volatility: Волатильность (опционально)
            
        Returns:
            float: Рекомендуемый стоп-лосс
        """
        pass
    
    @abstractmethod
    async def calculate_take_profit(
        self,
        symbol: str,
        entry_price: float,
        side: OrderSide,
        stop_loss: float,
        risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Расчет тейк-профита
        
        Args:
            symbol: Торговый символ
            entry_price: Цена входа
            side: Сторона позиции
            stop_loss: Стоп-лосс
            risk_reward_ratio: Соотношение риск/доходность
            
        Returns:
            float: Рекомендуемый тейк-профит
        """
        pass
    
    @abstractmethod
    async def get_risk_metrics(
        self,
        current_positions: List[Position],
        portfolio_value: float
    ) -> RiskMetrics:
        """
        Получение метрик риска
        
        Args:
            current_positions: Текущие позиции
            portfolio_value: Стоимость портфеля
            
        Returns:
            RiskMetrics: Метрики риска
        """
        pass
    
    @abstractmethod
    async def check_daily_limits(self, portfolio_value: float) -> tuple[bool, str]:
        """
        Проверка дневных лимитов
        
        Args:
            portfolio_value: Стоимость портфеля
            
        Returns:
            tuple[bool, str]: (в пределах лимитов, причина)
        """
        pass
    
    @abstractmethod
    async def update_daily_pnl(self, pnl: float):
        """
        Обновление дневного PnL
        
        Args:
            pnl: Изменение PnL
        """
        pass
    
    @abstractmethod
    async def reset_daily_limits(self):
        """Сброс дневных лимитов (вызывается в начале дня)"""
        pass
    
    async def calculate_volatility(
        self, 
        symbol: str, 
        prices: pd.Series, 
        period: int = 20
    ) -> float:
        """
        Расчет волатильности
        
        Args:
            symbol: Торговый символ
            prices: Цены
            period: Период для расчета
            
        Returns:
            float: Волатильность
        """
        if len(prices) < period:
            return 0.0
        
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(window=period).std().iloc[-1]
        return float(volatility) if not pd.isna(volatility) else 0.0
    
    async def calculate_correlation_risk(
        self, 
        positions: List[Position], 
        price_data: Dict[str, pd.Series]
    ) -> float:
        """
        Расчет корреляционного риска
        
        Args:
            positions: Позиции
            price_data: Данные цен по символам
            
        Returns:
            float: Максимальная корреляция между позициями
        """
        if len(positions) < 2:
            return 0.0
        
        # Упрощенный расчет корреляции
        # В реальной реализации нужно использовать исторические данные
        return 0.0


class RiskError(Exception):
    """Ошибка риск-менеджмента"""
    pass


class RiskLimitExceededError(RiskError):
    """Превышен лимит риска"""
    pass


class InsufficientRiskCapacityError(RiskError):
    """Недостаточно рискового капитала"""
    pass
