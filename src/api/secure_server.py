"""
Безопасный API сервер с веб-хуками
"""

import asyncio
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from ..core.config import config
from ..core.logger import setup_logging
from ..security.webhook_auth import require_webhook_auth, rate_limiter, webhook_authenticator
from ..security.retry_policy import retry_manager, circuit_breaker
from ..security.rate_limiter import rate_limit, backpressure_protection, backpressure_manager
from ..database.services import SignalService, PositionService, RunService, MetricsService
from ..database.models import SignalType, SignalStrength, PositionSide


class SecureAPIServer:
    """Безопасный API сервер"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Trading AI Agent API",
            description="Безопасный API для торгового AI-агента",
            version="1.0.0",
            docs_url="/docs" if config.get('api.docs_enabled', True) else None,
            redoc_url="/redoc" if config.get('api.docs_enabled', True) else None
        )
        
        self.setup_middleware()
        self.setup_routes()
        self.setup_security()
        
        logger.info("Безопасный API сервер инициализирован")
    
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
        
        # Backpressure Protection
        @self.app.middleware("http")
        async def backpressure_middleware(request: Request, call_next):
            if not await backpressure_manager.check_capacity():
                return JSONResponse(
                    status_code=503,
                    content={"error": "Service temporarily unavailable", "retry_after": 5}
                )
            
            response = await call_next(request)
            return response
    
    def setup_routes(self):
        """Настройка маршрутов"""
        
        @self.app.get("/health")
        async def health_check():
            """Проверка здоровья сервиса"""
            return {
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "queue_status": backpressure_manager.get_queue_status()
            }
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Получение метрик системы"""
            try:
                # Получаем метрики из БД
                latest_metrics = await MetricsService.get_latest_metrics("default")
                
                return {
                    "metrics": latest_metrics,
                    "queue_status": backpressure_manager.get_queue_status(),
                    "rate_limiter_status": {
                        "enabled": True,
                        "buckets_count": len(rate_limiter.buckets)
                    }
                }
            except Exception as e:
                logger.error(f"Ошибка получения метрик: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/webhook/n8n")
        @require_webhook_auth
        @rate_limit(requests_per_second=5.0)
        @backpressure_protection()
        async def n8n_webhook(request: Request, payload: bytes, headers: dict, client_ip: str):
            """Веб-хук для n8n"""
            try:
                data = json.loads(payload.decode('utf-8'))
                
                # Обрабатываем webhook с retry и идемпотентностью
                result = await retry_manager.execute_with_retry(
                    func=self._process_n8n_webhook,
                    execution_id=data.get('execution_id', 'unknown'),
                    params={'data': data, 'client_ip': client_ip},
                    idempotent=True
                )
                
                return {"status": "success", "result": result}
                
            except Exception as e:
                logger.error(f"Ошибка обработки n8n webhook: {e}")
                raise HTTPException(status_code=500, detail="Webhook processing failed")
        
        @self.app.post("/webhook/external")
        @require_webhook_auth
        @rate_limit(requests_per_second=2.0)
        @backpressure_protection()
        async def external_webhook(request: Request, payload: bytes, headers: dict, client_ip: str):
            """Внешний веб-хук"""
            try:
                data = json.loads(payload.decode('utf-8'))
                
                result = await retry_manager.execute_with_retry(
                    func=self._process_external_webhook,
                    execution_id=data.get('id', 'unknown'),
                    params={'data': data, 'client_ip': client_ip},
                    idempotent=True
                )
                
                return {"status": "success", "result": result}
                
            except Exception as e:
                logger.error(f"Ошибка обработки external webhook: {e}")
                raise HTTPException(status_code=500, detail="Webhook processing failed")
        
        @self.app.post("/signals")
        @rate_limit(requests_per_second=10.0)
        @backpressure_protection()
        async def create_signal(signal_data: dict):
            """Создание торгового сигнала"""
            try:
                signal = await SignalService.create_signal(
                    strategy_id=signal_data.get('strategy_id'),
                    symbol=signal_data.get('symbol'),
                    timeframe=signal_data.get('timeframe'),
                    signal_type=SignalType(signal_data.get('signal_type')),
                    strength=SignalStrength(signal_data.get('strength')),
                    price=signal_data.get('price'),
                    confidence=signal_data.get('confidence'),
                    stop_loss=signal_data.get('stop_loss'),
                    take_profit=signal_data.get('take_profit'),
                    metadata=signal_data.get('metadata', {})
                )
                
                return {"status": "success", "signal_id": signal.signal_id}
                
            except Exception as e:
                logger.error(f"Ошибка создания сигнала: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/signals")
        async def get_signals(strategy_id: Optional[str] = None, limit: int = 100):
            """Получение сигналов"""
            try:
                if strategy_id:
                    signals = await SignalService.get_recent_signals(strategy_id, hours=24)
                else:
                    signals = await SignalService.get_pending_signals()
                
                return {
                    "status": "success",
                    "signals": [signal.__dict__ for signal in signals[:limit]]
                }
                
            except Exception as e:
                logger.error(f"Ошибка получения сигналов: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/positions")
        async def get_positions(strategy_id: Optional[str] = None):
            """Получение позиций"""
            try:
                positions = await PositionService.get_open_positions(strategy_id)
                
                return {
                    "status": "success",
                    "positions": [position.__dict__ for position in positions]
                }
                
            except Exception as e:
                logger.error(f"Ошибка получения позиций: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/runs")
        @rate_limit(requests_per_second=5.0)
        async def create_run(run_data: dict):
            """Создание запуска оркестрации"""
            try:
                run = await RunService.create_run(
                    strategy_id=run_data.get('strategy_id'),
                    stage=run_data.get('stage'),
                    model_id=run_data.get('model_id'),
                    created_by=run_data.get('created_by'),
                    parent_run_id=run_data.get('parent_run_id'),
                    priority=run_data.get('priority', 0)
                )
                
                return {"status": "success", "run_id": run.run_id}
                
            except Exception as e:
                logger.error(f"Ошибка создания запуска: {e}")
                raise HTTPException(status_code=400, detail=str(e))
    
    def setup_security(self):
        """Настройка безопасности"""
        # Добавляем обработчики ошибок
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
    
    async def _process_n8n_webhook(self, data: dict, client_ip: str) -> dict:
        """Обработка n8n webhook"""
        logger.info(f"Обработка n8n webhook от {client_ip}: {data.get('type', 'unknown')}")
        
        # Здесь можно добавить логику обработки n8n webhook
        # Например, запуск стратегий, обновление конфигурации и т.д.
        
        return {
            "processed": True,
            "timestamp": asyncio.get_event_loop().time(),
            "client_ip": client_ip
        }
    
    async def _process_external_webhook(self, data: dict, client_ip: str) -> dict:
        """Обработка внешнего webhook"""
        logger.info(f"Обработка external webhook от {client_ip}: {data.get('type', 'unknown')}")
        
        # Здесь можно добавить логику обработки внешних webhook
        # Например, получение данных от брокеров, бирж и т.д.
        
        return {
            "processed": True,
            "timestamp": asyncio.get_event_loop().time(),
            "client_ip": client_ip
        }
    
    async def start_cleanup_tasks(self):
        """Запуск задач очистки"""
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(300)  # 5 минут
                    await rate_limiter.cleanup_old_entries()
                    logger.debug("Rate limiter очищен")
                except Exception as e:
                    logger.error(f"Ошибка очистки rate limiter: {e}")
        
        asyncio.create_task(cleanup_task())
        logger.info("Задачи очистки запущены")


# Глобальный экземпляр сервера
secure_server = SecureAPIServer()
