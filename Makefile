# Trading AI Agent - Makefile

.PHONY: help install run test clean docker-build docker-run

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	python3 -m pip install -r requirements.txt

run: ## Запустить систему (синхронная версия)
	python3 -m src.main

run-async: ## Запустить систему (асинхронная версия)
	python3 run_async.py

run-dashboard: ## Запустить только дашборд
	streamlit run app/dashboard.py

run-bot: ## Запустить только Telegram-бота
	python3 run_bot.py

run-bot-async: ## Запустить асинхронный Telegram-бот
	python3 -c "import asyncio; from telegram_bot.async_bot import async_telegram_bot; asyncio.run(async_telegram_bot.test_connection())"

run-all: ## Запустить все компоненты (legacy)
	python3 run_all.py

run-example: ## Запустить пример
	python3 run_example.py

# Quick start commands
start: ## 🚀 Запустить всю систему одной командой
	./start_all.sh

stop: ## 🛑 Остановить всю систему
	./stop_all.sh

status: ## 📊 Показать статус всех компонентов
	./status.sh

# n8n controls
n8n-start: ## Запустить только n8n (Docker требуется)
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Docker не установлен. Установите Docker Desktop и повторите."; \
		exit 1; \
	fi
	@if ! docker ps >/dev/null 2>&1; then \
		echo "Docker не запущен. Откройте Docker Desktop и повторите."; \
		exit 1; \
	fi
	docker compose up -d n8n redis postgres
	@echo "Откройте n8n UI: http://localhost:5678"

n8n-stop: ## Остановить n8n и его зависимости
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Docker не установлен."; exit 0; \
	fi
	docker compose stop n8n

n8n-down: ## Полностью остановить и удалить n8n+deps контейнеры
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Docker не установлен."; exit 0; \
	fi
	docker compose down

# Local commands (без Docker)
local-services: ## Запустить локальные сервисы (PostgreSQL, Redis)
	brew services start postgresql@14
	brew services start redis

local-stop: ## Остановить локальные сервисы
	brew services stop postgresql@14  
	brew services stop redis

local-setup: ## Настроить локальную БД
	createdb gregory_orchestration || echo "БД уже существует"
	psql gregory_orchestration < ops/sql/init.sql || echo "Схема уже применена"

local-dashboard: ## Запустить dashboard локально (FastAPI)
	python3 -m uvicorn app.dashboard_fastapi:app --host 127.0.0.1 --port 8501

local-dashboard-streamlit: ## Запустить dashboard на Streamlit (если работает)
	python3 -m streamlit run app/dashboard.py --server.port=8501 --server.address=127.0.0.1

local-api: ## Запустить API сервер локально  
	python3 -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload

# Orchestration commands (Docker)
docker-up: ## Запустить инфраструктуру с n8n
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Docker не установлен. Установите Docker Desktop и повторите."; \
		exit 1; \
	fi
	@if ! docker ps >/dev/null 2>&1; then \
		echo "Docker не запущен. Откройте Docker Desktop и повторите."; \
		exit 1; \
	fi
	docker compose up -d

docker-down: ## Остановить инфраструктуру
	@if command -v docker >/dev/null 2>&1; then docker compose down; else echo "Docker не установлен"; fi

docker-logs: ## Показать логи сервисов
	@if command -v docker >/dev/null 2>&1; then docker compose logs -f; else echo "Docker не установлен"; fi

api-test: ## Проверить API здоровье
	curl -f http://localhost:8000/health || echo "API недоступен"

n8n-ui: ## Открыть n8n UI (macOS)
	open http://localhost:5678

dashboard-ui: ## Открыть dashboard (macOS)
	open http://localhost:8501

trigger-retrain: ## Запустить ручное переобучение
	curl -X POST http://localhost:5678/webhook/run-strategy \
		-H "Content-Type: application/json" \
		-d '{"strategy_id": "eurusd_mtf", "mode": "paper"}'

db-connect: ## Подключиться к PostgreSQL
	docker exec -it gregory-postgres psql -U gregory -d gregory_orchestration

db-status: ## Показать статус запусков
	docker exec -it gregory-postgres psql -U gregory -d gregory_orchestration \
		-c "SELECT run_id, strategy_id, stage, status, progress, started_at FROM runs ORDER BY started_at DESC LIMIT 10;"

test: ## Запустить тесты
	pytest tests/ -v

test-coverage: ## Запустить тесты с покрытием
	pytest tests/ --cov=src --cov-report=html

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov

docker-build: ## Собрать Docker образ
	docker build -t trading-ai-agent .

docker-run: ## Запустить в Docker
	docker run -p 8501:8501 trading-ai-agent

format: ## Форматировать код
	black src/ app/ telegram_bot/ tests/
	flake8 src/ app/ telegram_bot/ tests/

type-check: ## Проверить типы
	mypy src/ app/ telegram_bot/

setup-dev: install ## Настроить окружение для разработки
	pre-commit install

backtest: ## Запустить бэктестинг
	python3 -m pipeline.backtest

train: ## Обучить модели
	python3 -m pipeline.train

data-collect: ## Собрать данные
	python3 -m pipeline.data_collector
