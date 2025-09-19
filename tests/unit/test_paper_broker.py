"""
Unit тесты для PaperBroker
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.execution.paper_broker import PaperBroker, PaperAccount
from src.contracts.broker import OrderSide, OrderType, OrderStatus
from src.data.adapters import create_test_data, InMemoryFeed


@pytest.mark.asyncio
class TestPaperBroker:
    """Тесты для PaperBroker"""
    
    async def test_paper_broker_creation(self):
        """Тест создания PaperBroker"""
        # Создаем тестовые данные
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        
        # Создаем брокера
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        assert broker.account.balance == 10000.0
        assert len(broker.account.positions) == 0
        assert len(broker.account.orders) == 0
        assert len(broker.account.executions) == 0
    
    async def test_paper_broker_connection(self):
        """Тест подключения PaperBroker"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed)
        
        # Подключаемся
        await broker.connect()
        assert await broker.is_connected()
        
        # Отключаемся
        await broker.disconnect()
        assert not await broker.is_connected()
    
    async def test_create_market_order(self):
        """Тест создания маркет-ордера"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        # Создаем маркет-ордер
        order_id = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            client_id="test_order_1"
        )
        
        assert order_id is not None
        assert order_id in broker.account.orders
        
        # Проверяем ордер
        order = broker.account.orders[order_id]
        assert order.symbol == "EURUSD"
        assert order.side == OrderSide.BUY
        assert order.type == OrderType.MARKET
        assert order.quantity == 0.01
        assert order.client_id == "test_order_1"
    
    async def test_create_limit_order(self):
        """Тест создания лимит-ордера"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        # Создаем лимит-ордер
        order_id = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.01,
            price=1.1000,
            client_id="test_order_2"
        )
        
        assert order_id is not None
        order = broker.account.orders[order_id]
        assert order.price == 1.1000
        assert order.type == OrderType.LIMIT
    
    async def test_order_execution(self):
        """Тест исполнения ордера"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        # Создаем маркет-ордер
        order_id = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            client_id="test_order_3"
        )
        
        # Ждем исполнения
        await asyncio.sleep(2)
        
        # Проверяем статус ордера
        order = await broker.get_order(order_id)
        assert order is not None
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 0.01
        assert order.average_price > 0
    
    async def test_position_creation(self):
        """Тест создания позиции"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        # Создаем и исполняем ордер
        order_id = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            client_id="test_order_4"
        )
        
        await asyncio.sleep(2)
        
        # Проверяем позицию
        positions = await broker.get_positions()
        assert len(positions) == 1
        
        position = positions[0]
        assert position.symbol == "EURUSD"
        assert position.quantity == 0.01
        assert position.average_price > 0
    
    async def test_balance_update(self):
        """Тест обновления баланса"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        initial_balance = broker.account.balance
        
        # Создаем и исполняем ордер
        order_id = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            client_id="test_order_5"
        )
        
        await asyncio.sleep(2)
        
        # Проверяем, что баланс изменился
        final_balance = broker.account.balance
        assert final_balance < initial_balance  # Деньги потрачены на покупку
    
    async def test_idempotency(self):
        """Тест идемпотентности ордеров"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        client_id = "test_idempotent_order"
        
        # Создаем первый ордер
        order_id_1 = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            client_id=client_id
        )
        
        # Создаем второй ордер с тем же client_id
        order_id_2 = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            client_id=client_id
        )
        
        # Должны получить тот же order_id
        assert order_id_1 == order_id_2
    
    async def test_cancel_order(self):
        """Тест отмены ордера"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        # Создаем лимит-ордер (не исполняется сразу)
        order_id = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.01,
            price=0.5,  # Очень низкая цена, не исполнится
            client_id="test_cancel_order"
        )
        
        # Отменяем ордер
        success = await broker.cancel_order(order_id)
        assert success
        
        # Проверяем статус
        order = await broker.get_order(order_id)
        assert order.status == OrderStatus.CANCELLED
    
    async def test_account_summary(self):
        """Тест сводки по счету"""
        test_data = create_test_data("EURUSD", days=1)
        data_feed = InMemoryFeed(test_data, "EURUSD")
        broker = PaperBroker(data_feed, initial_balance=10000.0)
        
        await broker.connect()
        
        # Создаем и исполняем ордер
        order_id = await broker.create_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            client_id="test_summary_order"
        )
        
        await asyncio.sleep(2)
        
        # Получаем сводку
        summary = broker.get_account_summary()
        
        assert 'balance' in summary
        assert 'total_value' in summary
        assert 'positions_count' in summary
        assert 'orders_count' in summary
        assert 'executions_count' in summary
        
        assert summary['positions_count'] == 1
        assert summary['orders_count'] == 1
        assert summary['executions_count'] == 1


@pytest.mark.asyncio
class TestPaperAccount:
    """Тесты для PaperAccount"""
    
    def test_paper_account_creation(self):
        """Тест создания PaperAccount"""
        account = PaperAccount(balance=5000.0)
        
        assert account.balance == 5000.0
        assert len(account.positions) == 0
        assert len(account.orders) == 0
        assert len(account.executions) == 0
        assert account.daily_pnl == 0.0
        assert account.total_pnl == 0.0
