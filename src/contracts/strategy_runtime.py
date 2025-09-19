"""
Контракт StrategyRuntime для жизненного цикла стратегий
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, AsyncIterator
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio

from .data_feed import Bar, Tick
from .broker import Order, Position, OrderSide, OrderType
from .portfolio_manager import PortfolioSnapshot


class StrategyStatus(Enum):
    """Статус стратегии"""
    INIT = "INIT"           # Инициализация
    WARMUP = "WARMUP"       # Прогрев (загрузка истории)
    RUN = "RUN"             # Работа (live торговля)
    PAUSE = "PAUSE"         # Пауза
    STOP = "STOP"           # Остановка
    ERROR = "ERROR"         # Ошибка


class SignalType(Enum):
    """Тип сигнала"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"


@dataclass
class Signal:
    """Торговый сигнал"""
    id: str
    symbol: str
    signal_type: SignalType
    strength: float  # 0.0 - 1.0
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    reason: Optional[str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StrategyConfig:
    """Конфигурация стратегии"""
    name: str
    symbols: List[str]
    timeframes: List[str]
    warmup_period: int = 100  # Количество баров для прогрева
    max_positions: int = 5
    risk_per_trade: float = 0.02  # 2% риска на сделку
    stop_loss_pct: float = 0.01  # 1% стоп-лосс
    take_profit_pct: float = 0.02  # 2% тейк-профит
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class StrategyRuntime(ABC):
    """Абстрактный контракт для рантайма стратегии"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.status = StrategyStatus.INIT
        self.start_time: Optional[datetime] = None
        self.last_update: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.performance_metrics: Dict[str, Any] = {}
        self.signal_handlers: List[Callable[[Signal], None]] = []
        self.status_handlers: List[Callable[[StrategyStatus], None]] = []
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Инициализация стратегии
        
        Returns:
            bool: True если инициализация успешна
        """
        pass
    
    @abstractmethod
    async def warmup(self, data: Dict[str, List[Bar]]) -> bool:
        """
        Прогрев стратегии историческими данными
        
        Args:
            data: Исторические данные по символам
            
        Returns:
            bool: True если прогрев успешен
        """
        pass
    
    @abstractmethod
    async def process_bar(self, bar: Bar) -> Optional[Signal]:
        """
        Обработка нового бара
        
        Args:
            bar: Новый бар
            
        Returns:
            Signal или None: Торговый сигнал или None
        """
        pass
    
    @abstractmethod
    async def process_tick(self, tick: Tick) -> Optional[Signal]:
        """
        Обработка нового тика
        
        Args:
            tick: Новый тик
            
        Returns:
            Signal или None: Торговый сигнал или None
        """
        pass
    
    @abstractmethod
    async def on_position_opened(self, position: Position):
        """
        Обработка открытия позиции
        
        Args:
            position: Открытая позиция
        """
        pass
    
    @abstractmethod
    async def on_position_closed(self, position: Position, pnl: float):
        """
        Обработка закрытия позиции
        
        Args:
            position: Закрытая позиция
            pnl: Реализованный PnL
        """
        pass
    
    @abstractmethod
    async def on_order_filled(self, order: Order):
        """
        Обработка исполнения ордера
        
        Args:
            order: Исполненный ордер
        """
        pass
    
    @abstractmethod
    async def on_error(self, error: Exception):
        """
        Обработка ошибки
        
        Args:
            error: Ошибка
        """
        pass
    
    @abstractmethod
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик производительности
        
        Returns:
            Dict[str, Any]: Метрики производительности
        """
        pass
    
    @abstractmethod
    async def pause(self):
        """Приостановка стратегии"""
        pass
    
    @abstractmethod
    async def resume(self):
        """Возобновление стратегии"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Остановка стратегии"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Очистка ресурсов"""
        pass
    
    def add_signal_handler(self, handler: Callable[[Signal], None]):
        """Добавление обработчика сигналов"""
        self.signal_handlers.append(handler)
    
    def add_status_handler(self, handler: Callable[[StrategyStatus], None]):
        """Добавление обработчика статуса"""
        self.status_handlers.append(handler)
    
    async def emit_signal(self, signal: Signal):
        """Отправка сигнала всем обработчикам"""
        for handler in self.signal_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(signal)
                else:
                    handler(signal)
            except Exception as e:
                await self.on_error(e)
    
    async def set_status(self, status: StrategyStatus, error_message: Optional[str] = None):
        """Установка статуса стратегии"""
        self.status = status
        self.last_update = datetime.utcnow()
        if error_message:
            self.error_message = error_message
        
        # Уведомляем обработчики
        for handler in self.status_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(status)
                else:
                    handler(status)
            except Exception as e:
                await self.on_error(e)
    
    def is_running(self) -> bool:
        """Проверка, работает ли стратегия"""
        return self.status == StrategyStatus.RUN
    
    def is_paused(self) -> bool:
        """Проверка, приостановлена ли стратегия"""
        return self.status == StrategyStatus.PAUSE
    
    def is_stopped(self) -> bool:
        """Проверка, остановлена ли стратегия"""
        return self.status in [StrategyStatus.STOP, StrategyStatus.ERROR]
    
    def get_uptime(self) -> Optional[float]:
        """Получение времени работы в секундах"""
        if self.start_time is None:
            return None
        return (datetime.utcnow() - self.start_time).total_seconds()


class StrategyError(Exception):
    """Ошибка стратегии"""
    pass


class StrategyInitializationError(StrategyError):
    """Ошибка инициализации стратегии"""
    pass


class StrategyRuntimeError(StrategyError):
    """Ошибка рантайма стратегии"""
    pass


class InvalidSignalError(StrategyError):
    """Невалидный сигнал"""
    pass
