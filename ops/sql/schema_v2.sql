-- Trading AI Agent - Обновленная схема базы данных (v2)
-- PostgreSQL с поддержкой runs, signals, orders, positions, executions, metrics

-- ==============================================
-- ОСНОВНЫЕ ТАБЛИЦЫ
-- ==============================================

-- Запуски стратегий
CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(100) NOT NULL,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('paper', 'live')),
    status VARCHAR(20) NOT NULL DEFAULT 'init' CHECK (status IN ('init', 'warmup', 'running', 'paused', 'stopped', 'error')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    note TEXT,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Торговые сигналы
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL', 'HOLD', 'CLOSE')),
    strength DECIMAL(5,4) NOT NULL CHECK (strength >= 0 AND strength <= 1),
    price DECIMAL(20,8) NOT NULL,
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    quantity DECIMAL(20,8),
    reason TEXT,
    params JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Торговые ордера
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    client_id VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    type VARCHAR(20) NOT NULL CHECK (type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')),
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    stop_price DECIMAL(20,8),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED')),
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    average_price DECIMAL(20,8),
    exchange_order_id VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Уникальность по client_id для идемпотентности
    UNIQUE(run_id, client_id)
);

-- Позиции
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    average_price DECIMAL(20,8) NOT NULL,
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Уникальность по символу в рамках запуска
    UNIQUE(run_id, symbol)
);

-- Исполнения ордеров
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    fee DECIMAL(20,8) DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Метрики
CREATE TABLE IF NOT EXISTS metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    value DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- ==============================================
-- ДОПОЛНИТЕЛЬНЫЕ ТАБЛИЦЫ
-- ==============================================

-- Балансы
CREATE TABLE IF NOT EXISTS balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    currency VARCHAR(10) NOT NULL,
    free DECIMAL(20,8) NOT NULL DEFAULT 0,
    used DECIMAL(20,8) NOT NULL DEFAULT 0,
    total DECIMAL(20,8) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(run_id, currency)
);

-- События стратегии
CREATE TABLE IF NOT EXISTS strategy_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'INFO' CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- ==============================================
-- ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- ==============================================

-- Индексы для runs
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_strategy_mode ON runs(strategy_name, mode);

-- Индексы для signals
CREATE INDEX IF NOT EXISTS idx_signals_run_id ON signals(run_id);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_processed ON signals(processed);

-- Индексы для orders
CREATE INDEX IF NOT EXISTS idx_orders_run_id ON orders(run_id);
CREATE INDEX IF NOT EXISTS idx_orders_client_id ON orders(client_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Индексы для positions
CREATE INDEX IF NOT EXISTS idx_positions_run_id ON positions(run_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);

-- Индексы для executions
CREATE INDEX IF NOT EXISTS idx_executions_order_id ON executions(order_id);
CREATE INDEX IF NOT EXISTS idx_executions_timestamp ON executions(timestamp);
CREATE INDEX IF NOT EXISTS idx_executions_symbol ON executions(symbol);

-- Индексы для metrics
CREATE INDEX IF NOT EXISTS idx_metrics_run_id ON metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);

-- Индексы для balances
CREATE INDEX IF NOT EXISTS idx_balances_run_id ON balances(run_id);
CREATE INDEX IF NOT EXISTS idx_balances_currency ON balances(currency);

-- Индексы для strategy_events
CREATE INDEX IF NOT EXISTS idx_strategy_events_run_id ON strategy_events(run_id);
CREATE INDEX IF NOT EXISTS idx_strategy_events_timestamp ON strategy_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_strategy_events_level ON strategy_events(level);

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
CREATE TRIGGER update_runs_updated_at 
    BEFORE UPDATE ON runs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Функция для обновления позиций при исполнении
CREATE OR REPLACE FUNCTION update_position_on_execution()
RETURNS TRIGGER AS $$
DECLARE
    current_qty DECIMAL(20,8);
    current_avg_price DECIMAL(20,8);
    new_qty DECIMAL(20,8);
    new_avg_price DECIMAL(20,8);
