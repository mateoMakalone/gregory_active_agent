# 🔄 Проблема с Event Loop в API сервере

## 📋 Описание проблемы

API сервер падает с ошибкой:
```
❌ Ошибка запуска API v2 сервера: asyncio.run() cannot be called from a running event loop
```

## 🔍 Анализ проблемы

### Что происходит:
1. **API сервер запускается** - инициализация проходит успешно
2. **База данных подключается** - SQLite схема создается
3. **Конфигурация загружается** - все настройки читаются
4. **При запуске uvicorn** - возникает конфликт event loops

### Техническая суть:
- Где-то в коде уже запущен event loop
- `asyncio.run()` не может быть вызван из уже запущенного event loop
- uvicorn сам управляет event loop'ом

## 🛠️ Что уже исправлено

### 1. Заменены проблемные вызовы:
```python
# Было:
loop = asyncio.get_event_loop()

# Стало:
loop = asyncio.get_running_loop()
```

**Файлы:**
- `src/database/connection.py` (5 мест)
- `src/main.py` (2 места)

### 2. Добавлен nest_asyncio:
```python
# В scripts/run_api_v2.py
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass
```

### 3. Исправлена SQL схема PostgreSQL:
- Проблема с `run_statistics` view (неполные имена таблиц в подзапросах)

## 🔍 Где искать проблему

### 1. Проверить импорты в startup:
```python
# В scripts/run_api_v2.py
from src.api.v2.server import api_server_v2  # ← Возможно здесь
from src.core.config import config
from src.database.connection import db_manager
```

### 2. Проверить инициализацию модулей:
- `src/api/v2/server.py` - инициализация FastAPI
- `src/database/connection.py` - подключение к БД
- `src/core/config.py` - загрузка конфигурации

### 3. Возможные места проблемы:
- Автоматический запуск event loop в импортах
- Глобальные переменные с asyncio
- Middleware или startup events в FastAPI

## 🧪 Способы отладки

### 1. Проверить, где запускается event loop:
```python
import asyncio
import inspect

def check_event_loop():
    try:
        loop = asyncio.get_running_loop()
        print(f"Event loop уже запущен: {loop}")
        print(f"Стек вызовов: {inspect.stack()}")
    except RuntimeError:
        print("Event loop не запущен")
```

### 2. Добавить отладочную информацию:
```python
# В scripts/run_api_v2.py перед uvicorn.run()
print(f"Event loop status: {asyncio.get_event_loop().is_running()}")
```

### 3. Проверить все asyncio.run() в коде:
```bash
grep -r "asyncio.run" src/ scripts/ --include="*.py"
```

## 💡 Возможные решения

### 1. Полностью убрать asyncio.run():
```python
# Вместо asyncio.run(main())
# Использовать прямой запуск uvicorn
uvicorn.run(app, host=host, port=port)
```

### 2. Использовать startup/shutdown events:
```python
# В FastAPI app
@app.on_event("startup")
async def startup():
    await db_manager.connect()

@app.on_event("shutdown") 
async def shutdown():
    await db_manager.disconnect()
```

### 3. Переписать на синхронную инициализацию:
```python
# Инициализировать БД синхронно
# Запустить uvicorn без asyncio
```

## 📊 Текущий статус

- ✅ **PostgreSQL**: работает и инициализируется
- ✅ **Redis**: работает корректно  
- ✅ **Docker**: образы собираются
- ✅ **SQLite**: схема создается
- ❌ **API сервер**: падает на startup

## 🎯 Следующие шаги

1. **Найти root cause** - где именно запускается event loop
2. **Переписать startup логику** - убрать конфликтующие asyncio.run()
3. **Протестировать** - убедиться, что API отвечает на запросы
4. **Запустить остальные сервисы** - dashboard, bot, strategy runner

## 📝 Полезные команды

```bash
# Запуск только инфраструктуры
docker-compose -f docker-compose.v2.yml up postgres redis -d

# Проверка логов API
docker-compose -f docker-compose.v2.yml logs api

# Тест API (когда заработает)
curl http://localhost:8000/healthz
curl http://localhost:8000/docs
```

---
*Проблема требует детального анализа startup процесса и возможной рефакторинга инициализации.*
