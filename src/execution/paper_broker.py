"""
Paper Broker - фейковый брокер для тестирования
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from loguru import logger

from ..contracts.broker import (
    Broker, Order, Position, Execution, OrderSide, OrderType, OrderStatus,
    BrokerError, OrderError, InsufficientFundsError, InvalidOrderError
)
from ..contracts.data_feed import DataFeed


@dataclass
class PaperAccount:
    """Бумажный счет"""
    balance: float = 100000.0  # Начальный баланс $100,000
    positions: Dict[str, Position] = field(default_factory=dict)
    orders: Dict[str, Order] = field(default_factory=dict)
    executions: List[Execution] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0


class PaperBroker(Broker):
    """Фейковый брокер для paper trading"""
    
    def __init__(self, data_feed: DataFeed, initial_balance: float = 100000.0):
        self.data_feed = data_feed
        self.account = PaperAccount(balance=initial_balance)
        self.connected = False
        self.order_counter = 0
        self.execution_counter = 0
        self.client_orders: Dict[str, str] = {}  # client_id -> order_id mapping
        
        # Настройки исполнения
        self.slippage = 0.0001  # 0.01% проскальзывание
        self.commission = 0.001  # 0.1% комиссия
        self.fill_delay = 0.1  # Задержка исполнения в секундах
        
        logger.info(f"Paper Broker инициализирован с балансом ${initial_balance:,.2f}")
    
    async def connect(self):
        """Подключение к брокеру"""
        if not await self.data_feed.is_connected():
            await self.data_feed.connect()
        
        self.connected = True
        logger.info("Paper Broker подключен")
    
    async def disconnect(self):
        """Отключение от брокера"""
        self.connected = False
        logger.info("Paper Broker отключен")
    
    async def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.connected and await self.data_feed.is_connected()
    
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
        """Создание ордера"""
        if not await self.is_connected():
            raise BrokerError("Broker не подключен")
        
        # Генерируем client_id если не предоставлен
        if client_id is None:
            client_id = str(uuid.uuid4())
        
        # Проверяем идемпотентность
        if client_id in self.client_orders:
            existing_order_id = self.client_orders[client_id]
            existing_order = self.account.orders.get(existing_order_id)
            if existing_order and existing_order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                logger.warning(f"Ордер с client_id {client_id} уже существует: {existing_order_id}")
                return existing_order_id
        
        # Валидация ордера
        await self._validate_order(symbol, side, order_type, quantity, price, stop_price)
        
        # Создаем ордер
        order_id = str(uuid.uuid4())
        order = Order(
            id=order_id,
            client_id=client_id,
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        # Сохраняем ордер
        self.account.orders[order_id] = order
        self.client_orders[client_id] = order_id
        
        logger.info(f"Создан ордер {order_id}: {side.value} {quantity} {symbol} @ {price or 'MARKET'}")
        
        # Асинхронно исполняем ордер
        asyncio.create_task(self._process_order(order_id))
        
        return order_id
    
    async def cancel_order(self, order_id: str) -> bool:
        """Отмена ордера"""
        if not await self.is_connected():
            raise BrokerError("Broker не подключен")
        
        order = self.account.orders.get(order_id)
        if not order:
            logger.warning(f"Ордер {order_id} не найден")
            return False
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            logger.warning(f"Ордер {order_id} уже {order.status.value}")
            return False
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        logger.info(f"Ордер {order_id} отменен")
        return True
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Получение ордера по ID"""
        return self.account.orders.get(order_id)
    
    async def get_orders(
        self, 
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100
    ) -> List[Order]:
        """Получение списка ордеров"""
        orders = list(self.account.orders.values())
        
        # Фильтрация
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        if status:
            orders = [o for o in orders if o.status == status]
        
        # Сортировка по времени создания (новые первые)
        orders.sort(key=lambda x: x.created_at, reverse=True)
        
        return orders[:limit]
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Получение позиций"""
        positions = list(self.account.positions.values())
        
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        return positions
    
    async def get_executions(
        self, 
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Execution]:
        """Получение исполнений"""
        executions = self.account.executions.copy()
        
        # Фильтрация
        if order_id:
            executions = [e for e in executions if e.order_id == order_id]
        if symbol:
            executions = [e for e in executions if e.symbol == symbol]
        
        # Сортировка по времени (новые первые)
        executions.sort(key=lambda x: x.timestamp, reverse=True)
        
        return executions[:limit]
    
    async def get_balance(self) -> Dict[str, float]:
        """Получение баланса"""
        return {"USD": self.account.balance}
    
    async def _validate_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float],
        stop_price: Optional[float]
    ):
        """Валидация ордера"""
        if quantity <= 0:
            raise InvalidOrderError("Количество должно быть положительным")
        
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and price is None:
            raise InvalidOrderError("Цена обязательна для лимитных ордеров")
        
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and stop_price is None:
            raise InvalidOrderError("Стоп-цена обязательна для стоп-ордеров")
        
        if price is not None and price <= 0:
            raise InvalidOrderError("Цена должна быть положительной")
        
        if stop_price is not None and stop_price <= 0:
            raise InvalidOrderError("Стоп-цена должна быть положительной")
        
        # Проверяем достаточность средств для маркет-ордеров
        if order_type == OrderType.MARKET:
            current_price = await self.data_feed.get_latest_price(symbol)
            required_margin = quantity * current_price
            
            if side == OrderSide.BUY and required_margin > self.account.balance:
                raise InsufficientFundsError(f"Недостаточно средств: требуется ${required_margin:,.2f}, доступно ${self.account.balance:,.2f}")
    
    async def _process_order(self, order_id: str):
        """Обработка ордера"""
        try:
            # Небольшая задержка для имитации реального исполнения
            await asyncio.sleep(self.fill_delay)
            
            order = self.account.orders[order_id]
            
            # Получаем текущую цену
            current_price = await self.data_feed.get_latest_price(order.symbol)
            
            # Определяем цену исполнения
            fill_price = await self._calculate_fill_price(order, current_price)
            
            if fill_price is None:
                # Ордер не может быть исполнен (например, лимитный ордер)
                order.status = OrderStatus.REJECTED
                order.error_message = "Ордер не может быть исполнен по текущей цене"
                order.updated_at = datetime.utcnow()
                return
            
            # Исполняем ордер
            await self._fill_order(order, fill_price)
            
        except Exception as e:
            logger.error(f"Ошибка обработки ордера {order_id}: {e}")
            if order_id in self.account.orders:
                self.account.orders[order_id].status = OrderStatus.REJECTED
                self.account.orders[order_id].error_message = str(e)
                self.account.orders[order_id].updated_at = datetime.utcnow()
    
    async def _calculate_fill_price(self, order: Order, current_price: float) -> Optional[float]:
        """Расчет цены исполнения"""
        if order.type == OrderType.MARKET:
            # Маркет-ордер исполняется по текущей цене с проскальзыванием
            slippage = current_price * self.slippage
            if order.side == OrderSide.BUY:
                return current_price + slippage
            else:
                return current_price - slippage
        
        elif order.type == OrderType.LIMIT:
            # Лимитный ордер исполняется только если цена достигнута
            if order.side == OrderSide.BUY and current_price <= order.price:
                return order.price
            elif order.side == OrderSide.SELL and current_price >= order.price:
                return order.price
            else:
                return None  # Не исполняется
        
        elif order.type == OrderType.STOP:
            # Стоп-ордер становится маркет-ордером при достижении стоп-цены
            if order.side == OrderSide.BUY and current_price >= order.stop_price:
                return current_price + (current_price * self.slippage)
            elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                return current_price - (current_price * self.slippage)
            else:
                return None  # Не исполняется
        
        elif order.type == OrderType.STOP_LIMIT:
            # Стоп-лимит ордер
            if order.side == OrderSide.BUY and current_price >= order.stop_price:
                if current_price <= order.price:
                    return order.price
                else:
                    return None  # Цена превысила лимит
            elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                if current_price >= order.price:
                    return order.price
                else:
                    return None  # Цена ниже лимита
            else:
                return None  # Стоп-цена не достигнута
        
        return None
    
    async def _fill_order(self, order: Order, fill_price: float):
        """Исполнение ордера"""
        # Рассчитываем комиссию
        commission = order.quantity * fill_price * self.commission
        
        # Обновляем баланс
        if order.side == OrderSide.BUY:
            cost = order.quantity * fill_price + commission
            if cost > self.account.balance:
                order.status = OrderStatus.REJECTED
                order.error_message = "Недостаточно средств для исполнения"
                return
            self.account.balance -= cost
        else:
            self.account.balance += order.quantity * fill_price - commission
        
        # Создаем исполнение
        execution_id = str(uuid.uuid4())
        execution = Execution(
            id=execution_id,
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            fee=commission,
            timestamp=datetime.utcnow()
        )
        
        self.account.executions.append(execution)
        
        # Обновляем ордер
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_price = fill_price
        order.updated_at = datetime.utcnow()
        
        # Обновляем позицию
        await self._update_position(order.symbol, order.side, order.quantity, fill_price)
        
        logger.info(f"Ордер {order.id} исполнен: {order.quantity} {order.symbol} @ {fill_price:.4f} (комиссия: {commission:.2f})")
    
    async def _update_position(self, symbol: str, side: OrderSide, quantity: float, price: float):
        """Обновление позиции"""
        if symbol not in self.account.positions:
            self.account.positions[symbol] = Position(
                symbol=symbol,
                quantity=0,
                average_price=0,
                updated_at=datetime.utcnow()
            )
        
        position = self.account.positions[symbol]
        
        # Рассчитываем новую позицию
        if side == OrderSide.BUY:
            new_quantity = position.quantity + quantity
        else:
            new_quantity = position.quantity - quantity
        
        # Рассчитываем новую среднюю цену
        if new_quantity == 0:
            position.quantity = 0
            position.average_price = 0
        elif (position.quantity > 0 and new_quantity > 0) or (position.quantity < 0 and new_quantity < 0):
            # Позиция в том же направлении
            position.average_price = (
                (position.quantity * position.average_price + quantity * price) / new_quantity
            )
        else:
            # Позиция изменила направление
            position.average_price = price
        
        position.quantity = new_quantity
        position.updated_at = datetime.utcnow()
        
        # Если позиция закрыта, удаляем её
        if position.quantity == 0:
            del self.account.positions[symbol]
    
    async def update_positions_pnl(self):
        """Обновление PnL позиций"""
        for symbol, position in self.account.positions.items():
            try:
                current_price = await self.data_feed.get_latest_price(symbol)
                
                if position.quantity > 0:
                    # Длинная позиция
                    position.unrealized_pnl = (current_price - position.average_price) * position.quantity
                else:
                    # Короткая позиция
                    position.unrealized_pnl = (position.average_price - current_price) * abs(position.quantity)
                
                position.updated_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Ошибка обновления PnL для {symbol}: {e}")
    
    def get_account_summary(self) -> Dict[str, any]:
        """Получение сводки по счету"""
        total_value = self.account.balance
        total_unrealized_pnl = 0
        
        for position in self.account.positions.values():
            total_unrealized_pnl += position.unrealized_pnl
        
        return {
            "balance": self.account.balance,
            "total_value": total_value + total_unrealized_pnl,
            "unrealized_pnl": total_unrealized_pnl,
            "realized_pnl": self.account.total_pnl,
            "positions_count": len(self.account.positions),
            "orders_count": len(self.account.orders),
            "executions_count": len(self.account.executions)
        }