BEGIN
    -- Получаем текущую позицию
    SELECT quantity, average_price 
    INTO current_qty, current_avg_price
    FROM positions 
    WHERE run_id = (SELECT run_id FROM orders WHERE id = NEW.order_id)
    AND symbol = NEW.symbol;
    
    -- Если позиции нет, создаем новую
    IF current_qty IS NULL THEN
        INSERT INTO positions (run_id, symbol, quantity, average_price)
        VALUES (
            (SELECT run_id FROM orders WHERE id = NEW.order_id),
            NEW.symbol,
            CASE WHEN NEW.side = 'BUY' THEN NEW.quantity ELSE -NEW.quantity END,
            NEW.price
        );
    ELSE
        -- Обновляем существующую позицию
        new_qty := current_qty + CASE WHEN NEW.side = 'BUY' THEN NEW.quantity ELSE -NEW.quantity END;
        
        -- Рассчитываем новую среднюю цену
        IF new_qty = 0 THEN
            new_avg_price := 0;
        ELSIF (current_qty > 0 AND new_qty > 0) OR (current_qty < 0 AND new_qty < 0) THEN
            new_avg_price := (current_qty * current_avg_price + NEW.quantity * NEW.price) / new_qty;
        ELSE
            new_avg_price := NEW.price;
        END IF;
        
        -- Обновляем или удаляем позицию
        IF new_qty = 0 THEN
            DELETE FROM positions 
            WHERE run_id = (SELECT run_id FROM orders WHERE id = NEW.order_id)
            AND symbol = NEW.symbol;
        ELSE
            UPDATE positions 
            SET quantity = new_qty, 
                average_price = new_avg_price,
                updated_at = NOW()
            WHERE run_id = (SELECT run_id FROM orders WHERE id = NEW.order_id)
            AND symbol = NEW.symbol;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для обновления позиций
CREATE TRIGGER update_position_on_execution_trigger
    AFTER INSERT ON executions
    FOR EACH ROW
    EXECUTE FUNCTION update_position_on_execution();

-- ==============================================
-- ПРЕДСТАВЛЕНИЯ (VIEWS)
-- ==============================================

-- Представление для активных позиций
CREATE OR REPLACE VIEW active_positions AS
SELECT 
    p.*,
    r.strategy_name,
    r.mode,
    r.status as run_status
FROM positions p
JOIN runs r ON p.run_id = r.run_id
WHERE r.status = 'running'
AND p.quantity != 0;

-- Представление для статистики по запускам
CREATE OR REPLACE VIEW run_statistics AS
SELECT 
    r.run_id,
    r.strategy_name,
    r.mode,
    r.status,
    r.started_at,
    r.finished_at,
    COALESCE(signal_count.count, 0) as signals_count,
    COALESCE(order_count.count, 0) as orders_count,
    COALESCE(position_count.count, 0) as positions_count,
    COALESCE(execution_count.count, 0) as executions_count,
    COALESCE(total_pnl.pnl, 0) as total_pnl
FROM runs r
LEFT JOIN (
    SELECT run_id, COUNT(*) as count 
    FROM signals 
    GROUP BY run_id
) signal_count ON r.run_id = signal_count.run_id
LEFT JOIN (
    SELECT run_id, COUNT(*) as count 
    FROM orders 
    GROUP BY run_id
) order_count ON r.run_id = order_count.run_id
LEFT JOIN (
    SELECT run_id, COUNT(*) as count 
    FROM positions 
    WHERE quantity != 0
    GROUP BY run_id
) position_count ON r.run_id = position_count.run_id
LEFT JOIN (
    SELECT run_id, COUNT(*) as count 
    FROM executions 
    GROUP BY run_id
) execution_count ON r.run_id = execution_count.run_id
LEFT JOIN (
    SELECT run_id, SUM(realized_pnl) as pnl 
    FROM positions 
    GROUP BY run_id
) total_pnl ON r.run_id = total_pnl.run_id;

-- ==============================================
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ==============================================

-- Вставка примера запуска
INSERT INTO runs (strategy_name, mode, status, note, config) 
VALUES (
    'trend_following',
    'paper',
    'init',
    'Пример запуска стратегии',
    '{"symbols": ["EURUSD", "GBPUSD"], "timeframes": ["1h", "4h"]}'
) ON CONFLICT DO NOTHING;

-- ==============================================
-- ПРАВА ДОСТУПА
-- ==============================================

-- Создание пользователя для чтения
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_readonly') THEN
        CREATE ROLE trading_readonly;
    END IF;
END
$$;

-- Предоставление прав на чтение
GRANT CONNECT ON DATABASE trading_agent TO trading_readonly;
GRANT USAGE ON SCHEMA public TO trading_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO trading_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO trading_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO trading_readonly;
