-- Gregory Trading Agent - Orchestration Database Schema
-- Создается автоматически при инициализации PostgreSQL

-- Стратегии
CREATE TABLE IF NOT EXISTS strategies (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    latest_version INTEGER DEFAULT 0,
    active_model_id VARCHAR(255),
    owner VARCHAR(100),
    auto_retrain BOOLEAN DEFAULT FALSE,
    quality_thresholds JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Модели
CREATE TABLE IF NOT EXISTS models (
    model_id VARCHAR(255) PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    featureset VARCHAR(100),
    data_window_start DATE,
    data_window_end DATE,
    hyperparams JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    artifacts_uri TEXT,
    promoted BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Запуски (runs)
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR(255) PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    model_id VARCHAR(255) REFERENCES models(model_id) ON DELETE SET NULL,
    stage VARCHAR(50) NOT NULL, -- ingest, train, backtest, promote, execute
    status VARCHAR(50) NOT NULL, -- started, running, completed, failed, cancelled
    progress DECIMAL(5,2) DEFAULT 0.0, -- 0.00 to 100.00
    eta_minutes INTEGER,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    logs_uri TEXT,
    metrics_partial JSONB DEFAULT '{}',
    error_message TEXT,
    created_by VARCHAR(100),
    parent_run_id VARCHAR(255) -- для связанных запусков
);

-- Неудачные задания
CREATE TABLE IF NOT EXISTS failed_jobs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) REFERENCES runs(run_id) ON DELETE CASCADE,
    workflow_name VARCHAR(100),
    stage VARCHAR(50),
    error_type VARCHAR(100),
    error_message TEXT,
    logs_tail TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Живые метрики для Metrics Guard
CREATE TABLE IF NOT EXISTS live_metrics (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    latency_ms INTEGER,
    positions_count INTEGER,
    pnl_daily DECIMAL(15,2),
    data_staleness_minutes INTEGER
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_runs_strategy_status ON runs(strategy_id, status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_models_strategy_version ON models(strategy_id, version);
CREATE INDEX IF NOT EXISTS idx_models_promoted ON models(promoted, strategy_id);
CREATE INDEX IF NOT EXISTS idx_live_metrics_timestamp ON live_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_failed_jobs_created_at ON failed_jobs(created_at);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для strategies
CREATE TRIGGER update_strategies_updated_at 
    BEFORE UPDATE ON strategies 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Вставка примера стратегии для тестирования
INSERT INTO strategies (id, name, description, auto_retrain, quality_thresholds) 
VALUES (
    'eurusd_mtf',
    'EUR/USD Multi-Timeframe Strategy',
    'Трендовая стратегия с анализом нескольких таймфреймов',
    TRUE,
    '{"min_sharpe": 1.2, "max_drawdown": 0.15, "max_staleness_hours": 4}'
) ON CONFLICT (id) DO NOTHING;

-- Вставка примера стратегии momentum
INSERT INTO strategies (id, name, description, auto_retrain, quality_thresholds) 
VALUES (
    'btcusd_momentum',
    'BTC/USD Momentum Strategy', 
    'Импульсная стратегия для торговли Bitcoin',
    FALSE,
    '{"min_sharpe": 1.0, "max_drawdown": 0.20, "max_staleness_hours": 2}'
) ON CONFLICT (id) DO NOTHING;

-- Создание пользователя для чтения (опционально)
-- DO $$ 
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'gregory_readonly') THEN
--         CREATE ROLE gregory_readonly;
--     END IF;
-- END
-- $$;
-- 
-- GRANT CONNECT ON DATABASE gregory_orchestration TO gregory_readonly;
-- GRANT USAGE ON SCHEMA public TO gregory_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO gregory_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO gregory_readonly;

