"""
Модели данных для работы с базой данных
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .connection import db_manager


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStrength(Enum):
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RunStatus(Enum):
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Signal:
    """Модель торгового сигнала"""
    signal_id: str
    strategy_id: str
    model_id: Optional[str]
    symbol: str
    timeframe: str
    signal_type: SignalType
    strength: SignalStrength
    price: float
    confidence: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    status: str = "pending"
    
    def __post_init__(self):
        if self.signal_id is None:
            self.signal_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    async def create(cls, **kwargs) -> 'Signal':
        """Создание нового сигнала"""
        signal = cls(**kwargs)
        await signal.save()
        return signal
    
    async def save(self):
        """Сохранение сигнала в БД"""
        query = """
        INSERT OR REPLACE INTO signals 
        (signal_id, strategy_id, model_id, symbol, timeframe, signal_type, strength, 
         price, confidence, stop_loss, take_profit, metadata, created_at, processed_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            self.signal_id,
            self.strategy_id,
            self.model_id,
            self.symbol,
            self.timeframe,
            self.signal_type.value,
            self.strength.value,
            self.price,
            self.confidence,
            self.stop_loss,
            self.take_profit,
            json.dumps(self.metadata),
            self.created_at,
            self.processed_at,
            self.status
        )
        
        await db_manager.execute(query, params)
        await db_manager.commit()
    
    @classmethod
    async def get_by_id(cls, signal_id: str) -> Optional['Signal']:
        """Получение сигнала по ID"""
        query = "SELECT * FROM signals WHERE signal_id = ?"
        row = await db_manager.execute_one(query, (signal_id,))
        
        if row:
            return cls._from_row(row)
        return None
    
    @classmethod
    async def get_by_strategy(cls, strategy_id: str, limit: int = 100) -> List['Signal']:
        """Получение сигналов по стратегии"""
        query = """
        SELECT * FROM signals 
        WHERE strategy_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
        """
        rows = await db_manager.execute(query, (strategy_id, limit))
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def _from_row(cls, row) -> 'Signal':
        """Создание объекта из строки БД"""
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return cls(
            signal_id=row['signal_id'],
            strategy_id=row['strategy_id'],
            model_id=row['model_id'],
            symbol=row['symbol'],
            timeframe=row['timeframe'],
            signal_type=SignalType(row['signal_type']),
            strength=SignalStrength(row['strength']),
            price=row['price'],
            confidence=row['confidence'],
            stop_loss=row['stop_loss'],
            take_profit=row['take_profit'],
            metadata=metadata,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            processed_at=datetime.fromisoformat(row['processed_at']) if row['processed_at'] else None,
            status=row['status']
        )


