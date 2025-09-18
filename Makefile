# Trading AI Agent - Makefile

.PHONY: help install run test clean docker-build docker-run

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

run: ## Запустить систему
	python -m src.main

run-dashboard: ## Запустить только дашборд
	streamlit run app/dashboard.py

run-bot: ## Запустить только Telegram-бота
	python run_bot.py

run-all: ## Запустить все компоненты
	python run_all.py

run-example: ## Запустить пример
	python run_example.py

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
	python -m pipeline.backtest

train: ## Обучить модели
	python -m pipeline.train

data-collect: ## Собрать данные
	python -m pipeline.data_collector
