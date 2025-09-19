# 🗄️ База данных торгового AI-агента

## 📋 Обзор

Система поддерживает две базы данных:
- **SQLite** - для локальной разработки и совместимости
- **PostgreSQL** - для продакшена и оркестрации

## 🏗️ Архитектура

### Основные таблицы

#### 1. **strategies** - Торговые стратегии
```sql
- id (VARCHAR) - Уникальный ID стратегии
- name (VARCHAR) - Название стратегии
- type (VARCHAR) - Тип стратегии (trend_following, momentum, etc.)
- active (BOOLEAN) - Активна ли стратегия
- quality_thresholds (JSONB) - Пороги качества
- risk_limits (JSONB) - Лимиты риска
```

#### 2. **models** - Модели машинного обучения
```sql
- model_id (VARCHAR) - Уникальный ID модели
- strategy_id (VARCHAR) - Связь со стратегией
- version (INTEGER) - Версия модели
- type (VARCHAR) - Тип модели (xgboost, lightgbm, etc.)
- metrics (JSONB) - Метрики модели
- promoted (BOOLEAN) - Продвинута ли модель
```

#### 3. **signals** - Торговые сигналы
```sql
- signal_id (VARCHAR) - Уникальный ID сигнала
- strategy_id (VARCHAR) - Связь со стратегией
- symbol (VARCHAR) - Торговый символ
- signal_type (VARCHAR) - Тип сигнала (BUY, SELL, HOLD)
- strength (VARCHAR) - Сила сигнала (WEAK, MEDIUM, STRONG)
- price (DECIMAL) - Цена сигнала
- confidence (DECIMAL) - Уверенность в сигнале
- stop_loss (DECIMAL) - Стоп-лосс
- take_profit (DECIMAL) - Тейк-профит
```

#### 4. **positions** - Торговые позиции
```sql
- position_id (VARCHAR) - Уникальный ID позиции
- signal_id (VARCHAR) - Связь с сигналом
- symbol (VARCHAR) - Торговый символ
- side (VARCHAR) - Сторона позиции (LONG, SHORT)
- size (DECIMAL) - Размер позиции
- entry_price (DECIMAL) - Цена входа
- current_price (DECIMAL) - Текущая цена
- unrealized_pnl (DECIMAL) - Нереализованный PnL
- realized_pnl (DECIMAL) - Реализованный PnL
```

#### 5. **orders** - Торговые ордера
```sql
- order_id (VARCHAR) - Уникальный ID ордера
- position_id (VARCHAR) - Связь с позицией
- symbol (VARCHAR) - Торговый символ
- side (VARCHAR) - Сторона ордера (BUY, SELL)
- type (VARCHAR) - Тип ордера (MARKET, LIMIT, STOP)
- size (DECIMAL) - Размер ордера
- price (DECIMAL) - Цена ордера
- status (VARCHAR) - Статус ордера
- filled_size (DECIMAL) - Исполненный размер
- filled_price (DECIMAL) - Цена исполнения
```

### Таблицы оркестрации

#### 6. **runs** - Запуски оркестрации
```sql
- run_id (VARCHAR) - Уникальный ID запуска
- strategy_id (VARCHAR) - Связь со стратегией
- stage (VARCHAR) - Этап запуска (ingest, train, backtest, execute)
- status (VARCHAR) - Статус запуска
- progress (DECIMAL) - Прогресс выполнения (0-100)
- started_at (TIMESTAMP) - Время начала
- ended_at (TIMESTAMP) - Время окончания
```

#### 7. **jobs** - Задания
```sql
- job_id (VARCHAR) - Уникальный ID задания
- run_id (VARCHAR) - Связь с запуском
- job_type (VARCHAR) - Тип задания
- status (VARCHAR) - Статус задания
- priority (INTEGER) - Приоритет
- parameters (JSONB) - Параметры задания
- results (JSONB) - Результаты задания
```

#### 8. **executions** - Выполнения
```sql
- execution_id (VARCHAR) - Уникальный ID выполнения
- job_id (VARCHAR) - Связь с заданием
- step_name (VARCHAR) - Название шага
- status (VARCHAR) - Статус выполнения
- duration_ms (INTEGER) - Длительность в мс
- memory_used_mb (INTEGER) - Использованная память
- cpu_usage_percent (DECIMAL) - Использование CPU
```

### Таблицы мониторинга

