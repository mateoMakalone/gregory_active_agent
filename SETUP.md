# Инструкция по настройке торгового AI-агента

## Предварительные требования

- Python 3.9+
- Git
- Make (для Windows можно установить через Chocolatey или использовать WSL)

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd trading-ai-agent
```

### 2. Установка зависимостей

```bash
make install
```

Или вручную:

```bash
pip install -r requirements.txt
```

### 3. Настройка конфигурации

Скопируйте пример конфигурации и заполните своими данными:

```bash
cp config/settings.example.yaml config/settings.yaml
```

Отредактируйте `config/settings.yaml` и добавьте:

- API ключи для FundingPips
- API ключи для HashHedge  
- Токен Telegram-бота
- ID чата для уведомлений

### 4. Создание Telegram-бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Получите токен бота
5. Создайте группу и добавьте бота как администратора
6. Получите ID чата (можно использовать @userinfobot)

## Запуск

### Локальный запуск

#### Запуск дашборда
```bash
make run-dashboard
```
Или:
```bash
python run_dashboard.py
```

#### Запуск Telegram-бота
```bash
make run-bot
```
Или:
```bash
python run_bot.py
```

#### Запуск основного агента
```bash
make run
```
Или:
```bash
python -m src.main
```

### Запуск всех компонентов

```bash
make run-all
```

### Docker запуск

#### Сборка образа
```bash
make docker-build
```

#### Запуск контейнеров
```bash
make docker-run
```

Или с docker-compose:

```bash
docker-compose up -d
```

## Структура проекта

```
trading-ai-agent/
├── src/                    # Исходный код
│   ├── core/              # Основные компоненты
│   ├── data/              # Адаптеры данных
│   ├── strategies/        # Торговые стратегии
│   └── models/            # ML модели
├── app/                   # Веб-приложение
├── telegram_bot/          # Telegram-бот
├── config/                # Конфигурация
├── data/                  # Данные
├── logs/                  # Логи
├── models/                # Обученные модели
└── tests/                 # Тесты
```

## Настройка API

### FundingPips

1. Зарегистрируйтесь на [FundingPips](https://fundingpips.com)
2. Получите API ключи в личном кабинете
3. Добавьте ключи в `config/settings.yaml`

### HashHedge

1. Зарегистрируйтесь на [HashHedge](https://hashhedge.com)
2. Получите API ключи в личном кабинете
3. Добавьте ключи в `config/settings.yaml`

## Мониторинг

### Логи

Логи сохраняются в папке `logs/`:
- `trading_agent.log` - основные логи системы
- Логи автоматически ротируются при достижении 10MB

### Дашборд

Веб-интерфейс доступен по адресу: http://localhost:8501

### Telegram уведомления

Бот отправляет:
- Торговые сигналы
- Уведомления о состоянии системы
- Отчеты о производительности

## Разработка

### Запуск тестов

```bash
make test
```

### Форматирование кода

```bash
make format
```

### Проверка типов

```bash
make type-check
```

## Устранение неполадок

### Проблемы с TA-Lib

На Windows:
```bash
pip install --find-links https://github.com/cgohlke/talib-build/releases TA-Lib
```

На Linux/Mac:
```bash
# Установите системные зависимости
sudo apt-get install build-essential
# Затем установите TA-Lib
pip install TA-Lib
```

### Проблемы с Telegram

1. Проверьте правильность токена бота
2. Убедитесь, что бот добавлен в группу как администратор
3. Проверьте ID чата

### Проблемы с API

1. Проверьте правильность API ключей
2. Убедитесь, что у вас есть доступ к API
3. Проверьте лимиты запросов

## Поддержка

При возникновении проблем:

1. Проверьте логи в папке `logs/`
2. Убедитесь, что все зависимости установлены
3. Проверьте конфигурацию в `config/settings.yaml`
4. Создайте issue в репозитории с описанием проблемы

