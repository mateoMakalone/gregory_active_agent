# Gregory Trading Agent - n8n Orchestration

Эта папка содержит конфигурации для оркестрации Gregory Trading Agent через n8n.

## Структура

```
ops/
├── sql/
│   └── init.sql          # PostgreSQL схема
├── n8n/
│   ├── nightly-retrain.json    # Ежедневное переобучение
│   ├── metrics-guard.json      # Мониторинг метрик
│   ├── run-strategy.json       # Запуск стратегий
│   └── upload-deploy.json      # Загрузка и деплой (TODO)
└── README.md
```

## Воркфлоу

### 1. Nightly Retrain (`nightly-retrain.json`)
**Триггер:** Cron каждый день в 2:00 UTC  
**Функции:**
- Сбор свежих данных (`/ingest`)
- Обучение модели (`/train`) 
- Бэктестинг (`/backtest`)
- Проверка качества (Sharpe > 1.2, MaxDD < 15%)
- Активация модели (`/promote`) при прохождении проверки
- Уведомления в Telegram

### 2. Metrics Guard (`metrics-guard.json`)
**Триггер:** Cron каждые 5 минут  
**Функции:**
- Проверка живых метрик (`/metrics`)
- Сравнение с порогами качества
- Алерты при превышении порогов
- Emergency stop при критических нарушениях

### 3. Run Strategy (`run-strategy.json`)
**Триггер:** Webhook `POST /webhook/run-strategy`  
**Функции:**
- Подготовка окружения (`/prepare`)
- Запуск стратегии (`/execute`)
- Мониторинг выполнения
- Уведомления о результатах

### 4. Upload & Deploy (TODO)
**Триггер:** Webhook с файлом стратегии  
**Функции:**
- Валидация `manifest.yaml`
- Регистрация в БД (`/register`)
- Автоматический retrain при `auto_retrain=true`

## Установка и настройка

### 1. Запуск инфраструктуры
```bash
# Скопировать переменные окружения
cp env.example .env
# Отредактировать .env с вашими значениями

# Запуск всех сервисов
docker-compose up -d
```

### 2. Доступ к n8n
- URL: http://localhost:5678
- Login: admin (или из `N8N_USER`)
- Password: n8n_secret (или из `N8N_PASSWORD`)

### 3. Импорт воркфлоу
1. Зайти в n8n UI
2. Settings > Import/Export
3. Импортировать JSON файлы из папки `ops/n8n/`

### 4. Настройка Credentials
Создать в n8n:
- **HTTP Basic Auth** для Gregory API
- **Webhook Authentication** (если нужен)

## API Endpoints

Gregory API (`http://gregory-api:8000`):

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/ingest` | POST | Сбор данных |
| `/train` | POST | Обучение модели |
| `/backtest` | POST | Бэктестинг |
| `/promote` | POST | Активация модели |
| `/prepare` | POST | Подготовка окружения |
| `/execute` | POST | Запуск стратегии |
| `/status/{run_id}` | GET | Статус выполнения |
| `/metrics` | GET | Живые метрики |
| `/notify` | POST | Отправка уведомлений |
| `/health` | GET | Проверка здоровья |

## Webhook Endpoints

n8n webhooks (`http://localhost:5678/webhook/`):

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/run-strategy` | POST | Запуск стратегии |
| `/upload-strategy` | POST | Загрузка стратегии (TODO) |

### Пример запроса запуска стратегии:
```bash
curl -X POST http://localhost:5678/webhook/run-strategy \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "eurusd_mtf",
    "mode": "paper",
    "params": {
      "timeframe": "4h",
      "risk_factor": 0.02
    }
  }'
```

## Мониторинг

### PostgreSQL таблицы
- `runs` - история всех запусков
- `strategies` - зарегистрированные стратегии  
- `models` - обученные модели
- `failed_jobs` - неудачные выполнения
- `live_metrics` - текущие метрики

### Логи
- n8n: docker logs gregory-n8n
- Gregory API: docker logs gregory-api
- PostgreSQL: docker logs gregory-postgres

### Дашборд
- Streamlit: http://localhost:8501
- n8n UI: http://localhost:5678

## Troubleshooting

### Проблемы с подключением
```bash
# Проверить статус сервисов
docker-compose ps

# Проверить логи
docker-compose logs gregory-api
docker-compose logs gregory-n8n

# Проверить здоровье API
curl http://localhost:8000/health
```

### Проблемы с воркфлоу
1. Проверить статус выполнения в n8n UI
2. Посмотреть логи выполнения
3. Проверить настройки Credentials
4. Убедиться что Gregory API доступен

### Проблемы с БД
```bash
# Подключиться к PostgreSQL
docker exec -it gregory-postgres psql -U gregory -d gregory_orchestration

# Проверить таблицы
\dt

# Проверить последние запуски
SELECT * FROM runs ORDER BY started_at DESC LIMIT 10;
```

## Безопасность

1. **Смените пароли** в `.env` файле
2. **Настройте firewall** для портов 5432, 5678, 8000
3. **Используйте HTTPS** в продакшене
4. **Ротируйте webhook secrets** регулярно
5. **Ограничьте доступ** к n8n UI по IP

## Масштабирование

### Увеличение производительности
- Добавить n8n workers: `docker-compose scale n8n=3`
- Настроить Redis Cluster для queue
- Использовать PostgreSQL master-slave

### Мониторинг в продакшене
- Prometheus + Grafana для метрик
- ELK Stack для логов
- Alertmanager для критических алертов

