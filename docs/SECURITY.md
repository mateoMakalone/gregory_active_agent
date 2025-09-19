# 🔒 Система безопасности торгового AI-агента

## 📋 Обзор

Система безопасности включает в себя:
- **Веб-хук аутентификация** - проверка подписей и IP адресов
- **Rate Limiting** - ограничение частоты запросов
- **Backpressure** - защита от перегрузки системы
- **Retry политики** - повторные попытки с идемпотентностью
- **Circuit Breaker** - защита от каскадных сбоев

## 🔐 Веб-хук аутентификация

### Подпись запросов

Все входящие веб-хуки должны содержать:
- `X-Signature-256` - HMAC-SHA256 подпись
- `X-Timestamp` - Unix timestamp запроса

```python
# Создание подписи
import hmac
import hashlib
import time

def create_signature(payload: str, secret: str) -> str:
    timestamp = str(int(time.time()))
    message = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"
```

### Проверка IP адресов

```yaml
security:
  webhook:
    allowed_ips:
      - "127.0.0.1"           # localhost
      - "172.16.0.0/12"       # Docker networks
      - "10.0.0.0/8"          # Private networks
    max_timestamp_diff: 300   # 5 минут
```

### Использование

```python
from src.security.webhook_auth import require_webhook_auth

@require_webhook_auth
async def webhook_handler(request, payload, headers, client_ip):
    # Обработка веб-хука
    pass
```

## ⚡ Rate Limiting

### Стратегии

1. **Token Bucket** - классический алгоритм с токенами
2. **Sliding Window** - скользящее окно запросов
3. **Fixed Window** - фиксированное окно

### Конфигурация

```yaml
security:
  rate_limit:
    max_requests: 100        # Максимум запросов
    window_seconds: 3600     # Окно в секундах (1 час)
    burst_limit: 10          # Burst лимит
    burst_window: 60         # Burst окно (1 минута)
```

### Использование

```python
from src.security.rate_limiter import rate_limit

@rate_limit(requests_per_second=10.0)
async def api_endpoint():
    # Обработка запроса
    pass
```

## 🛡️ Backpressure

### Защита от перегрузки

```yaml
security:
  backpressure:
    max_queue_size: 1000           # Максимальный размер очереди
    queue_full_threshold: 0.8      # Порог перегрузки (80%)
    delay: 0.1                     # Задержка при перегрузке
```

### Использование

```python
from src.security.rate_limiter import backpressure_protection

@backpressure_protection(max_queue_size=500)
async def processing_function():
    # Обработка с защитой от перегрузки
    pass
```

## 🔄 Retry политики

### Стратегии повторных попыток

1. **FIXED** - фиксированная задержка
2. **EXPONENTIAL** - экспоненциальная задержка
3. **LINEAR** - линейная задержка
4. **CUSTOM** - пользовательская стратегия

### Конфигурация

```yaml
security:
  retry:
    max_attempts: 3          # Максимум попыток
    base_delay: 1.0          # Базовая задержка (сек)
    max_delay: 300.0         # Максимальная задержка (сек)
    backoff_factor: 2.0      # Коэффициент увеличения
    strategy: "exponential"  # Стратегия
    jitter: true             # Добавлять случайность
```

### Идемпотентность

```python
from src.security.retry_policy import retry_manager

# Выполнение с retry и идемпотентностью
result = await retry_manager.execute_with_retry(
    func=my_function,
    execution_id="unique_id",
    params={"param": "value"},
    idempotent=True  # Результат кэшируется
)
```

## ⚡ Circuit Breaker

### Защита от каскадных сбоев

```python
from src.security.retry_policy import circuit_breaker

# Выполнение через circuit breaker
try:
    result = await circuit_breaker.call(my_function)
except Exception as e:
    if "Circuit breaker is OPEN" in str(e):
        # Система перегружена, ждем восстановления
        pass
```

### Состояния

- **CLOSED** - нормальная работа
- **OPEN** - блокировка запросов
- **HALF_OPEN** - тестирование восстановления

## 🚀 API сервер

### Запуск

```bash
# Запуск безопасного API сервера
make run-api

# Или напрямую
python scripts/run_api.py
```

### Endpoints

