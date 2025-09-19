"""
Чистый API v2 сервер с lifespan для инициализации БД
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import os
import logging
import inspect

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
from ...database.clean_connection import clean_db_manager
from ...execution.paper_broker import PaperBroker
from ...contracts.data_feed import DataFeed
from ...contracts.broker import OrderSide, OrderType

# Настройка логирования для build info
log = logging.getLogger(__name__)


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


class SignalCreateRequest(BaseModel):
    run_id: str = Field(..., description="ID запуска")
    symbol: str = Field(..., description="Символ")
    side: str = Field(..., description="Сторона: BUY, SELL, HOLD, CLOSE")
    strength: float = Field(..., ge=0, le=1, description="Сила сигнала 0-1")
    price: float = Field(..., description="Цена")
    stop_loss: Optional[float] = Field(None, description="Стоп-лосс")
    take_profit: Optional[float] = Field(None, description="Тейк-профит")
    quantity: Optional[float] = Field(None, description="Количество")
    reason: Optional[str] = Field(None, description="Причина сигнала")
    params: Dict[str, Any] = Field(default_factory=dict, description="Параметры")


class SignalResponse(BaseModel):
    id: str
    run_id: str
    symbol: str
    side: str
    strength: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    reason: Optional[str] = None
    processed: bool
    created_at: datetime


class OrderCreateRequest(BaseModel):
    run_id: str = Field(..., description="ID запуска")
    client_id: str = Field(..., description="Клиентский ID")
    symbol: str = Field(..., description="Символ")
    side: str = Field(..., description="Сторона: BUY, SELL")
    type: str = Field(..., description="Тип: MARKET, LIMIT, STOP, STOP_LIMIT")
    quantity: float = Field(..., description="Количество")
    price: Optional[float] = Field(None, description="Цена")
    stop_price: Optional[float] = Field(None, description="Стоп-цена")
    time_in_force: str = Field("GTC", description="Время действия")
    params: Dict[str, Any] = Field(default_factory=dict, description="Параметры")


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
    time_in_force: str
    status: str
    created_at: datetime
    updated_at: datetime


class PositionResponse(BaseModel):
    id: str
    run_id: str
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float
    created_at: datetime
    updated_at: datetime


class ExecutionResponse(BaseModel):
    id: str
    order_id: str
    run_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    timestamp: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan для инициализации и очистки ресурсов"""
    # Инициализация при запуске
    logger.info("🚀 Инициализация API v2 сервера...")
    
    # Логирование build info для верификации
    logger.info(f"📦 Module file: {__file__}")
    logger.info(f"🚀 API build: {os.getenv('BUILD_SHA', 'unknown')}")
    
    # Подключаемся к базе данных
    if not await clean_db_manager.connect():
        raise ConnectionError("Не удалось подключиться к базе данных")
    
    logger.info("✅ Подключение к базе данных установлено")
    logger.info("🌐 API v2 сервер готов к работе")
    
    yield
    
    # Очистка при остановке
    logger.info("🛑 Остановка API v2 сервера...")
    await clean_db_manager.disconnect()
    logger.info("🔌 Отключение от базы данных завершено")


# Создаем FastAPI приложение с lifespan
app = FastAPI(
    title="Trading AI Agent API v2",
    description="Минимальный API для торгового AI-агента",
    version="2.0.0",
    docs_url="/docs" if config.get('api.docs_enabled', True) else None,
    redoc_url="/redoc" if config.get('api.docs_enabled', True) else None,
    lifespan=lifespan
)

# Настройка middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('api.cors.allow_origins', ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=config.get('api.trusted_hosts', ["*"])
)

# Глобальные переменные для компонентов
paper_broker: Optional[PaperBroker] = None
data_feed: Optional[DataFeed] = None
active_runs: Dict[str, Dict[str, Any]] = {}


# ==============================================
# ЭНДПОИНТЫ
# ==============================================

@app.get("/healthz")
async def healthz():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/status")
async def get_status():
    """Получить статус системы"""
    return {
        "status": "running",
        "active_runs": len(active_runs),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/runs", response_model=RunResponse)
async def create_run(request: RunCreateRequest):
    """Создать новый запуск стратегии"""
    run_id = str(uuid.uuid4())
    
    # Создаем запись в БД
    # TODO: Реализовать сохранение в БД
    
    active_runs[run_id] = {
        "strategy_name": request.strategy_name,
        "mode": request.mode,
        "status": "init",
        "started_at": datetime.utcnow(),
        "config": request.config,
        "note": request.note
    }
    
    return RunResponse(
        run_id=run_id,
        strategy_name=request.strategy_name,
        mode=request.mode,
        status="init",
        started_at=datetime.utcnow(),
        note=request.note
    )


@app.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str):
    """Получить статус запуска"""
    if run_id not in active_runs:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_data = active_runs[run_id]
    return RunStatusResponse(
        run_id=run_id,
        status=run_data["status"],
        started_at=run_data["started_at"],
        finished_at=run_data.get("finished_at"),
        note=run_data.get("note"),
        metrics=run_data.get("metrics", {})
    )


@app.post("/signals", response_model=SignalResponse)
async def create_signal(request: SignalCreateRequest):
    """Создать торговый сигнал"""
    signal_id = str(uuid.uuid4())
    
    # TODO: Реализовать сохранение в БД
    
    return SignalResponse(
        id=signal_id,
        run_id=request.run_id,
        symbol=request.symbol,
        side=request.side,
        strength=request.strength,
        price=request.price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        quantity=request.quantity,
        reason=request.reason,
        processed=False,
        created_at=datetime.utcnow()
    )


@app.get("/signals")
async def get_signals(run_id: Optional[str] = None, limit: int = 100):
    """Получить список сигналов"""
    # TODO: Реализовать получение из БД
    return {"signals": [], "total": 0}


@app.post("/orders", response_model=OrderResponse)
async def create_order(request: OrderCreateRequest):
    """Создать торговый ордер"""
    order_id = str(uuid.uuid4())
    
    # TODO: Реализовать создание ордера через broker
    
    return OrderResponse(
        id=order_id,
        run_id=request.run_id,
        client_id=request.client_id,
        symbol=request.symbol,
        side=request.side,
        type=request.type,
        quantity=request.quantity,
        price=request.price,
        stop_price=request.stop_price,
        time_in_force=request.time_in_force,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@app.get("/orders")
async def get_orders(run_id: Optional[str] = None, limit: int = 100):
    """Получить список ордеров"""
    # TODO: Реализовать получение из БД
    return {"orders": [], "total": 0}


@app.get("/positions")
async def get_positions(run_id: Optional[str] = None):
    """Получить позиции"""
    # TODO: Реализовать получение из БД
    return {"positions": [], "total": 0}


@app.post("/webhooks/execution")
async def webhook_execution(request: Request):
    """Webhook для получения уведомлений об исполнении"""
    # TODO: Реализовать обработку webhook
    return {"status": "received", "timestamp": datetime.utcnow().isoformat()}
