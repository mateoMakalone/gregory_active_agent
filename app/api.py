"""
Gregory Trading Agent - Orchestration API
FastAPI сервер для интеграции с n8n
"""

import os
import json
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, UploadFile, File
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import asyncpg
from loguru import logger
import asyncio
import uuid

from src.core.config import config


# Pydantic Models
class RunResponse(BaseModel):
    run_id: str
    status: str
    artifacts_uri: Optional[str] = None
    eta_minutes: Optional[int] = None


class StatusResponse(BaseModel):
    run_id: str
    status: str
    stage: Optional[str] = None
    progress: float = 0.0
    metrics_partial: Dict[str, Any] = {}
    logs_tail: Optional[str] = None
    error_message: Optional[str] = None


class TrainRequest(BaseModel):
    run_id: str
    strategy_id: str
    data_window_start: Optional[str] = None
    data_window_end: Optional[str] = None
    featureset: str = "default"
    hyperparams: Dict[str, Any] = {}


class ExecuteRequest(BaseModel):
    run_id: str
    strategy_id: str
    mode: str = "paper"  # paper, live
    params: Dict[str, Any] = {}


class NotifyRequest(BaseModel):
    channel: str = "general"
    text: str
    level: str = "info"  # info, warning, error, success
    attachments: List[Dict[str, str]] = []


class MetricsResponse(BaseModel):
    timestamp: datetime
    strategies: Dict[str, Dict[str, Any]]
    system: Dict[str, Any]


# App setup
app = FastAPI(
    title="Gregory Trading Agent API",
    description="Orchestration API for n8n integration",
    version="1.0.0"
)

security = HTTPBearer()


# Database connection
async def get_db_connection():
    """Получить подключение к PostgreSQL"""
    db_url = os.getenv("DATABASE_URL", config.get("orchestration", {}).get("database", {}).get("url"))
    if not db_url:
        raise HTTPException(status_code=500, detail="Database URL not configured")
    
    try:
        conn = await asyncpg.connect(db_url)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


# Security
def verify_webhook_signature(payload: str, signature: str) -> bool:
    """Проверить подпись webhook от n8n"""
    secret = os.getenv("N8N_WEBHOOK_SECRET", config.get("orchestration", {}).get("n8n", {}).get("webhook_secret"))
    if not secret:
        return False
    
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


async def verify_request(x_n8n_signature: Optional[str] = Header(None)):
    """Проверить авторизацию запроса от n8n"""
    if not x_n8n_signature:
        raise HTTPException(status_code=401, detail="Missing n8n signature")
    # В реальной реализации здесь была бы проверка подписи
    return True


