# 🚀 Быстрый старт

## Установка и запуск за 5 минут

### 1. Установка зависимостей

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd trading-ai-agent

# Установите зависимости
pip install -r requirements.txt
```

### 2. Настройка конфигурации

```bash
# Скопируйте пример конфигурации
cp config/settings.example.yaml config/settings.yaml

# Отредактируйте config/settings.yaml и добавьте свои API ключи
```

### 3. Создание Telegram-бота

1. Найдите @BotFather в Telegram
2. Отправьте `/newbot` и следуйте инструкциям
3. Получите токен бота
4. Создайте группу и добавьте бота
5. Получите ID чата через @userinfobot

### 4. Запуск системы

```bash
# Запуск дашборда
python run_dashboard.py

# В новом терминале - запуск Telegram-бота
python run_bot.py

# В новом терминале - запуск основного агента
python -m src.main
```

### 5. Проверка работы

- Дашборд: http://localhost:8501
- Telegram: проверьте уведомления в группе
- Логи: папка `logs/`

## 🧪 Тестирование

```bash
# Запуск примера
python example_usage.py

# Запуск тестов
make test
```

## 🐳 Docker запуск

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

## 📚 Документация

- [Полная инструкция](SETUP.md)
- [Архитектура системы](ARCHITECTURE.md)
- [API документация](docs/api.md) - планируется

## 🆘 Поддержка

При проблемах:
1. Проверьте логи в `logs/`
2. Убедитесь в правильности API ключей
3. Проверьте конфигурацию
4. Создайте issue в репозитории

