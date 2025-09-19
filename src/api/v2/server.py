"""
API v2 сервер с минимальным набором эндпоинтов
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

from ...core.config import config
from ...core.logger import setup_logging
from ...security.webhook_auth import require_webhook_auth, rate_limiter
from ...security.retry_policy import retry_manager
from ...database.connection import db_manager
from ...execution.paper_broker import PaperBroker
from ...contracts.data_feed import DataFeed
from ...contracts.broker import OrderSide, OrderType


# Pydantic модели
class RunCreateRequest(BaseModel):
    strategy_name: str = Field(..., description="Название стратегии")
    mode: str = Field(..., description="Режим: paper или live")
    config: Dict[str, Any] = Field(default_factory=dict, description="Конфигурация стратегии")
    note: Optional[str] = Field(None, description="Заметка")


class RunResponse(BaseModel):
    run_id: str
    strategy_name: str
    mode: str
    status: str
    started_at: datetime
    note: Optional[str] = None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    note: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class SignalResponse(BaseModel):
    id: str
    run_id: str
    timestamp: datetime
    symbol: str
    side: str
    strength: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    reason: Optional[str] = None
    processed: bool = False


class OrderResponse(BaseModel):
    id: str
    run_id: str
    client_id: str
    symbol: str
    side: str
    type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class PositionResponse(BaseModel):
    id: str
    run_id: str
    symbol: str
    quantity: float
    average_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    updated_at: datetime


class ExecutionWebhookRequest(BaseModel):
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float = 0.0
    timestamp: datetime


class APIServerV2:
    """API сервер v2"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Trading AI Agent API v2",
            description="Минимальный API для торгового AI-агента",
            version="2.0.0",
            docs_url="/docs" if config.get('api.docs_enabled', True) else None,
            redoc_url="/redoc" if config.get('api.docs_enabled', True) else None
        )
        
        self.setup_middleware()
        self.setup_routes()
        self.setup_security()
        
        # Инициализация компонентов
        self.paper_broker: Optional[PaperBroker] = None
        self.data_feed: Optional[DataFeed] = None
        self.active_runs: Dict[str, Dict[str, Any]] = {}
        
        logger.info("API v2 сервер инициализирован")
    
    def setup_middleware(self):
        """Настройка middleware"""
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get('api.cors.allow_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
        
        # Trusted Host
        trusted_hosts = config.get('api.trusted_hosts', ["*"])
        if trusted_hosts != ["*"]:
            self.app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=trusted_hosts
            )
        
        # Rate Limiting
        @self.app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            client_ip = request.client.host
            endpoint = request.url.path
            
            if not await rate_limiter.is_allowed(client_ip, endpoint):
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded", "retry_after": 60}
                )
            
            response = await call_next(request)
            return response
    
    def setup_routes(self):
        """Настройка маршрутов"""
        
        @self.app.get("/healthz")
        async def health_check():
            """Проверка здоровья (Kubernetes)"""
            return {"status": "healthy", "timestamp": datetime.utcnow()}
        
        @self.app.get("/readyz")
        async def readiness_check():
            """Проверка готовности (Kubernetes)"""
            if not await db_manager.is_connected():
                raise HTTPException(status_code=503, detail="Database not connected")
            
            return {"status": "ready", "timestamp": datetime.utcnow()}
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Получение метрик (Prometheus)"""
            try:
                # Базовые метрики
                metrics = {
                    "active_runs": len(self.active_runs),
                    "database_connected": await db_manager.is_connected(),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Метрики по запускам
                if self.active_runs:
                    running_runs = sum(1 for run in self.active_runs.values() if run['status'] == 'running')
                    metrics.update({
                        "running_runs": running_runs,
                        "paused_runs": len(self.active_runs) - running_runs
                    })
                
                return metrics
                
            except Exception as e:
                logger.error(f"Ошибка получения метрик: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/runs", response_model=RunResponse)
        async def create_run(request: RunCreateRequest, background_tasks: BackgroundTasks):
            """Создание запуска стратегии"""
            try:
                # Валидация режима
                if request.mode not in ['paper', 'live']:
                    raise HTTPException(status_code=400, detail="Mode must be 'paper' or 'live'")
                
                # Создаем run_id
                run_id = str(uuid.uuid4())
                
                # Сохраняем в БД
                query = """
                INSERT INTO runs (run_id, strategy_name, mode, status, note, config)
                VALUES ($1, $2, $3, $4, $5, $6)
                """
                
                await db_manager.execute(
                    query, 
                    (run_id, request.strategy_name, request.mode, 'init', request.note, request.config)
                )
                await db_manager.commit()
                
                # Добавляем в активные запуски
                self.active_runs[run_id] = {
                    'strategy_name': request.strategy_name,
                    'mode': request.mode,
                    'status': 'init',
                    'started_at': datetime.utcnow(),
                    'config': request.config
                }
                
                # Запускаем стратегию в фоне
                background_tasks.add_task(self._start_strategy, run_id)
                
                logger.info(f"Создан запуск {run_id}: {request.strategy_name} ({request.mode})")
                
                return RunResponse(
                    run_id=run_id,
                    strategy_name=request.strategy_name,
                    mode=request.mode,
                    status='init',
                    started_at=datetime.utcnow(),
                    note=request.note
                )
                
            except Exception as e:
                logger.error(f"Ошибка создания запуска: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/runs/{run_id}/stop")
        async def stop_run(run_id: str):
            """Остановка запуска"""
            try:
                if run_id not in self.active_runs:
                    raise HTTPException(status_code=404, detail="Run not found")
                
                # Обновляем статус в БД
                query = """
                UPDATE runs 
                SET status = 'stopped', finished_at = $1, updated_at = $1
                WHERE run_id = $2
                """
                
                await db_manager.execute(query, (datetime.utcnow(), run_id))
                await db_manager.commit()
                
                # Обновляем в памяти
                self.active_runs[run_id]['status'] = 'stopped'
                self.active_runs[run_id]['finished_at'] = datetime.utcnow()
                
                logger.info(f"Запуск {run_id} остановлен")
                
                return {"status": "success", "message": f"Run {run_id} stopped"}
                
            except Exception as e:
                logger.error(f"Ошибка остановки запуска {run_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/runs/{run_id}/status", response_model=RunStatusResponse)
        async def get_run_status(run_id: str):
            """Получение статуса запуска"""
            try:
                # Получаем из БД
                query = """
                SELECT run_id, status, started_at, finished_at, note
                FROM runs 
                WHERE run_id = $1
                """
                
                row = await db_manager.execute_one(query, (run_id,))
                
                if not row:
                    raise HTTPException(status_code=404, detail="Run not found")
                
                # Получаем метрики
                metrics_query = """
                SELECT name, value, timestamp
                FROM metrics 
                WHERE run_id = $1 
                ORDER BY timestamp DESC 
                LIMIT 10
                """
                
                metrics_rows = await db_manager.execute(metrics_query, (run_id,))
                metrics = {row['name']: row['value'] for row in metrics_rows}
                
                return RunStatusResponse(
                    run_id=row['run_id'],
                    status=row['status'],
                    started_at=row['started_at'],
                    finished_at=row['finished_at'],
                    note=row['note'],
                    metrics=metrics
                )
                
            except Exception as e:
                logger.error(f"Ошибка получения статуса запуска {run_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/runs/{run_id}/signals", response_model=List[SignalResponse])
        async def get_run_signals(run_id: str, limit: int = 100):
            """Получение сигналов запуска"""
            try:
                query = """
                SELECT id, run_id, timestamp, symbol, side, strength, price, 
                       stop_loss, take_profit, quantity, reason, processed
                FROM signals 
                WHERE run_id = $1 
                ORDER BY timestamp DESC 
                LIMIT $2
                """
                
                rows = await db_manager.execute(query, (run_id, limit))
                
                return [
                    SignalResponse(
                        id=row['id'],
                        run_id=row['run_id'],
                        timestamp=row['timestamp'],
                        symbol=row['symbol'],
                        side=row['side'],
                        strength=row['strength'],
                        price=row['price'],
                        stop_loss=row['stop_loss'],
                        take_profit=row['take_profit'],
                        quantity=row['quantity'],
                        reason=row['reason'],
                        processed=row['processed']
                    )
                    for row in rows
                ]
                
            except Exception as e:
                logger.error(f"Ошибка получения сигналов запуска {run_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/runs/{run_id}/orders", response_model=List[OrderResponse])
        async def get_run_orders(run_id: str, limit: int = 100):
            """Получение ордеров запуска"""
            try:
                query = """
                SELECT id, run_id, client_id, symbol, side, type, quantity, price, 
                       stop_price, status, filled_quantity, average_price, created_at, updated_at
                FROM orders 
                WHERE run_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
                """
                
                rows = await db_manager.execute(query, (run_id, limit))
                
                return [
                    OrderResponse(
                        id=row['id'],
                        run_id=row['run_id'],
                        client_id=row['client_id'],
                        symbol=row['symbol'],
                        side=row['side'],
                        type=row['type'],
                        quantity=row['quantity'],
                        price=row['price'],
                        stop_price=row['stop_price'],
                        status=row['status'],
                        filled_quantity=row['filled_quantity'],
                        average_price=row['average_price'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    for row in rows
                ]
                
            except Exception as e:
                logger.error(f"Ошибка получения ордеров запуска {run_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/runs/{run_id}/positions", response_model=List[PositionResponse])
        async def get_run_positions(run_id: str):
            """Получение позиций запуска"""
            try:
                query = """
                SELECT id, run_id, symbol, quantity, average_price, 
                       unrealized_pnl, realized_pnl, updated_at
                FROM positions 
                WHERE run_id = $1 AND quantity != 0
                ORDER BY updated_at DESC
                """
                
                rows = await db_manager.execute(query, (run_id,))
                
                return [
                    PositionResponse(
                        id=row['id'],
                        run_id=row['run_id'],
                        symbol=row['symbol'],
                        quantity=row['quantity'],
                        average_price=row['average_price'],
                        unrealized_pnl=row['unrealized_pnl'],
                        realized_pnl=row['realized_pnl'],
                        updated_at=row['updated_at']
                    )
                    for row in rows
                ]
                
            except Exception as e:
                logger.error(f"Ошибка получения позиций запуска {run_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/webhooks/execution")
        @require_webhook_auth
        async def execution_webhook(request: ExecutionWebhookRequest, payload: bytes, headers: dict, client_ip: str):
            """Веб-хук исполнения от брокера"""
            try:
                # Обрабатываем исполнение с retry и идемпотентностью
                result = await retry_manager.execute_with_retry(
                    func=self._process_execution,
                    execution_id=f"exec_{request.order_id}_{int(request.timestamp.timestamp())}",
                    params={
                        'order_id': request.order_id,
                        'symbol': request.symbol,
                        'side': request.side,
                        'quantity': request.quantity,
                        'price': request.price,
                        'fee': request.fee,
                        'timestamp': request.timestamp
                    },
                    idempotent=True
                )
                
                logger.info(f"Обработано исполнение ордера {request.order_id}")
                
                return {"status": "success", "result": result}
                
            except Exception as e:
                logger.error(f"Ошибка обработки исполнения: {e}")
                raise HTTPException(status_code=500, detail="Execution processing failed")
    
    def setup_security(self):
        """Настройка безопасности"""
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.detail, "status_code": exc.status_code}
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Необработанная ошибка: {exc}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "status_code": 500}
            )
    
    async def _start_strategy(self, run_id: str):
        """Запуск стратегии"""
        try:
            run_info = self.active_runs[run_id]
            
            # Обновляем статус на warmup
            await self._update_run_status(run_id, 'warmup')
            
            # Здесь должна быть логика запуска стратегии
            # Пока что просто имитируем работу
            await asyncio.sleep(2)
            
            # Обновляем статус на running
            await self._update_run_status(run_id, 'running')
            
            logger.info(f"Стратегия {run_id} запущена")
            
        except Exception as e:
            logger.error(f"Ошибка запуска стратегии {run_id}: {e}")
            await self._update_run_status(run_id, 'error', str(e))
    
    async def _update_run_status(self, run_id: str, status: str, error_message: Optional[str] = None):
        """Обновление статуса запуска"""
        query = """
        UPDATE runs 
        SET status = $1, updated_at = $2, finished_at = $3
        WHERE run_id = $4
        """
        
        finished_at = datetime.utcnow() if status in ['stopped', 'error'] else None
        
        await db_manager.execute(query, (status, datetime.utcnow(), finished_at, run_id))
        await db_manager.commit()
        
        # Обновляем в памяти
        if run_id in self.active_runs:
            self.active_runs[run_id]['status'] = status
            if finished_at:
                self.active_runs[run_id]['finished_at'] = finished_at
    
    async def _process_execution(
        self, 
        order_id: str, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: float, 
        fee: float, 
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Обработка исполнения ордера"""
        # Сохраняем исполнение в БД
        execution_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO executions (id, order_id, symbol, side, quantity, price, fee, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        await db_manager.execute(
            query, 
            (execution_id, order_id, symbol, side, quantity, price, fee, timestamp)
        )
        await db_manager.commit()
        
        return {
            "execution_id": execution_id,
            "order_id": order_id,
            "processed_at": datetime.utcnow().isoformat()
        }


# Глобальный экземпляр сервера
api_server_v2 = APIServerV2()
