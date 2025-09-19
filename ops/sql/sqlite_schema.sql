-- Trading AI Agent - SQLite Schema
-- Упрощенная версия для совместимости с SQLite

-- ==============================================
-- ОСНОВНЫЕ ТАБЛИЦЫ
-- ==============================================

-- Стратегии торговли
CREATE TABLE IF NOT EXISTS strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'trend_following',
    version INTEGER DEFAULT 1,
    latest_model_id TEXT,
    active BOOLEAN DEFAULT 1,
    auto_retrain BOOLEAN DEFAULT 0,
    quality_thresholds TEXT DEFAULT '{}',
    risk_limits TEXT DEFAULT '{}',
    owner TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Модели машинного обучения
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    strategy_id TEXT REFERENCES strategies(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    featureset TEXT,
    data_window_start DATE,
    data_window_end DATE,
    hyperparams TEXT DEFAULT '{}',
    metrics TEXT DEFAULT '{}',
    artifacts_uri TEXT,
    promoted BOOLEAN DEFAULT 0,
    promoted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ ОРКЕСТРАЦИИ
-- ==============================================

-- Запуски (runs)
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    strategy_id TEXT REFERENCES strategies(id) ON DELETE CASCADE,
    model_id TEXT REFERENCES models(model_id) ON DELETE SET NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0.0,
    eta_minutes INTEGER,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    logs_uri TEXT,
    metrics_partial TEXT DEFAULT '{}',
    error_message TEXT,
    created_by TEXT,
    parent_run_id TEXT,
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Задания (jobs)
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    parameters TEXT DEFAULT '{}',
    results TEXT DEFAULT '{}',
    worker_id TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Выполнения (executions)
CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(job_id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    duration_ms INTEGER,
    memory_used_mb INTEGER,
    cpu_usage_percent REAL,
    error_message TEXT,
    logs TEXT,
    metrics TEXT DEFAULT '{}'
);

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ ТОРГОВЛИ
-- ==============================================

-- Торговые сигналы
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    strategy_id TEXT REFERENCES strategies(id) ON DELETE CASCADE,
    model_id TEXT REFERENCES models(model_id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    strength TEXT NOT NULL,
    price REAL NOT NULL,
    confidence REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME,
    status TEXT DEFAULT 'pending'
);

-- Позиции
CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    signal_id TEXT REFERENCES signals(signal_id) ON DELETE SET NULL,
    strategy_id TEXT REFERENCES strategies(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    size REAL NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL,
    stop_loss REAL,
    take_profit REAL,
    unrealized_pnl REAL DEFAULT 0,
    realized_pnl REAL DEFAULT 0,
    status TEXT DEFAULT 'open',
    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,
    metadata TEXT DEFAULT '{}'
);

-- Ордера
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    position_id TEXT REFERENCES positions(position_id) ON DELETE SET NULL,
    signal_id TEXT REFERENCES signals(signal_id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    type TEXT NOT NULL,
    size REAL NOT NULL,
    price REAL,
    stop_price REAL,
    status TEXT DEFAULT 'pending',
    filled_size REAL DEFAULT 0,
    filled_price REAL,
    commission REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    filled_at DATETIME,
    cancelled_at DATETIME,
    error_message TEXT,
    external_order_id TEXT,
    metadata TEXT DEFAULT '{}'
);

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ МОНИТОРИНГА
-- ==============================================

-- Живые метрики
CREATE TABLE IF NOT EXISTS live_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT REFERENCES strategies(id) ON DELETE CASCADE,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    sharpe_ratio REAL,
    max_drawdown REAL,
    win_rate REAL,
    profit_factor REAL,
    latency_ms INTEGER,
    positions_count INTEGER,
    pnl_daily REAL,
    pnl_total REAL,
    data_staleness_minutes INTEGER,
    error_count INTEGER DEFAULT 0,
    success_rate REAL
);

-- Алерты
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    strategy_id TEXT REFERENCES strategies(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at DATETIME,
    acknowledged_by TEXT,
    resolved_at DATETIME,
    resolved_by TEXT,
    metadata TEXT DEFAULT '{}'
);

