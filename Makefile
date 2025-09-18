# Trading AI Agent - Makefile

.PHONY: help install run test clean docker-build docker-run

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	python3 -m pip install -r requirements.txt

run: ## Запустить систему
	python3 -m src.main

run-dashboard: ## Запустить только дашборд
	streamlit run app/dashboard.py

run-bot: ## Запустить только Telegram-бота
	python3 run_bot.py

run-all: ## Запустить все компоненты (legacy)
	python3 run_all.py

run-example: ## Запустить пример
	python3 run_example.py

# Orchestration commands
docker-up: ## Запустить инфраструктуру с n8n
	docker-compose up -d

docker-down: ## Остановить инфраструктуру
	docker-compose down

docker-logs: ## Показать логи сервисов
	docker-compose logs -f

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