# Utility functions
def generate_run_id(strategy_id: str, stage: str) -> str:
    """Сгенерировать уникальный run_id"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{stage}_{strategy_id}_{timestamp}_{unique_id}"


def get_artifacts_path(run_id: str) -> Path:
    """Получить путь к артефактам для run_id"""
    artifacts_root = os.getenv("ARTIFACTS_ROOT", config.get("orchestration", {}).get("artifacts", {}).get("root_path", "./artifacts"))
    return Path(artifacts_root) / run_id


async def create_run_record(conn: asyncpg.Connection, run_id: str, strategy_id: str, stage: str, status: str = "started"):
    """Создать запись о запуске в БД"""
    await conn.execute("""
        INSERT INTO runs (run_id, strategy_id, stage, status, started_at)
        VALUES ($1, $2, $3, $4, $5)
    """, run_id, strategy_id, stage, status, datetime.now(timezone.utc))


async def update_run_status(conn: asyncpg.Connection, run_id: str, status: str, progress: float = None, 
                           metrics: Dict = None, error_message: str = None):
    """Обновить статус запуска"""
    set_clause = "status = $2"
    params = [run_id, status]
    param_count = 2
    
    if progress is not None:
        param_count += 1
        set_clause += f", progress = ${param_count}"
        params.append(progress)
    
    if metrics:
        param_count += 1
        set_clause += f", metrics_partial = ${param_count}"
        params.append(json.dumps(metrics))
    
    if error_message:
        param_count += 1
        set_clause += f", error_message = ${param_count}"
        params.append(error_message)
    
    if status in ["completed", "failed", "cancelled"]:
        param_count += 1
        set_clause += f", ended_at = ${param_count}"
        params.append(datetime.now(timezone.utc))
    
    query = f"UPDATE runs SET {set_clause} WHERE run_id = $1"
    await conn.execute(query, *params)


# Background task functions
async def run_data_ingestion(run_id: str, strategy_id: str, params: Dict):
    """Фоновая задача для сбора данных"""
    conn = await get_db_connection()
    try:
        await update_run_status(conn, run_id, "running", 10.0)
        
        # Симуляция сбора данных
        await asyncio.sleep(5)
        await update_run_status(conn, run_id, "running", 50.0)
        
        await asyncio.sleep(5)
        await update_run_status(conn, run_id, "running", 90.0)
        
        # Создание артефактов
        artifacts_path = get_artifacts_path(run_id)
        artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # Сохранение метаданных
        metadata = {
            "run_id": run_id,
            "strategy_id": strategy_id,
            "stage": "ingest",
            "data_rows": 10000,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        with open(artifacts_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        await update_run_status(conn, run_id, "completed", 100.0, {"data_rows": 10000})
        logger.info(f"Data ingestion completed for {run_id}")
        
    except Exception as e:
        logger.error(f"Data ingestion failed for {run_id}: {e}")
        await update_run_status(conn, run_id, "failed", error_message=str(e))
    finally:
        await conn.close()


async def run_training(run_id: str, strategy_id: str, params: Dict):
    """Фоновая задача для обучения модели"""
    conn = await get_db_connection()
    try:
        await update_run_status(conn, run_id, "running", 0.0)
        
        # Симуляция этапов обучения
        stages = [
            ("feature_engineering", 20.0),
            ("model_training", 60.0),
            ("validation", 80.0),
            ("saving_model", 95.0)
        ]
        
        for stage_name, progress in stages:
            logger.info(f"Training {run_id}: {stage_name} - {progress}%")
            await update_run_status(conn, run_id, "running", progress, {"current_stage": stage_name})
            await asyncio.sleep(10)  # Симуляция времени обучения
        
        # Создание артефактов модели
        artifacts_path = get_artifacts_path(run_id)
        artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # Симуляция метрик модели
        model_metrics = {
            "accuracy": 0.78,
            "precision": 0.75,
            "recall": 0.82,
            "f1_score": 0.78,
            "sharpe_ratio": 1.35,
            "max_drawdown": 0.12
        }
        
        # Сохранение метрик
        with open(artifacts_path / "metrics.json", "w") as f:
            json.dump(model_metrics, f, indent=2)
        
        # Создание записи модели в БД
        model_id = f"model_{strategy_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        await conn.execute("""
            INSERT INTO models (model_id, strategy_id, version, metrics, artifacts_uri, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, model_id, strategy_id, 1, json.dumps(model_metrics), str(artifacts_path), datetime.now(timezone.utc))
        
        await update_run_status(conn, run_id, "completed", 100.0, model_metrics)
        logger.info(f"Training completed for {run_id}")
        
    except Exception as e:
        logger.error(f"Training failed for {run_id}: {e}")
        await update_run_status(conn, run_id, "failed", error_message=str(e))
    finally:
        await conn.close()


# API Endpoints

@app.post("/ingest", response_model=RunResponse)
async def ingest_data(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    # auth: bool = Depends(verify_request)
):
    """Запустить сбор данных"""
    run_id = request.run_id or generate_run_id(request.strategy_id, "ingest")
    
    conn = await get_db_connection()
    try:
        await create_run_record(conn, run_id, request.strategy_id, "ingest")
        
        # Запуск фоновой задачи
        background_tasks.add_task(
            run_data_ingestion, 
            run_id, 
            request.strategy_id, 
            request.dict()
        )
        
        return RunResponse(
            run_id=run_id,
            status="started",
            artifacts_uri=f"/artifacts/{run_id}",
            eta_minutes=2
        )
        
    finally:
        await conn.close()


@app.post("/train", response_model=RunResponse)
async def train_model(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    # auth: bool = Depends(verify_request)
):
    """Запустить обучение модели"""
    run_id = request.run_id or generate_run_id(request.strategy_id, "train")
    
    conn = await get_db_connection()
    try:
        await create_run_record(conn, run_id, request.strategy_id, "train")
        
        # Запуск фоновой задачи
        background_tasks.add_task(
            run_training, 
            run_id, 
            request.strategy_id, 
            request.dict()
        )
        
        return RunResponse(
            run_id=run_id,
            status="started",
            artifacts_uri=f"/artifacts/{run_id}",
            eta_minutes=45
        )
        
    finally:
        await conn.close()


@app.post("/backtest", response_model=RunResponse)
async def run_backtest(
    request: TrainRequest,
    # auth: bool = Depends(verify_request)
):
    """Запустить бэктестинг"""
    run_id = request.run_id or generate_run_id(request.strategy_id, "backtest")
    
    # Здесь будет логика бэктестинга
    return RunResponse(
        run_id=run_id,
        status="started",
        artifacts_uri=f"/artifacts/{run_id}",
        eta_minutes=15
    )


