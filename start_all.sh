#!/bin/bash

# Gregory Trading Agent - Полный запуск системы
# Скрипт для запуска всех компонентов локально

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Функция проверки зависимостей
check_dependencies() {
    print_status "Проверка зависимостей..."
    
    # Проверка Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 не найден. Установите Python 3.9+"
        exit 1
    fi
    
    # Проверка версии Python
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    major=$(echo $python_version | cut -d. -f1)
    minor=$(echo $python_version | cut -d. -f2)
    
    if [ $major -lt 3 ] || ([ $major -eq 3 ] && [ $minor -lt 9 ]); then
        print_error "Требуется Python 3.9+, текущая версия: $python_version"
        exit 1
    fi
    
    # Проверка pip пакетов
    if ! python3 -c "import streamlit, pandas, plotly" 2>/dev/null; then
        print_warning "Установка Python зависимостей..."
        pip3 install -r requirements.txt
    fi
    
    # Проверка PostgreSQL
    if ! command -v psql &> /dev/null; then
        print_warning "PostgreSQL не найден. Установка через brew..."
        brew install postgresql@14
    fi
    
    # Проверка Redis
    if ! command -v redis-server &> /dev/null; then
        print_warning "Redis не найден. Установка через brew..."
        brew install redis
    fi
    
    print_success "Все зависимости проверены"
}

# Функция запуска сервисов
start_services() {
    print_status "Запуск сервисов..."
    
    # Запуск PostgreSQL
    if ! brew services list | grep postgresql@14 | grep started > /dev/null; then
        print_status "Запуск PostgreSQL..."
        brew services start postgresql@14
        sleep 3
    else
        print_success "PostgreSQL уже запущен"
    fi
    
    # Запуск Redis
    if ! brew services list | grep redis | grep started > /dev/null; then
        print_status "Запуск Redis..."
        brew services start redis
        sleep 2
    else
        print_success "Redis уже запущен"
    fi
}

# Функция настройки базы данных
setup_database() {
    print_status "Настройка базы данных..."
    
    # Создание базы данных
    if ! psql -lqt | cut -d \| -f 1 | grep -qw gregory_orchestration; then
        print_status "Создание базы данных gregory_orchestration..."
        createdb gregory_orchestration
    else
        print_success "База данных уже существует"
    fi
    
    # Применение схемы
    print_status "Применение схемы базы данных..."
    psql gregory_orchestration < ops/sql/init.sql > /dev/null 2>&1 || true
    print_success "Схема базы данных применена"
}

# Функция проверки портов
check_ports() {
    print_status "Проверка портов..."
    
    # Проверка порта 8501 (Streamlit)
    if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null; then
        print_warning "Порт 8501 занят. Остановка процесса..."
        lsof -ti:8501 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Проверка порта 8000 (API)
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null; then
        print_warning "Порт 8000 занят. Остановка процесса..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    print_success "Порты свободны"
}

# Функция запуска компонентов
start_components() {
    print_status "Запуск компонентов Gregory Trading Agent..."
    
    # Создание папки для логов
    mkdir -p logs
    
    # Запуск API сервера в фоне
    print_status "Запуск API сервера (порт 8000)..."
    nohup python3 -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload > logs/api.log 2>&1 &
    API_PID=$!
    sleep 3
    
    # Проверка API
    if curl -f http://127.0.0.1:8000/health > /dev/null 2>&1; then
        print_success "API сервер запущен (PID: $API_PID)"
    else
        print_error "API сервер не отвечает"
        return 1
    fi
    
    # Запуск Dashboard в фоне
    print_status "Запуск Dashboard (порт 8501)..."
    nohup python3 -m streamlit run app/dashboard.py --server.port=8501 --server.address=127.0.0.1 > logs/dashboard.log 2>&1 &
    DASHBOARD_PID=$!
    sleep 5
    
    # Проверка Dashboard
    if curl -f http://127.0.0.1:8501 > /dev/null 2>&1; then
        print_success "Dashboard запущен (PID: $DASHBOARD_PID)"
    else
        print_warning "Dashboard может быть еще не готов"
    fi
    
    # Запуск Telegram бота в фоне
    print_status "Запуск Telegram бота..."
    nohup python3 run_bot.py > logs/bot.log 2>&1 &
    BOT_PID=$!
    sleep 2
    
    print_success "Telegram бот запущен (PID: $BOT_PID)"
    
    # Сохранение PID для остановки
    echo "$API_PID" > .pids/api.pid
    echo "$DASHBOARD_PID" > .pids/dashboard.pid
    echo "$BOT_PID" > .pids/bot.pid
    
    print_success "Все компоненты запущены!"
}

# Функция отображения статуса
show_status() {
    echo ""
    echo "🎉 Gregory Trading Agent запущен!"
    echo "=================================="
    echo ""
    echo "📊 Dashboard:    http://127.0.0.1:8501"
    echo "🔧 API Server:   http://127.0.0.1:8000"
    echo "📖 API Docs:     http://127.0.0.1:8000/docs"
    echo "📱 Telegram:     Проверьте уведомления"
    echo ""
    echo "📝 Логи:"
    echo "   - API:        tail -f logs/api.log"
    echo "   - Dashboard:  tail -f logs/dashboard.log"
    echo "   - Bot:        tail -f logs/bot.log"
    echo ""
    echo "🛑 Остановка:    ./stop_all.sh"
    echo "📊 Статус:       ./status.sh"
    echo ""
}

# Функция очистки при ошибке
cleanup() {
    print_error "Ошибка при запуске. Очистка..."
    if [ -f .pids/api.pid ]; then
        kill $(cat .pids/api.pid) 2>/dev/null || true
    fi
    if [ -f .pids/dashboard.pid ]; then
        kill $(cat .pids/dashboard.pid) 2>/dev/null || true
    fi
    if [ -f .pids/bot.pid ]; then
        kill $(cat .pids/bot.pid) 2>/dev/null || true
    fi
    rm -rf .pids
    exit 1
}

# Основная функция
main() {
    echo "🤖 Gregory Trading Agent - Полный запуск"
    echo "========================================"
    echo ""
    
    # Создание папки для PID файлов
    mkdir -p .pids
    
    # Установка обработчика ошибок
    trap cleanup EXIT
    
    # Выполнение шагов
    check_dependencies
    start_services
    setup_database
    check_ports
    start_components
    
    # Успешное завершение
    trap - EXIT
    show_status
}

# Запуск
main "$@"