@dataclass
class Position:
    """Модель торговой позиции"""
    position_id: str
    signal_id: Optional[str]
    strategy_id: str
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    status: str = "open"
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.position_id is None:
            self.position_id = str(uuid.uuid4())
        if self.opened_at is None:
            self.opened_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    async def create(cls, **kwargs) -> 'Position':
        """Создание новой позиции"""
        position = cls(**kwargs)
        await position.save()
        return position
    
    async def save(self):
        """Сохранение позиции в БД"""
        query = """
        INSERT OR REPLACE INTO positions 
        (position_id, signal_id, strategy_id, symbol, side, size, entry_price, 
         current_price, stop_loss, take_profit, unrealized_pnl, realized_pnl, 
         status, opened_at, closed_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            self.position_id,
            self.signal_id,
            self.strategy_id,
            self.symbol,
            self.side.value,
            self.size,
            self.entry_price,
            self.current_price,
            self.stop_loss,
            self.take_profit,
            self.unrealized_pnl,
            self.realized_pnl,
            self.status,
            self.opened_at,
            self.closed_at,
            json.dumps(self.metadata)
        )
        
        await db_manager.execute(query, params)
        await db_manager.commit()
    
    async def update_pnl(self, current_price: float):
        """Обновление PnL позиции"""
        self.current_price = current_price
        
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size
        
        await self.save()
    
    @classmethod
    async def get_open_positions(cls, strategy_id: Optional[str] = None) -> List['Position']:
        """Получение открытых позиций"""
        if strategy_id:
            query = "SELECT * FROM positions WHERE status = 'open' AND strategy_id = ?"
            params = (strategy_id,)
        else:
            query = "SELECT * FROM positions WHERE status = 'open'"
            params = ()
        
        rows = await db_manager.execute(query, params)
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def _from_row(cls, row) -> 'Position':
        """Создание объекта из строки БД"""
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return cls(
            position_id=row['position_id'],
            signal_id=row['signal_id'],
            strategy_id=row['strategy_id'],
            symbol=row['symbol'],
            side=PositionSide(row['side']),
            size=row['size'],
            entry_price=row['entry_price'],
            current_price=row['current_price'],
            stop_loss=row['stop_loss'],
            take_profit=row['take_profit'],
            unrealized_pnl=row['unrealized_pnl'],
            realized_pnl=row['realized_pnl'],
            status=row['status'],
            opened_at=datetime.fromisoformat(row['opened_at']) if row['opened_at'] else None,
            closed_at=datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None,
            metadata=metadata
        )


@dataclass
class Order:
    """Модель торгового ордера"""
    order_id: str
    position_id: Optional[str]
    signal_id: Optional[str]
    symbol: str
    side: str
    type: OrderType
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_size: float = 0.0
    filled_price: Optional[float] = None
    commission: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    error_message: Optional[str] = None
    external_order_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.order_id is None:
            self.order_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    async def create(cls, **kwargs) -> 'Order':
        """Создание нового ордера"""
        order = cls(**kwargs)
        await order.save()
        return order
    
    async def save(self):
        """Сохранение ордера в БД"""
        self.updated_at = datetime.now()
        
        query = """
        INSERT OR REPLACE INTO orders 
        (order_id, position_id, signal_id, symbol, side, type, size, price, 
         stop_price, status, filled_size, filled_price, commission, created_at, 
         updated_at, filled_at, cancelled_at, error_message, external_order_id, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            self.order_id,
            self.position_id,
            self.signal_id,
            self.symbol,
            self.side,
            self.type.value,
            self.size,
            self.price,
            self.stop_price,
            self.status.value,
            self.filled_size,
            self.filled_price,
            self.commission,
            self.created_at,
            self.updated_at,
            self.filled_at,
            self.cancelled_at,
            self.error_message,
            self.external_order_id,
            json.dumps(self.metadata)
        )
        
        await db_manager.execute(query, params)
        await db_manager.commit()
    
    @classmethod
    def _from_row(cls, row) -> 'Order':
        """Создание объекта из строки БД"""
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return cls(
            order_id=row['order_id'],
            position_id=row['position_id'],
            signal_id=row['signal_id'],
            symbol=row['symbol'],
            side=row['side'],
            type=OrderType(row['type']),
            size=row['size'],
            price=row['price'],
            stop_price=row['stop_price'],
            status=OrderStatus(row['status']),
            filled_size=row['filled_size'],
            filled_price=row['filled_price'],
            commission=row['commission'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            filled_at=datetime.fromisoformat(row['filled_at']) if row['filled_at'] else None,
            cancelled_at=datetime.fromisoformat(row['cancelled_at']) if row['cancelled_at'] else None,
            error_message=row['error_message'],
            external_order_id=row['external_order_id'],
            metadata=metadata
        )


@dataclass
class Run:
    """Модель запуска оркестрации"""
    run_id: str
    strategy_id: str
    model_id: Optional[str]
    stage: str
    status: RunStatus
    progress: float = 0.0
    eta_minutes: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    logs_uri: Optional[str] = None
    metrics_partial: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    parent_run_id: Optional[str] = None
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.run_id is None:
            self.run_id = str(uuid.uuid4())
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.metrics_partial is None:
            self.metrics_partial = {}
    
    @classmethod
    async def create(cls, **kwargs) -> 'Run':
        """Создание нового запуска"""
        run = cls(**kwargs)
        await run.save()
        return run
    
    async def save(self):
        """Сохранение запуска в БД"""
        query = """
        INSERT OR REPLACE INTO runs 
        (run_id, strategy_id, model_id, stage, status, progress, eta_minutes, 
         started_at, ended_at, logs_uri, metrics_partial, error_message, 
         created_by, parent_run_id, priority, retry_count, max_retries)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            self.run_id,
            self.strategy_id,
            self.model_id,
            self.stage,
            self.status.value,
            self.progress,
            self.eta_minutes,
            self.started_at,
            self.ended_at,
            self.logs_uri,
            json.dumps(self.metrics_partial),
            self.error_message,
            self.created_by,
            self.parent_run_id,
            self.priority,
            self.retry_count,
            self.max_retries
        )
        
        await db_manager.execute(query, params)
        await db_manager.commit()
    
    @classmethod
    def _from_row(cls, row) -> 'Run':
        """Создание объекта из строки БД"""
        metrics_partial = json.loads(row['metrics_partial']) if row['metrics_partial'] else {}
        
        return cls(
            run_id=row['run_id'],
            strategy_id=row['strategy_id'],
            model_id=row['model_id'],
            stage=row['stage'],
            status=RunStatus(row['status']),
            progress=row['progress'],
            eta_minutes=row['eta_minutes'],
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
            logs_uri=row['logs_uri'],
            metrics_partial=metrics_partial,
            error_message=row['error_message'],
            created_by=row['created_by'],
            parent_run_id=row['parent_run_id'],
            priority=row['priority'],
            retry_count=row['retry_count'],
            max_retries=row['max_retries']
        )
