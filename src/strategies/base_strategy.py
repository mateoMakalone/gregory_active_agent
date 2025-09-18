"""
Базовый класс для торговых стратегий
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from datetime import datetime
from enum import Enum
from loguru import logger


class SignalType(Enum):
    """Типы торговых сигналов"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStrength(Enum):
    """Сила сигнала"""
    WEAK = 1
    MEDIUM = 2
    STRONG = 3


class TradingSignal:
    """Класс для хранения торгового сигнала"""
    
    def __init__(
        self,
        symbol: str,
        signal_type: SignalType,
        strength: SignalStrength,
        price: float,
        timestamp: datetime,
        timeframe: str,
        strategy_name: str,
        confidence: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict] = None
    ):
        self.symbol = symbol
        self.signal_type = signal_type
        self.strength = strength
        self.price = price
        self.timestamp = timestamp
        self.timeframe = timeframe
        self.strategy_name = strategy_name
        self.confidence = confidence
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.metadata = metadata or {}
    
    def __repr__(self):
        return (f"TradingSignal(symbol={self.symbol}, type={self.signal_type.value}, "
                f"strength={self.strength.name}, price={self.price:.4f}, "
                f"confidence={self.confidence:.2f})")
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для сериализации"""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': self.strength.name,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'timeframe': self.timeframe,
            'strategy_name': self.strategy_name,
            'confidence': self.confidence,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'metadata': self.metadata
        }


class BaseStrategy(ABC):
    """Базовый класс для торговых стратегий"""
    
    def __init__(self, name: str, config: Dict):
        """
        Инициализация стратегии
        
        Args:
            name: Название стратегии
            config: Конфигурация стратегии
        """
        self.name = name
        self.config = config
        self.is_active = True
        self.signals_history: List[TradingSignal] = []
        
        # Параметры стратегии
        self.min_confidence = config.get('min_confidence', 0.6)
        self.max_signals_per_day = config.get('max_signals_per_day', 10)
        self.cooldown_minutes = config.get('cooldown_minutes', 30)
        
        logger.info(f"Стратегия {self.name} инициализирована")
    
    @abstractmethod
    def analyze(self, data: Dict[str, pd.DataFrame]) -> Optional[TradingSignal]:
        """
        Анализ данных и генерация сигнала
        
        Args:
            data: Словарь с данными по таймфреймам {timeframe: DataFrame}
            
        Returns:
            TradingSignal или None если сигнал не сгенерирован
        """
        pass
    
    @abstractmethod
    def get_required_timeframes(self) -> List[str]:
        """
        Получение списка необходимых таймфреймов
        
        Returns:
            Список таймфреймов
        """
        pass
    
    def validate_signal(self, signal: TradingSignal) -> bool:
        """
        Валидация сигнала
        
        Args:
            signal: Сигнал для проверки
            
        Returns:
            True если сигнал валиден
        """
        # Проверка минимальной уверенности
        if signal.confidence < self.min_confidence:
            logger.debug(f"Сигнал отклонен: низкая уверенность {signal.confidence:.2f}")
            return False
        
        # Проверка лимита сигналов в день
        today = datetime.now().date()
        today_signals = [s for s in self.signals_history 
                        if s.timestamp.date() == today and s.symbol == signal.symbol]
        
        if len(today_signals) >= self.max_signals_per_day:
            logger.debug(f"Сигнал отклонен: превышен лимит сигналов в день для {signal.symbol}")
            return False
        
        # Проверка кулдауна
        if self.signals_history:
            last_signal = max(self.signals_history, key=lambda x: x.timestamp)
            time_diff = (signal.timestamp - last_signal.timestamp).total_seconds() / 60
            
            if time_diff < self.cooldown_minutes:
                logger.debug(f"Сигнал отклонен: кулдаун {self.cooldown_minutes} минут")
                return False
        
        return True
    
    def add_signal(self, signal: TradingSignal) -> bool:
        """
        Добавление сигнала в историю
        
        Args:
            signal: Сигнал для добавления
            
        Returns:
            True если сигнал добавлен
        """
        if self.validate_signal(signal):
            self.signals_history.append(signal)
            logger.info(f"Добавлен сигнал: {signal}")
            return True
        return False
    
    def get_signals(self, symbol: Optional[str] = None, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[TradingSignal]:
        """
        Получение сигналов с фильтрацией
        
        Args:
            symbol: Фильтр по символу
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список отфильтрованных сигналов
        """
        signals = self.signals_history.copy()
        
        if symbol:
            signals = [s for s in signals if s.symbol == symbol]
        
        if start_date:
            signals = [s for s in signals if s.timestamp >= start_date]
        
        if end_date:
            signals = [s for s in signals if s.timestamp <= end_date]
        
        return signals
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик производительности стратегии
        
        Returns:
            Словарь с метриками
        """
        if not self.signals_history:
            return {}
        
        total_signals = len(self.signals_history)
        buy_signals = len([s for s in self.signals_history if s.signal_type == SignalType.BUY])
        sell_signals = len([s for s in self.signals_history if s.signal_type == SignalType.SELL])
        
        avg_confidence = sum(s.confidence for s in self.signals_history) / total_signals
        
        # Группировка по символам
        symbols = set(s.symbol for s in self.signals_history)
        signals_by_symbol = {symbol: len([s for s in self.signals_history if s.symbol == symbol]) 
                           for symbol in symbols}
        
        return {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'avg_confidence': avg_confidence,
            'signals_by_symbol': signals_by_symbol,
            'strategy_name': self.name,
            'is_active': self.is_active
        }
    
    def activate(self):
        """Активация стратегии"""
        self.is_active = True
        logger.info(f"Стратегия {self.name} активирована")
    
    def deactivate(self):
        """Деактивация стратегии"""
        self.is_active = False
        logger.info(f"Стратегия {self.name} деактивирована")
    
    def reset(self):
        """Сброс истории сигналов"""
        self.signals_history.clear()
        logger.info(f"История сигналов стратегии {self.name} очищена")