@app.post("/promote", response_model=RunResponse)
async def promote_model(
    request: TrainRequest,
    # auth: bool = Depends(verify_request)
):
    """Активировать модель"""
    run_id = request.run_id or generate_run_id(request.strategy_id, "promote")
    
    # Здесь будет логика активации модели
    return RunResponse(
        run_id=run_id,
        status="completed",
        artifacts_uri=f"/artifacts/{run_id}"
    )


@app.post("/prepare", response_model=RunResponse)
async def prepare_environment(
    request: ExecuteRequest,
    # auth: bool = Depends(verify_request)
):
    """Подготовить окружение для выполнения"""
    run_id = request.run_id or generate_run_id(request.strategy_id, "prepare")
    
    # Здесь будет логика подготовки окружения
    return RunResponse(
        run_id=run_id,
        status="completed",
        artifacts_uri=f"/artifacts/{run_id}"
    )


@app.post("/execute", response_model=RunResponse)
async def execute_strategy(
    request: ExecuteRequest,
    # auth: bool = Depends(verify_request)
):
    """Запустить выполнение стратегии"""
    run_id = request.run_id or generate_run_id(request.strategy_id, "execute")
    
    # Здесь будет логика выполнения стратегии
    return RunResponse(
        run_id=run_id,
        status="started",
        artifacts_uri=f"/artifacts/{run_id}",
        eta_minutes=5
    )


@app.get("/status/{run_id}", response_model=StatusResponse)
async def get_status(run_id: str):
    """Получить статус выполнения"""
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("""
            SELECT run_id, status, stage, progress, metrics_partial, error_message
            FROM runs WHERE run_id = $1
        """, run_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Попытка прочитать логи
        artifacts_path = get_artifacts_path(run_id)
        logs_tail = ""
        log_file = artifacts_path / "logs.txt"
        if log_file.exists():
            with open(log_file, "r") as f:
                lines = f.readlines()
                logs_tail = "".join(lines[-10:])  # Последние 10 строк
        
        return StatusResponse(
            run_id=row["run_id"],
            status=row["status"],
            stage=row["stage"],
            progress=float(row["progress"] or 0),
            metrics_partial=json.loads(row["metrics_partial"] or "{}"),
            logs_tail=logs_tail,
            error_message=row["error_message"]
        )
        
    finally:
        await conn.close()


@app.get("/metrics", response_model=MetricsResponse)
async def get_live_metrics():
    """Получить живые метрики для Metrics Guard"""
    conn = await get_db_connection()
    try:
        # Получить последние метрики по стратегиям
        strategies_data = {}
        rows = await conn.fetch("""
            SELECT DISTINCT ON (strategy_id) strategy_id, sharpe_ratio, max_drawdown, 
                   latency_ms, positions_count, pnl_daily, data_staleness_minutes
            FROM live_metrics 
            ORDER BY strategy_id, timestamp DESC
        """)
        
        for row in rows:
            strategies_data[row["strategy_id"]] = {
                "sharpe_ratio": float(row["sharpe_ratio"] or 0),
                "max_drawdown": float(row["max_drawdown"] or 0),
                "latency_ms": row["latency_ms"] or 0,
                "positions_count": row["positions_count"] or 0,
                "pnl_daily": float(row["pnl_daily"] or 0),
                "data_staleness_minutes": row["data_staleness_minutes"] or 0
            }
        
        # Системные метрики
        system_data = {
            "active_runs": await conn.fetchval("SELECT COUNT(*) FROM runs WHERE status = 'running'"),
            "failed_runs_today": await conn.fetchval("""
                SELECT COUNT(*) FROM runs 
                WHERE status = 'failed' AND started_at > NOW() - INTERVAL '1 day'
            """),
            "disk_usage_pct": 45.2,  # Пример
            "memory_usage_pct": 67.8
        }
        
        return MetricsResponse(
            timestamp=datetime.now(timezone.utc),
            strategies=strategies_data,
            system=system_data
        )
        
    finally:
        await conn.close()


@app.post("/notify")
async def send_notification(request: NotifyRequest):
    """Отправить уведомление в Telegram через существующий бот"""
    try:
        # Здесь должен быть вызов существующего telegram_bot
        # Для примера просто логируем
        logger.info(f"Notification [{request.level}] to {request.channel}: {request.text}")
        
        # В реальной реализации:
        # from telegram_bot.bot import send_notification
        # await send_notification(request.channel, request.text, request.level, request.attachments)
        
        return {"status": "sent", "channel": request.channel}
        
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    try:
        conn = await get_db_connection()
        await conn.fetchval("SELECT 1")
        await conn.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc),
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
