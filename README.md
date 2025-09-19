# 🤖 Gregory Trading AI Agent

Интеллектуальный торговый агент с поддержкой множественных стратегий и интеграцией с Telegram.

## 📚 Документация

### 🎯 Обзор
- [README](docs/overview/README.md) - Основная документация
- [Что было построено](docs/overview/WHAT_WAS_BUILT.md) - Детальное описание функционала
- [Финальная сводка](docs/overview/FINAL_SUMMARY.md) - Краткий обзор проекта
- [Сводка реализации](docs/overview/IMPLEMENTATION_SUMMARY.md) - Техническая сводка
- [Улучшения](docs/overview/IMPROVEMENTS.md) - Планы по развитию
- [Следующие шаги](docs/overview/NEXT_STEPS.md) - Roadmap

### ⚙️ Установка и настройка
- [Быстрый старт](docs/setup/QUICKSTART.md) - Быстрое начало работы
- [Подробная установка](docs/setup/SETUP.md) - Детальная инструкция по установке

### 🏗️ Архитектура
- [Архитектура системы](docs/architecture/ARCHITECTURE.md) - Обзор архитектуры
- [Асинхронная производительность](docs/architecture/ASYNC_PERFORMANCE.md) - Производительность

### 🔧 API и интеграции
- [База данных](docs/DATABASE.md) - Схема и модели данных
- [Безопасность](docs/SECURITY.md) - Политики безопасности

### 📖 Справочники
- [Глоссарий](docs/glossary/GLOSSARY.md) - Термины и определения
- [FAQ](docs/glossary/FAQ.md) - Часто задаваемые вопросы

## 🚀 Быстрый старт

```bash
# Клонирование репозитория
git clone <repository-url>
cd trading-ai-agent

# Установка зависимостей
pip install -r requirements.txt

# Запуск через Docker Compose
docker-compose -f docker-compose.v2.yml up -d

# Или локальный запуск
python scripts/run_all.py
```

## 📁 Структура проекта

```
trading-ai-agent/
├── docs/                          # 📚 Документация
│   ├── overview/                  # Обзор проекта
│   ├── setup/                     # Установка и настройка
│   ├── architecture/              # Архитектура
│   ├── api/                       # API документация
│   ├── deployment/                # Развертывание
│   └── glossary/                  # Справочники
├── src/                           # 🐍 Исходный код
├── app/                           # 🌐 Веб-приложения
├── docker/                        # 🐳 Docker файлы
├── scripts/                       # 📜 Скрипты запуска
├── tests/                         # 🧪 Тесты
└── ops/                          # ⚙️ Операционные файлы
```

## 🛠️ Основные команды

```bash
# Запуск всех сервисов
make docker-compose-up

# Остановка сервисов
make docker-compose-down

# Сборка образов
make docker-build

# Запуск тестов
make test

# Линтинг кода
make lint
```

## 📞 Поддержка

Для вопросов и предложений создавайте Issues в репозитории.

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.
