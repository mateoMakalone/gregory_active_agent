"""
Unit тесты для контрактов
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.contracts.data_feed import Bar, Tick, DataFeedError
from src.contracts.broker import Order, Position, Execution, OrderSide, OrderType, OrderStatus
from src.contracts.risk_engine import RiskLimits, RiskLevel
from src.contracts.strategy_runtime import Signal, SignalType, StrategyConfig, StrategyStatus


class TestBar:
    """Тесты для структуры Bar"""
    
    def test_bar_creation(self):
        """Тест создания бара"""
        bar = Bar(
            timestamp=datetime.utcnow(),
            open=1.1000,
            high=1.1050,
            low=1.0950,
            close=1.1020,
            volume=1000.0,
            symbol="EURUSD",
            timeframe="1h"
        )
        
        assert bar.symbol == "EURUSD"
        assert bar.timeframe == "1h"
        assert bar.open == 1.1000
        assert bar.high == 1.1050
        assert bar.low == 1.0950
        assert bar.close == 1.1020
        assert bar.volume == 1000.0


class TestTick:
    """Тесты для структуры Tick"""
    
    def test_tick_creation(self):
        """Тест создания тика"""
        tick = Tick(
            timestamp=datetime.utcnow(),
            price=1.1020,
            volume=100.0,
            symbol="EURUSD",
            bid=1.1019,
            ask=1.1021
        )
        
        assert tick.symbol == "EURUSD"
        assert tick.price == 1.1020
        assert tick.volume == 100.0
        assert tick.bid == 1.1019
        assert tick.ask == 1.1021


class TestOrder:
    """Тесты для структуры Order"""
    
    def test_order_creation(self):
        """Тест создания ордера"""
        order = Order(
            id="test_order_1",
            client_id="client_1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=0.01
        )
        
        assert order.id == "test_order_1"
        assert order.client_id == "client_1"
        assert order.symbol == "EURUSD"
        assert order.side == OrderSide.BUY
        assert order.type == OrderType.MARKET
        assert order.quantity == 0.01
        assert order.status == OrderStatus.PENDING
        assert order.created_at is not None


class TestPosition:
    """Тесты для структуры Position"""
    
    def test_position_creation(self):
        """Тест создания позиции"""
        position = Position(
            symbol="EURUSD",
            quantity=0.01,
            average_price=1.1000
        )
        
        assert position.symbol == "EURUSD"
        assert position.quantity == 0.01
        assert position.average_price == 1.1000
        assert position.unrealized_pnl == 0.0
        assert position.realized_pnl == 0.0
        assert position.updated_at is not None


class TestExecution:
    """Тесты для структуры Execution"""
    
    def test_execution_creation(self):
        """Тест создания исполнения"""
        execution = Execution(
            id="exec_1",
            order_id="order_1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            price=1.1000,
            fee=0.11
        )
        
        assert execution.id == "exec_1"
        assert execution.order_id == "order_1"
        assert execution.symbol == "EURUSD"
        assert execution.side == OrderSide.BUY
        assert execution.quantity == 0.01
        assert execution.price == 1.1000
        assert execution.fee == 0.11
        assert execution.timestamp is not None


class TestSignal:
    """Тесты для структуры Signal"""
    
    def test_signal_creation(self):
        """Тест создания сигнала"""
        signal = Signal(
            id="signal_1",
            symbol="EURUSD",
            signal_type=SignalType.BUY,
            strength=0.75,
            price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            quantity=0.01,
            reason="Trend following signal"
        )
        
        assert signal.id == "signal_1"
        assert signal.symbol == "EURUSD"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == 0.75
        assert signal.price == 1.1000
        assert signal.stop_loss == 1.0950
        assert signal.take_profit == 1.1100
        assert signal.quantity == 0.01
        assert signal.reason == "Trend following signal"
        assert signal.timestamp is not None
        assert signal.metadata == {}


class TestStrategyConfig:
    """Тесты для конфигурации стратегии"""
    
    def test_strategy_config_creation(self):
        """Тест создания конфигурации стратегии"""
        config = StrategyConfig(
            name="test_strategy",
            symbols=["EURUSD", "GBPUSD"],
            timeframes=["1h", "4h"],
            warmup_period=100,
            max_positions=5,
            risk_per_trade=0.02,
            stop_loss_pct=0.01,
            take_profit_pct=0.02,
            parameters={"param1": "value1"}
        )
        
        assert config.name == "test_strategy"
        assert config.symbols == ["EURUSD", "GBPUSD"]
        assert config.timeframes == ["1h", "4h"]
        assert config.warmup_period == 100
        assert config.max_positions == 5
        assert config.risk_per_trade == 0.02
        assert config.stop_loss_pct == 0.01
        assert config.take_profit_pct == 0.02
        assert config.parameters == {"param1": "value1"}


class TestRiskLimits:
    """Тесты для лимитов риска"""
    
    def test_risk_limits_creation(self):
        """Тест создания лимитов риска"""
        limits = RiskLimits(
            max_daily_loss=0.02,
            max_position_size=0.1,
            max_correlation=0.7,
            max_drawdown=0.15,
            max_leverage=1.0,
            stop_loss_pct=0.01,
            take_profit_pct=0.02
        )
        
        assert limits.max_daily_loss == 0.02
        assert limits.max_position_size == 0.1
        assert limits.max_correlation == 0.7
        assert limits.max_drawdown == 0.15
        assert limits.max_leverage == 1.0
        assert limits.stop_loss_pct == 0.01
        assert limits.take_profit_pct == 0.02


class TestEnums:
    """Тесты для enum'ов"""
    
    def test_order_side_enum(self):
        """Тест enum OrderSide"""
        assert OrderSide.BUY.value == "BUY"
        assert OrderSide.SELL.value == "SELL"
    
    def test_order_type_enum(self):
        """Тест enum OrderType"""
        assert OrderType.MARKET.value == "MARKET"
        assert OrderType.LIMIT.value == "LIMIT"
        assert OrderType.STOP.value == "STOP"
        assert OrderType.STOP_LIMIT.value == "STOP_LIMIT"
    
    def test_order_status_enum(self):
        """Тест enum OrderStatus"""
        assert OrderStatus.PENDING.value == "PENDING"
        assert OrderStatus.FILLED.value == "FILLED"
        assert OrderStatus.CANCELLED.value == "CANCELLED"
    
    def test_signal_type_enum(self):
        """Тест enum SignalType"""
        assert SignalType.BUY.value == "BUY"
        assert SignalType.SELL.value == "SELL"
        assert SignalType.HOLD.value == "HOLD"
        assert SignalType.CLOSE.value == "CLOSE"
    
    def test_strategy_status_enum(self):
        """Тест enum StrategyStatus"""
        assert StrategyStatus.INIT.value == "INIT"
        assert StrategyStatus.RUN.value == "RUN"
        assert StrategyStatus.STOP.value == "STOP"
    
    def test_risk_level_enum(self):
        """Тест enum RiskLevel"""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


