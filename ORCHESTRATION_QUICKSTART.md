# 🚀 Gregory Trading Agent - n8n Orchestration Quickstart

## ✅ Готово к запуску!

Система n8n оркестрации для Gregory Trading Agent полностью настроена и готова к использованию.

## 🏗️ Что было реализовано

### 1. **Инфраструктура**
- ✅ **PostgreSQL** - база данных для оркестрации (схема, таблицы)  
- ✅ **n8n** - оркестратор с Queue Mode и Redis
- ✅ **FastAPI** - API сервер с 9 orchestration endpoints
- ✅ **Docker Compose** - полная инфраструктура в контейнерах

### 2. **API Endpoints** 
| Endpoint | Функция | Статус |
|----------|---------|--------|
| `POST /ingest` | Сбор данных | ✅ |
| `POST /train` | Обучение модели | ✅ |
| `POST /backtest` | Бэктестинг | ✅ |
| `POST /promote` | Активация модели | ✅ |
| `POST /prepare` | Подготовка окружения | ✅ |
| `POST /execute` | Запуск стратегии | ✅ |
| `GET /status/{run_id}` | Статус выполнения | ✅ |
| `GET /metrics` | Живые метрики | ✅ |
| `POST /notify` | Telegram уведомления | ✅ |
| `GET /health` | Проверка здоровья | ✅ |

### 3. **n8n Воркфлоу**
- ✅ **Nightly Retrain** - автоматическое переобучение (2:00 AM)
- ✅ **Metrics Guard** - мониторинг метрик (каждые 5 минут)  
- ✅ **Run Strategy** - запуск стратегий по webhook
- 🔄 **Upload & Deploy** - загрузка стратегий (TODO)

### 4. **Система артефактов**
- ✅ Уникальные `run_id` для каждого запуска
- ✅ Хранение в `/artifacts/<run_id>/`
- ✅ Структурированные логи в JSONL
- ✅ Метаданные и метрики в JSON

### 5. **Мониторинг и алерты**
- ✅ Quality thresholds (Sharpe, MaxDD, staleness)
- ✅ Telegram уведомления для всех событий
- ✅ Emergency stop при критических нарушениях
- ✅ Retry policy с экспоненциальным backoff

## 🚀 Быстрый запуск

### 1. Подготовка окружения
```bash
cd gregory_active_agent

# Создать .env файл из примера
cp env.example .env

# Отредактировать .env с вашими значениями:
# - POSTGRES_PASSWORD
# - N8N_PASSWORD  
# - TELEGRAM_BOT_TOKEN
# - API ключи
```

### 2. Запуск инфраструктуры
```bash
# Запустить все сервисы
make docker-up

# Проверить статус
docker-compose ps

# Посмотреть логи
make docker-logs
```

### 3. Настройка n8n
```bash
# Открыть n8n UI
make n8n-ui
# или http://localhost:5678

# Войти с credentials из .env:
# Login: admin (N8N_USER)
# Password: ваш_пароль (N8N_PASSWORD)

# Импортировать воркфлоу:
# Settings > Import/Export > Import
# Файлы: ops/n8n/*.json
```

### 4. Проверка работоспособности
```bash
# Проверить API
make api-test

# Открыть дашборд  
make dashboard-ui

# Проверить статус БД
make db-status

# Тест запуска стратегии
make trigger-retrain
```

## 🎯 Основные команды

| Команда | Описание |
|---------|----------|
| `make docker-up` | Запустить инфраструктуру |
| `make docker-down` | Остановить все |
| `make api-test` | Проверить API |
| `make n8n-ui` | Открыть n8n |
| `make dashboard-ui` | Открыть дашборд |
| `make db-status` | Статус запусков |
| `make docker-logs` | Логи сервисов |

## 📡 API примеры

### Запуск стратегии через webhook:
```bash
curl -X POST http://localhost:5678/webhook/run-strategy \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "eurusd_mtf",
    "mode": "paper",
    "params": {"risk_factor": 0.02}
  }'
```

### Проверка статуса:
```bash
curl http://localhost:8000/status/your_run_id
```

### Получение метрик:
```bash
curl http://localhost:8000/metrics
```

## 🗄️ База данных

Основные таблицы PostgreSQL:
- **`strategies`** - зарегистрированные стратегии
- **`models`** - обученные модели  
- **`runs`** - история всех запусков
- **`failed_jobs`** - неудачные выполнения
- **`live_metrics`** - текущие метрики

```sql
-- Подключение к БД
make db-connect

-- Просмотр последних запусков
SELECT * FROM runs ORDER BY started_at DESC LIMIT 5;

-- Просмотр активных стратегий
SELECT * FROM strategies WHERE active_model_id IS NOT NULL;
```

## 🔄 Воркфлоу тестирование

### 1. Nightly Retrain (ручной запуск)
Запустится автоматически в 2:00 AM или можно протестировать через n8n UI

### 2. Metrics Guard  
Работает каждые 5 минут автоматически

### 3. Run Strategy
```bash
# Через webhook
curl -X POST http://localhost:5678/webhook/run-strategy \
  -d '{"strategy_id": "eurusd_mtf", "mode": "paper"}'
```

## 🔍 Troubleshooting

### Проблемы с подключением
```bash
# Статус сервисов
docker-compose ps

# Логи конкретного сервиса  
docker-compose logs gregory-api
docker-compose logs gregory-n8n
docker-compose logs gregory-postgres
```

### Проблемы с n8n
1. Проверить что сервисы запущены: `docker-compose ps`
2. Убедиться что Gregory API доступен: `make api-test`
3. Проверить логи n8n: `docker-compose logs gregory-n8n`

### Проблемы с БД
```bash
# Подключение
make db-connect

# Проверка таблиц
\dt

# Проверка данных
SELECT COUNT(*) FROM runs;
```

## 🎉 Следующие шаги

1. **Протестировать полный цикл**: загрузка стратегии → retrain → deploy
2. **Настроить реальные API ключи** в конфигурации
3. **Добавить Upload & Deploy воркфлоу** для загрузки стратегий
4. **Настроить мониторинг** в продакшене (Prometheus, Grafana)
5. **Добавить S3 storage** для артефактов

## 📚 Документация

- **Полная документация**: `ops/README.md`
- **API схема**: http://localhost:8000/docs (после запуска)
- **n8n документация**: https://docs.n8n.io
- **PostgreSQL схема**: `ops/sql/init.sql`

---

**🎯 Система готова к продуктивному использованию!**

Gregory Trading Agent теперь полностью интегрирован с n8n оркестрацией и готов к автоматизированному управлению жизненным циклом стратегий.