#### 9. **live_metrics** - Живые метрики
```sql
- id (SERIAL) - Автоинкремент ID
- strategy_id (VARCHAR) - Связь со стратегией
- timestamp (TIMESTAMP) - Время метрики
- sharpe_ratio (DECIMAL) - Коэффициент Шарпа
- max_drawdown (DECIMAL) - Максимальная просадка
- win_rate (DECIMAL) - Процент выигрышных сделок
- pnl_daily (DECIMAL) - Дневная прибыль
- latency_ms (INTEGER) - Задержка в мс
```

#### 10. **alerts** - Алерты
```sql
- alert_id (VARCHAR) - Уникальный ID алерта
- strategy_id (VARCHAR) - Связь со стратегией
- alert_type (VARCHAR) - Тип алерта
- severity (VARCHAR) - Серьезность (LOW, MEDIUM, HIGH, CRITICAL)
- title (VARCHAR) - Заголовок
- message (TEXT) - Сообщение
- status (VARCHAR) - Статус алерта
```

## 🚀 Использование

### Инициализация

```bash
# Инициализация базы данных
make init-db

# Или напрямую
python scripts/init_db.py
```

### Программное использование

```python
from src.database.services import SignalService, PositionService
from src.database.models import SignalType, SignalStrength, PositionSide

# Создание сигнала
signal = await SignalService.create_signal(
    strategy_id="eurusd_mtf",
    symbol="EURUSD",
    timeframe="1h",
    signal_type=SignalType.BUY,
    strength=SignalStrength.MEDIUM,
    price=1.1000,
    confidence=0.75
)

# Создание позиции
position = await PositionService.create_position(
    strategy_id="eurusd_mtf",
    symbol="EURUSD",
    side=PositionSide.LONG,
    size=0.01,
    entry_price=1.1000,
    signal_id=signal.signal_id
)

# Получение статистики
stats = await SignalService.get_signal_stats("eurusd_mtf")
print(f"Всего сигналов: {stats['total_signals']}")
```

## 🔧 Конфигурация

### SQLite (по умолчанию)
```yaml
database:
  type: "sqlite"
  url: "sqlite:///data/trading_agent.db"
```

### PostgreSQL
```yaml
database:
  type: "postgresql"
  url: "postgresql://user:password@localhost:5432/trading_agent"
  host: "localhost"
  port: 5432
  name: "trading_agent"
  user: "postgres"
  password: "password"
```

## 📊 Индексы

Система автоматически создает индексы для оптимизации:

- `idx_runs_strategy_status` - Запуски по стратегии и статусу
- `idx_signals_strategy_symbol` - Сигналы по стратегии и символу
- `idx_positions_strategy` - Позиции по стратегии
- `idx_orders_status` - Ордера по статусу
- `idx_live_metrics_timestamp` - Метрики по времени

## 🔄 Миграции

### SQLite
Схема автоматически создается при первом запуске из файла `ops/sql/sqlite_schema.sql`.

### PostgreSQL
Схема создается из файла `ops/sql/init.sql` при инициализации контейнера.

## 📈 Мониторинг

### Живые метрики
```python
from src.database.services import MetricsService

# Запись метрик
await MetricsService.record_live_metrics(
    strategy_id="eurusd_mtf",
    sharpe_ratio=1.5,
    max_drawdown=0.1,
    win_rate=0.65,
    pnl_daily=150.0
)

# Получение последних метрик
metrics = await MetricsService.get_latest_metrics("eurusd_mtf")
```

### Алерты
```python
from src.database.services import AlertService

# Создание алерта
await AlertService.create_alert(
    strategy_id="eurusd_mtf",
    alert_type="performance",
    severity="HIGH",
    title="Высокая просадка",
    message="Просадка превысила 15%"
)
```

## 🛠️ Разработка

### Добавление новых таблиц
1. Добавьте SQL в `ops/sql/init.sql` (PostgreSQL)
2. Добавьте SQL в `ops/sql/sqlite_schema.sql` (SQLite)
3. Создайте модель в `src/database/models.py`
4. Создайте сервис в `src/database/services.py`

### Тестирование
```bash
# Тест подключения
python -c "from src.database.connection import db_manager; import asyncio; asyncio.run(db_manager.connect())"

# Тест создания данных
python scripts/init_db.py
```

## 🔒 Безопасность

- Все пароли хранятся в конфигурации
- Используются параметризованные запросы
- Создан пользователь только для чтения
- Логирование всех операций

## 📚 Дополнительные ресурсы

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