@pytest.mark.asyncio
class TestAsyncContracts:
    """Тесты для асинхронных контрактов"""
    
    async def test_data_feed_interface(self):
        """Тест интерфейса DataFeed"""
        # Создаем мок DataFeed
        class MockDataFeed:
            async def subscribe(self, ticker, timeframe):
                yield Bar(
                    timestamp=datetime.utcnow(),
                    open=1.1000,
                    high=1.1050,
                    low=1.0950,
                    close=1.1020,
                    volume=1000.0,
                    symbol=ticker,
                    timeframe=timeframe
                )
            
            async def history(self, ticker, timeframe, since=None, until=None, limit=None):
                import pandas as pd
                return pd.DataFrame({
                    'timestamp': [datetime.utcnow()],
                    'open': [1.1000],
                    'high': [1.1050],
                    'low': [1.0950],
                    'close': [1.1020],
                    'volume': [1000.0]
                })
            
            async def get_latest_price(self, ticker):
                return 1.1020
            
            async def is_connected(self):
                return True
            
            async def disconnect(self):
                pass
        
        feed = MockDataFeed()
        
        # Тестируем subscribe
        async for bar in feed.subscribe("EURUSD", "1h"):
            assert bar.symbol == "EURUSD"
            assert bar.timeframe == "1h"
            break
        
        # Тестируем history
        df = await feed.history("EURUSD", "1h")
        assert len(df) == 1
        assert df['symbol'].iloc[0] == "EURUSD"
        
        # Тестируем get_latest_price
        price = await feed.get_latest_price("EURUSD")
        assert price == 1.1020
        
        # Тестируем is_connected
        connected = await feed.is_connected()
        assert connected is True
