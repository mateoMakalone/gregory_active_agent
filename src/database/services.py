"""
Сервисы для работы с базой данных
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger

from .models import Signal, Position, Order, Run, SignalType, SignalStrength, PositionSide, OrderType, OrderStatus, RunStatus
from .connection import db_manager


class SignalService:
    """Сервис для работы с торговыми сигналами"""
    
    @staticmethod
    async def create_signal(
        strategy_id: str,
        symbol: str,
        timeframe: str,
        signal_type: SignalType,
        strength: SignalStrength,
        price: float,
        confidence: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None
    ) -> Signal:
        """Создание нового торгового сигнала"""
        signal = await Signal.create(
            strategy_id=strategy_id,
            model_id=model_id,
            symbol=symbol,
            timeframe=timeframe,
            signal_type=signal_type,
            strength=strength,
            price=price,
            confidence=confidence,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata or {}
        )
        
        logger.info(f"Создан сигнал: {signal.signal_id} {signal.symbol} {signal.signal_type.value}")
        return signal
    
    @staticmethod
    async def get_recent_signals(strategy_id: str, hours: int = 24) -> List[Signal]:
        """Получение недавних сигналов"""
        query = """
        SELECT * FROM signals 
        WHERE strategy_id = ? 
        AND created_at >= datetime('now', '-{} hours')
        ORDER BY created_at DESC
        """.format(hours)
        
        rows = await db_manager.execute(query, (strategy_id,))
        return [Signal._from_row(row) for row in rows]
    
    @staticmethod
    async def get_pending_signals() -> List[Signal]:
        """Получение необработанных сигналов"""
        query = "SELECT * FROM signals WHERE status = 'pending' ORDER BY created_at ASC"
        rows = await db_manager.execute(query)
        return [Signal._from_row(row) for row in rows]
    
    @staticmethod
    async def mark_signal_processed(signal_id: str):
        """Отметка сигнала как обработанного"""
        query = """
        UPDATE signals 
        SET status = 'processed', processed_at = ? 
        WHERE signal_id = ?
        """
        await db_manager.execute(query, (datetime.now(), signal_id))
        await db_manager.commit()
    
    @staticmethod
    async def get_signal_stats(strategy_id: str, days: int = 30) -> Dict[str, Any]:
        """Получение статистики сигналов"""
        query = """
        SELECT 
            COUNT(*) as total_signals,
            COUNT(CASE WHEN signal_type = 'BUY' THEN 1 END) as buy_signals,
            COUNT(CASE WHEN signal_type = 'SELL' THEN 1 END) as sell_signals,
            AVG(confidence) as avg_confidence,
            COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed_signals
        FROM signals 
        WHERE strategy_id = ? 
        AND created_at >= datetime('now', '-{} days')
        """.format(days)
        
        row = await db_manager.execute_one(query, (strategy_id,))
        
        return {
            'total_signals': row['total_signals'] or 0,
            'buy_signals': row['buy_signals'] or 0,
            'sell_signals': row['sell_signals'] or 0,
            'avg_confidence': row['avg_confidence'] or 0.0,
            'processed_signals': row['processed_signals'] or 0
        }


class PositionService:
    """Сервис для работы с торговыми позициями"""
    
    @staticmethod
    async def create_position(
        strategy_id: str,
        symbol: str,
        side: PositionSide,
        size: float,
        entry_price: float,
        signal_id: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Position:
        """Создание новой торговой позиции"""
        position = await Position.create(
            strategy_id=strategy_id,
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata or {}
        )
        
        logger.info(f"Создана позиция: {position.position_id} {position.symbol} {position.side.value}")
        return position
    
    @staticmethod
    async def get_open_positions(strategy_id: Optional[str] = None) -> List[Position]:
        """Получение открытых позиций"""
        return await Position.get_open_positions(strategy_id)
    
    @staticmethod
    async def update_position_prices(symbol: str, current_price: float):
        """Обновление цен для всех открытых позиций по символу"""
        query = "SELECT * FROM positions WHERE symbol = ? AND status = 'open'"
        rows = await db_manager.execute(query, (symbol,))
        
        for row in rows:
            position = Position._from_row(row)
            await position.update_pnl(current_price)
    
    @staticmethod
    async def close_position(position_id: str, close_price: float, reason: str = "manual"):
        """Закрытие позиции"""
        position = await Position.get_by_id(position_id)
        if not position:
            raise ValueError(f"Позиция {position_id} не найдена")
        
        # Рассчитываем реализованный PnL
        if position.side == PositionSide.LONG:
            realized_pnl = (close_price - position.entry_price) * position.size
        else:
            realized_pnl = (position.entry_price - close_price) * position.size
        
        # Обновляем позицию
        position.status = "closed"
        position.closed_at = datetime.now()
        position.realized_pnl = realized_pnl
        position.unrealized_pnl = 0.0
        
        if 'close_reasons' not in position.metadata:
            position.metadata['close_reasons'] = []
        position.metadata['close_reasons'].append({
            'reason': reason,
            'price': close_price,
            'timestamp': datetime.now().isoformat()
        })
        
        await position.save()
        logger.info(f"Закрыта позиция: {position_id} по цене {close_price}, PnL: {realized_pnl:.2f}")
    
    @staticmethod
    async def get_position_stats(strategy_id: str, days: int = 30) -> Dict[str, Any]:
        """Получение статистики позиций"""
        query = """
        SELECT 
            COUNT(*) as total_positions,
            COUNT(CASE WHEN status = 'open' THEN 1 END) as open_positions,
            COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_positions,
            SUM(realized_pnl) as total_realized_pnl,
            AVG(realized_pnl) as avg_realized_pnl,
            COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as profitable_positions
        FROM positions 
        WHERE strategy_id = ? 
        AND opened_at >= datetime('now', '-{} days')
        """.format(days)
        
        row = await db_manager.execute_one(query, (strategy_id,))
        
        total_closed = row['closed_positions'] or 0
        profitable = row['profitable_positions'] or 0
        
        return {
            'total_positions': row['total_positions'] or 0,
            'open_positions': row['open_positions'] or 0,
            'closed_positions': total_closed,
            'total_realized_pnl': row['total_realized_pnl'] or 0.0,
            'avg_realized_pnl': row['avg_realized_pnl'] or 0.0,
            'win_rate': (profitable / total_closed * 100) if total_closed > 0 else 0.0
        }


class OrderService:
    """Сервис для работы с торговыми ордерами"""
    
    @staticmethod
    async def create_order(
        symbol: str,
        side: str,
        order_type: OrderType,
        size: float,
        position_id: Optional[str] = None,
        signal_id: Optional[str] = None,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Order:
        """Создание нового торгового ордера"""
        order = await Order.create(
            position_id=position_id,
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            type=order_type,
            size=size,
            price=price,
            stop_price=stop_price,
            metadata=metadata or {}
        )
        
        logger.info(f"Создан ордер: {order.order_id} {order.symbol} {order.side} {order.type.value}")
        return order
    
    @staticmethod
    async def get_pending_orders() -> List[Order]:
        """Получение ожидающих ордеров"""
        query = "SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at ASC"
        rows = await db_manager.execute(query)
        return [Order._from_row(row) for row in rows]
    
    @staticmethod
    async def fill_order(order_id: str, filled_size: float, filled_price: float, commission: float = 0.0):
        """Исполнение ордера"""
        query = """
        UPDATE orders 
        SET status = 'filled', filled_size = ?, filled_price = ?, 
            filled_at = ?, commission = ?
        WHERE order_id = ?
        """
        
        await db_manager.execute(query, (filled_size, filled_price, datetime.now(), commission, order_id))
        await db_manager.commit()
        
        logger.info(f"Исполнен ордер: {order_id} {filled_size} @ {filled_price}")
    
    @staticmethod
    async def cancel_order(order_id: str, reason: str = "manual"):
        """Отмена ордера"""
        query = """
        UPDATE orders 
        SET status = 'cancelled', cancelled_at = ?, error_message = ?
        WHERE order_id = ?
        """
        
        await db_manager.execute(query, (datetime.now(), reason, order_id))
        await db_manager.commit()
        
        logger.info(f"Отменен ордер: {order_id} - {reason}")


class RunService:
    """Сервис для работы с запусками оркестрации"""
    
    @staticmethod
    async def create_run(
        strategy_id: str,
        stage: str,
        model_id: Optional[str] = None,
        created_by: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        priority: int = 0
    ) -> Run:
        """Создание нового запуска"""
        run = await Run.create(
            strategy_id=strategy_id,
            model_id=model_id,
            stage=stage,
            status=RunStatus.STARTED,
            created_by=created_by,
            parent_run_id=parent_run_id,
            priority=priority
        )
        
        logger.info(f"Создан запуск: {run.run_id} {strategy_id} {stage}")
        return run
    
    @staticmethod
    async def update_run_progress(run_id: str, progress: float, eta_minutes: Optional[int] = None):
        """Обновление прогресса запуска"""
        query = """
        UPDATE runs 
        SET progress = ?, eta_minutes = ?, status = 'running'
        WHERE run_id = ?
        """
        
        await db_manager.execute(query, (progress, eta_minutes, run_id))
        await db_manager.commit()
    
    @staticmethod
    async def complete_run(run_id: str, metrics: Optional[Dict[str, Any]] = None):
        """Завершение запуска"""
        query = """
        UPDATE runs 
        SET status = 'completed', progress = 100.0, ended_at = ?, metrics_partial = ?
        WHERE run_id = ?
        """
        
        metrics_json = json.dumps(metrics) if metrics else None
        await db_manager.execute(query, (datetime.now(), metrics_json, run_id))
        await db_manager.commit()
        
        logger.info(f"Завершен запуск: {run_id}")
    
    @staticmethod
    async def fail_run(run_id: str, error_message: str):
        """Отметка запуска как неудачного"""
        query = """
        UPDATE runs 
        SET status = 'failed', ended_at = ?, error_message = ?
        WHERE run_id = ?
        """
        
        await db_manager.execute(query, (datetime.now(), error_message, run_id))
        await db_manager.commit()
        
        logger.info(f"Неудачный запуск: {run_id} - {error_message}")
    
    @staticmethod
    async def get_active_runs() -> List[Run]:
        """Получение активных запусков"""
        query = """
        SELECT * FROM runs 
        WHERE status IN ('started', 'running') 
        ORDER BY priority DESC, started_at ASC
        """
        
        rows = await db_manager.execute(query)
        return [Run._from_row(row) for row in rows]


class MetricsService:
    """Сервис для работы с метриками"""
    
    @staticmethod
    async def record_live_metrics(
        strategy_id: str,
        sharpe_ratio: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        win_rate: Optional[float] = None,
        profit_factor: Optional[float] = None,
        latency_ms: Optional[int] = None,
        positions_count: Optional[int] = None,
        pnl_daily: Optional[float] = None,
        pnl_total: Optional[float] = None,
        data_staleness_minutes: Optional[int] = None,
        error_count: int = 0,
        success_rate: Optional[float] = None
    ):
        """Запись живых метрик"""
        query = """
        INSERT INTO live_metrics 
        (strategy_id, sharpe_ratio, max_drawdown, win_rate, profit_factor, 
         latency_ms, positions_count, pnl_daily, pnl_total, data_staleness_minutes, 
         error_count, success_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            strategy_id, sharpe_ratio, max_drawdown, win_rate, profit_factor,
            latency_ms, positions_count, pnl_daily, pnl_total, data_staleness_minutes,
            error_count, success_rate
        )
        
        await db_manager.execute(query, params)
        await db_manager.commit()
    
    @staticmethod
    async def get_latest_metrics(strategy_id: str) -> Optional[Dict[str, Any]]:
        """Получение последних метрик стратегии"""
        query = """
        SELECT * FROM live_metrics 
        WHERE strategy_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        
        row = await db_manager.execute_one(query, (strategy_id,))
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def get_metrics_history(strategy_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Получение истории метрик"""
        query = """
        SELECT * FROM live_metrics 
        WHERE strategy_id = ? 
        AND timestamp >= datetime('now', '-{} hours')
        ORDER BY timestamp ASC
        """.format(hours)
        
        rows = await db_manager.execute(query, (strategy_id,))
        return [dict(row) for row in rows]
