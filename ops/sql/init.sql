-- Trading AI Agent - Полная схема базы данных
-- Поддерживает PostgreSQL для оркестрации и SQLite для совместимости

-- ==============================================
-- ОСНОВНЫЕ ТАБЛИЦЫ СИСТЕМЫ
-- ==============================================

-- Стратегии торговли
CREATE TABLE IF NOT EXISTS strategies (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL DEFAULT 'trend_following', -- trend_following, mean_reversion, breakout, scalping
    version INTEGER DEFAULT 1,
    latest_model_id VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    auto_retrain BOOLEAN DEFAULT FALSE,
    quality_thresholds JSONB DEFAULT '{}',
    risk_limits JSONB DEFAULT '{}',
    owner VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Модели машинного обучения
CREATE TABLE IF NOT EXISTS models (
    model_id VARCHAR(255) PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- xgboost, lightgbm, neural_network, ensemble
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

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ ОРКЕСТРАЦИИ
-- ==============================================

-- Запуски (runs) - основная таблица для отслеживания выполнения
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR(255) PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    model_id VARCHAR(255) REFERENCES models(model_id) ON DELETE SET NULL,
    stage VARCHAR(50) NOT NULL, -- ingest, train, backtest, promote, execute, monitor
    status VARCHAR(50) NOT NULL, -- started, running, completed, failed, cancelled, paused
    progress DECIMAL(5,2) DEFAULT 0.0, -- 0.00 to 100.00
    eta_minutes INTEGER,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    logs_uri TEXT,
    metrics_partial JSONB DEFAULT '{}',
    error_message TEXT,
    created_by VARCHAR(100),
    parent_run_id VARCHAR(255) REFERENCES runs(run_id) ON DELETE SET NULL,
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Задания (jobs) - детализация задач внутри запусков
CREATE TABLE IF NOT EXISTS jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    run_id VARCHAR(255) REFERENCES runs(run_id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- data_collection, feature_engineering, training, validation, backtesting
    status VARCHAR(50) NOT NULL, -- pending, running, completed, failed, cancelled
    priority INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    parameters JSONB DEFAULT '{}',
    results JSONB DEFAULT '{}',
    worker_id VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Выполнения (executions) - детальная информация о выполнении
CREATE TABLE IF NOT EXISTS executions (
    execution_id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES jobs(job_id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL, -- started, completed, failed
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    memory_used_mb INTEGER,
    cpu_usage_percent DECIMAL(5,2),
    error_message TEXT,
    logs TEXT,
    metrics JSONB DEFAULT '{}'
);

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ ТОРГОВЛИ
-- ==============================================

-- Торговые сигналы
CREATE TABLE IF NOT EXISTS signals (
    signal_id VARCHAR(255) PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    model_id VARCHAR(255) REFERENCES models(model_id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    signal_type VARCHAR(10) NOT NULL, -- BUY, SELL, HOLD
    strength VARCHAR(10) NOT NULL, -- WEAK, MEDIUM, STRONG
    price DECIMAL(20,8) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL, -- 0.0000 to 1.0000
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending' -- pending, processed, cancelled, expired
);

-- Позиции
CREATE TABLE IF NOT EXISTS positions (
    position_id VARCHAR(255) PRIMARY KEY,
    signal_id VARCHAR(255) REFERENCES signals(signal_id) ON DELETE SET NULL,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- LONG, SHORT
    size DECIMAL(20,8) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    current_price DECIMAL(20,8),
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'open', -- open, closed, cancelled
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- Ордера
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(255) PRIMARY KEY,
    position_id VARCHAR(255) REFERENCES positions(position_id) ON DELETE SET NULL,
    signal_id VARCHAR(255) REFERENCES signals(signal_id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- BUY, SELL
    type VARCHAR(20) NOT NULL, -- MARKET, LIMIT, STOP, STOP_LIMIT
    size DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    stop_price DECIMAL(20,8),
    status VARCHAR(20) DEFAULT 'pending', -- pending, filled, cancelled, rejected, expired
    filled_size DECIMAL(20,8) DEFAULT 0,
    filled_price DECIMAL(20,8),
    commission DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    external_order_id VARCHAR(255), -- ID от брокера/биржи
    metadata JSONB DEFAULT '{}'
);

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ МОНИТОРИНГА
-- ==============================================

-- Живые метрики для мониторинга
CREATE TABLE IF NOT EXISTS live_metrics (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    win_rate DECIMAL(5,4),
    profit_factor DECIMAL(8,4),
    latency_ms INTEGER,
    positions_count INTEGER,
    pnl_daily DECIMAL(15,2),
    pnl_total DECIMAL(15,2),
    data_staleness_minutes INTEGER,
    error_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,4)
);

-- Алерты и уведомления
CREATE TABLE IF NOT EXISTS alerts (
    alert_id VARCHAR(255) PRIMARY KEY,
    strategy_id VARCHAR(100) REFERENCES strategies(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- performance, error, risk, system
    severity VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, acknowledged, resolved, dismissed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    metadata JSONB DEFAULT '{}'
);

-- Неудачные задания
CREATE TABLE IF NOT EXISTS failed_jobs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) REFERENCES runs(run_id) ON DELETE CASCADE,
    job_id VARCHAR(255) REFERENCES jobs(job_id) ON DELETE CASCADE,
    workflow_name VARCHAR(100),
    stage VARCHAR(50),
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    logs_tail TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ ДАННЫХ
-- ==============================================

-- Источники данных
CREATE TABLE IF NOT EXISTS data_sources (
    source_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- fundingpips, hashhedge, yahoo, alpha_vantage
    config JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT TRUE,
    last_update TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Символы для торговли
CREATE TABLE IF NOT EXISTS trading_symbols (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL, -- forex, crypto, stock, commodity
    source_id VARCHAR(100) REFERENCES data_sources(source_id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT TRUE,
    min_trade_size DECIMAL(20,8),
    max_trade_size DECIMAL(20,8),
    tick_size DECIMAL(20,8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==============================================
-- ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- ==============================================

-- Индексы для runs
CREATE INDEX IF NOT EXISTS idx_runs_strategy_status ON runs(strategy_id, status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_stage_status ON runs(stage, status);

-- Индексы для jobs
CREATE INDEX IF NOT EXISTS idx_jobs_run_id ON jobs(run_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority DESC);

-- Индексы для executions
CREATE INDEX IF NOT EXISTS idx_executions_job_id ON executions(job_id);
CREATE INDEX IF NOT EXISTS idx_executions_started_at ON executions(started_at);

-- Индексы для signals
CREATE INDEX IF NOT EXISTS idx_signals_strategy_symbol ON signals(strategy_id, symbol);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_signal_type ON signals(signal_type);

-- Индексы для positions
CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_opened_at ON positions(opened_at);

-- Индексы для orders
CREATE INDEX IF NOT EXISTS idx_orders_position_id ON orders(position_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_external_id ON orders(external_order_id);

-- Индексы для live_metrics
CREATE INDEX IF NOT EXISTS idx_live_metrics_timestamp ON live_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_live_metrics_strategy ON live_metrics(strategy_id);

-- Индексы для alerts
CREATE INDEX IF NOT EXISTS idx_alerts_strategy ON alerts(strategy_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);

-- ==============================================
-- ФУНКЦИИ И ТРИГГЕРЫ
-- ==============================================

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для обновления updated_at
CREATE TRIGGER update_strategies_updated_at 
    BEFORE UPDATE ON strategies 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Функция для расчета PnL позиции
CREATE OR REPLACE FUNCTION calculate_position_pnl()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.current_price IS NOT NULL AND NEW.entry_price IS NOT NULL THEN
        IF NEW.side = 'LONG' THEN
            NEW.unrealized_pnl = (NEW.current_price - NEW.entry_price) * NEW.size;
        ELSE
            NEW.unrealized_pnl = (NEW.entry_price - NEW.current_price) * NEW.size;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического расчета PnL
CREATE TRIGGER calculate_pnl_trigger
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION calculate_position_pnl();

-- ==============================================
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ==============================================

-- Вставка источников данных
INSERT INTO data_sources (source_id, name, type, config) VALUES 
('fundingpips', 'FundingPips API', 'fundingpips', '{"base_url": "https://api.fundingpips.com"}'),
('hashhedge', 'HashHedge API', 'hashhedge', '{"base_url": "https://api.hashhedge.com"}'),
('yahoo', 'Yahoo Finance', 'yahoo', '{"base_url": "https://query1.finance.yahoo.com"}')
ON CONFLICT (source_id) DO NOTHING;

-- Вставка торговых символов
INSERT INTO trading_symbols (symbol, name, type, source_id, min_trade_size, max_trade_size, tick_size) VALUES 
('EURUSD', 'Euro/US Dollar', 'forex', 'fundingpips', 0.01, 1000, 0.00001),
('GBPUSD', 'British Pound/US Dollar', 'forex', 'fundingpips', 0.01, 1000, 0.00001),
('USDJPY', 'US Dollar/Japanese Yen', 'forex', 'fundingpips', 0.01, 1000, 0.001),
('BTCUSDT', 'Bitcoin/USDT', 'crypto', 'hashhedge', 0.001, 100, 0.01),
('ETHUSDT', 'Ethereum/USDT', 'crypto', 'hashhedge', 0.001, 1000, 0.01),
('ADAUSDT', 'Cardano/USDT', 'crypto', 'hashhedge', 1, 100000, 0.0001)
ON CONFLICT (symbol) DO NOTHING;

-- Вставка примеров стратегий
INSERT INTO strategies (id, name, description, type, quality_thresholds, risk_limits) VALUES 
('eurusd_mtf', 'EUR/USD Multi-Timeframe Strategy', 'Трендовая стратегия с анализом нескольких таймфреймов', 'trend_following', 
 '{"min_sharpe": 1.2, "max_drawdown": 0.15, "max_staleness_hours": 4}',
 '{"max_position_size": 0.02, "stop_loss_pct": 0.01, "take_profit_pct": 0.02}'),
('btcusd_momentum', 'BTC/USD Momentum Strategy', 'Импульсная стратегия для торговли Bitcoin', 'momentum',
 '{"min_sharpe": 1.0, "max_drawdown": 0.20, "max_staleness_hours": 2}',
 '{"max_position_size": 0.01, "stop_loss_pct": 0.02, "take_profit_pct": 0.04}')
ON CONFLICT (id) DO NOTHING;

-- ==============================================
-- ПРАВА ДОСТУПА
-- ==============================================

-- Создание пользователя для чтения (опционально)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_readonly') THEN
        CREATE ROLE trading_readonly;
    END IF;
END
$$;

-- Предоставление прав на чтение
GRANT CONNECT ON DATABASE gregory_orchestration TO trading_readonly;
GRANT USAGE ON SCHEMA public TO trading_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO trading_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO trading_readonly;