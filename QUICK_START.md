# 🚀 Gregory Trading Agent - Быстрый старт

## ⚡ Одна команда для запуска всего

```bash
make start
```

Или напрямую:
```bash
./start_all.sh
```

## 🛠️ Основные команды

| Команда | Описание |
|---------|----------|
| `make start` | 🚀 Запустить всю систему |
| `make stop` | 🛑 Остановить все компоненты |
| `make status` | 📊 Показать статус системы |
| `make help` | 📖 Показать все команды |

## 📋 Что запускается

1. **Проверка зависимостей** - Python, pip пакеты, PostgreSQL, Redis
2. **Запуск сервисов** - PostgreSQL и Redis через brew
3. **Настройка БД** - создание и применение схемы
4. **Запуск компонентов**:
   - 🔧 **API Server** (порт 8000) - FastAPI для n8n интеграции
   - 📊 **Dashboard** (порт 8501) - Streamlit интерфейс
   - 📱 **Telegram Bot** - уведомления и управление

## 🌐 Доступные интерфейсы

После запуска будут доступны:

- **Dashboard**: http://127.0.0.1:8501
- **API Server**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs

## 📝 Логи

Все логи сохраняются в папку `logs/`:
- `logs/api.log` - API сервер
- `logs/dashboard.log` - Dashboard
- `logs/bot.log` - Telegram бот

Просмотр логов:
```bash
tail -f logs/api.log
tail -f logs/dashboard.log
tail -f logs/bot.log
```

## 🔧 Устранение проблем

### Если что-то не работает:

1. **Проверить статус**:
   ```bash
   make status
   ```

2. **Остановить и перезапустить**:
   ```bash
   make stop
   make start
   ```

3. **Проверить логи**:
   ```bash
   tail -f logs/dashboard.log
   ```

4. **Очистить порты** (если заняты):
   ```bash
   lsof -ti:8501 | xargs kill -9
   lsof -ti:8000 | xargs kill -9
   ```

### Если нужны только сервисы:

```bash
# Запустить только PostgreSQL и Redis
make local-services

# Настроить только БД
make local-setup

# Запустить только dashboard
make local-dashboard

# Запустить только API
make local-api
```

## 🐳 Docker (альтернатива)

Если предпочитаете Docker:

```bash
# Установить Docker Desktop
brew install --cask docker

# Запустить через Docker
make docker-up

# Остановить
make docker-down
```

## 📚 Дополнительная документация

- **Полная документация**: `README.md`
- **Оркестрация n8n**: `ORCHESTRATION_QUICKSTART.md`
- **Настройка**: `SETUP.md`
- **Улучшения**: `IMPROVEMENTS.md`

---

**🎯 Готово! Система запущена и готова к работе!**