#### Веб-хуки
- `POST /webhook/n8n` - n8n интеграция
- `POST /webhook/external` - внешние веб-хуки

#### Торговля
- `POST /signals` - создание сигналов
- `GET /signals` - получение сигналов
- `GET /positions` - получение позиций

#### Оркестрация
- `POST /runs` - создание запусков
- `GET /metrics` - метрики системы

#### Мониторинг
- `GET /health` - проверка здоровья

### Пример запроса

```bash
# Создание сигнала
curl -X POST "http://localhost:8000/signals" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "eurusd_mtf",
    "symbol": "EURUSD",
    "timeframe": "1h",
    "signal_type": "BUY",
    "strength": "MEDIUM",
    "price": 1.1000,
    "confidence": 0.75
  }'
```

### Пример веб-хука

```bash
# n8n webhook
curl -X POST "http://localhost:8000/webhook/n8n" \
  -H "Content-Type: application/json" \
  -H "X-Signature-256: sha256=..." \
  -H "X-Timestamp: 1234567890" \
  -d '{
    "type": "strategy_trigger",
    "execution_id": "run_123",
    "data": {...}
  }'
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Тестирование системы безопасности
make test-security

# Или напрямую
python scripts/test_security.py
```

### Тесты включают

1. **Веб-хук аутентификация**
   - Валидные подписи
   - Невалидные подписи
   - Проверка IP адресов

2. **Rate Limiting**
   - Превышение лимитов
   - Burst защита

3. **Backpressure**
   - Перегрузка системы
   - Защита очереди

4. **Retry политики**
   - Повторные попытки
   - Идемпотентность

5. **Circuit Breaker**
   - Открытие при сбоях
   - Восстановление

## 📊 Мониторинг

### Метрики безопасности

```python
# Получение метрик
GET /metrics

{
  "metrics": {...},
  "queue_status": {
    "current_size": 10,
    "max_size": 1000,
    "utilization": 0.01,
    "is_full": false
  },
  "rate_limiter_status": {
    "enabled": true,
    "buckets_count": 5
  }
}
```

### Логирование

Все события безопасности логируются:
- Неудачные аутентификации
- Превышения rate limit
- Срабатывания backpressure
- Retry попытки
- Circuit breaker состояния

## 🔧 Конфигурация

### Полная конфигурация безопасности

```yaml
security:
  webhook:
    secret_key: "your_webhook_secret_key_change_me"
    allowed_ips: 
      - "127.0.0.1"
      - "172.16.0.0/12"
    max_timestamp_diff: 300
  
  rate_limit:
    max_requests: 100
    window_seconds: 3600
    burst_limit: 10
    burst_window: 60
  
  retry:
    max_attempts: 3
    base_delay: 1.0
    max_delay: 300.0
    backoff_factor: 2.0
    strategy: "exponential"
    jitter: true
  
  idempotency:
    cache_ttl: 3600
    max_cache_size: 10000
  
  backpressure:
    max_queue_size: 1000
    queue_full_threshold: 0.8
    delay: 0.1

api:
  host: "0.0.0.0"
  port: 8000
  docs_enabled: true
  cors:
    allow_origins: ["*"]
  trusted_hosts: ["*"]
```

## 🚨 Рекомендации по безопасности

### 1. Веб-хуки
- Используйте сильные секретные ключи
- Ограничивайте IP адреса
- Проверяйте временные метки
- Логируйте все попытки доступа

### 2. Rate Limiting
- Настройте разумные лимиты
- Мониторьте превышения
- Используйте burst лимиты
- Настройте разные лимиты для разных endpoints

### 3. Backpressure
- Мониторьте размер очереди
- Настройте алерты при перегрузке
- Используйте graceful degradation

### 4. Retry
- Не retry для идемпотентных операций
- Используйте экспоненциальный backoff
- Ограничивайте количество попыток
- Логируйте все retry попытки

### 5. Circuit Breaker
- Настройте разумные пороги
- Мониторьте состояния
- Используйте fallback стратегии

## 📚 Дополнительные ресурсы

- [OWASP Webhook Security](https://owasp.org/www-community/attacks/Webhook_Attacks)
- [Rate Limiting Best Practices](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Idempotency Keys](https://stripe.com/docs/api/idempotent_requests)