-- Неудачные задания
CREATE TABLE IF NOT EXISTS failed_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
    job_id TEXT REFERENCES jobs(job_id) ON DELETE CASCADE,
    workflow_name TEXT,
    stage TEXT,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    logs_tail TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME
);

-- ==============================================
-- ТАБЛИЦЫ ДЛЯ ДАННЫХ
-- ==============================================

-- Источники данных
CREATE TABLE IF NOT EXISTS data_sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    config TEXT DEFAULT '{}',
    active BOOLEAN DEFAULT 1,
    last_update DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Торговые символы
CREATE TABLE IF NOT EXISTS trading_symbols (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    source_id TEXT REFERENCES data_sources(source_id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT 1,
    min_trade_size REAL,
    max_trade_size REAL,
    tick_size REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================
-- ИНДЕКСЫ
-- ==============================================

-- Индексы для runs
CREATE INDEX IF NOT EXISTS idx_runs_strategy_status ON runs(strategy_id, status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);

-- Индексы для jobs
CREATE INDEX IF NOT EXISTS idx_jobs_run_id ON jobs(run_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Индексы для signals
CREATE INDEX IF NOT EXISTS idx_signals_strategy_symbol ON signals(strategy_id, symbol);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);

-- Индексы для positions
CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);

-- Индексы для orders
CREATE INDEX IF NOT EXISTS idx_orders_position_id ON orders(position_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Индексы для live_metrics
CREATE INDEX IF NOT EXISTS idx_live_metrics_timestamp ON live_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_live_metrics_strategy ON live_metrics(strategy_id);

-- ==============================================
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ==============================================

-- Источники данных
INSERT OR IGNORE INTO data_sources (source_id, name, type, config) VALUES 
('fundingpips', 'FundingPips API', 'fundingpips', '{"base_url": "https://api.fundingpips.com"}'),
('hashhedge', 'HashHedge API', 'hashhedge', '{"base_url": "https://api.hashhedge.com"}'),
('yahoo', 'Yahoo Finance', 'yahoo', '{"base_url": "https://query1.finance.yahoo.com"}');

-- Торговые символы
INSERT OR IGNORE INTO trading_symbols (symbol, name, type, source_id, min_trade_size, max_trade_size, tick_size) VALUES 
('EURUSD', 'Euro/US Dollar', 'forex', 'fundingpips', 0.01, 1000, 0.00001),
('GBPUSD', 'British Pound/US Dollar', 'forex', 'fundingpips', 0.01, 1000, 0.00001),
('USDJPY', 'US Dollar/Japanese Yen', 'forex', 'fundingpips', 0.01, 1000, 0.001),
('BTCUSDT', 'Bitcoin/USDT', 'crypto', 'hashhedge', 0.001, 100, 0.01),
('ETHUSDT', 'Ethereum/USDT', 'crypto', 'hashhedge', 0.001, 1000, 0.01),
('ADAUSDT', 'Cardano/USDT', 'crypto', 'hashhedge', 1, 100000, 0.0001);

-- Примеры стратегий
INSERT OR IGNORE INTO strategies (id, name, description, type, quality_thresholds, risk_limits) VALUES 
('eurusd_mtf', 'EUR/USD Multi-Timeframe Strategy', 'Трендовая стратегия с анализом нескольких таймфреймов', 'trend_following', 
 '{"min_sharpe": 1.2, "max_drawdown": 0.15, "max_staleness_hours": 4}',
 '{"max_position_size": 0.02, "stop_loss_pct": 0.01, "take_profit_pct": 0.02}'),
('btcusd_momentum', 'BTC/USD Momentum Strategy', 'Импульсная стратегия для торговли Bitcoin', 'momentum',
 '{"min_sharpe": 1.0, "max_drawdown": 0.20, "max_staleness_hours": 2}',
 '{"max_position_size": 0.01, "stop_loss_pct": 0.02, "take_profit_pct": 0.04}');
