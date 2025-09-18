#!/bin/bash

# Gregory Trading Agent - Остановка всех компонентов

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Функция остановки процесса по PID
stop_process() {
    local name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_status "Остановка $name (PID: $pid)..."
            kill "$pid" 2>/dev/null
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                print_warning "Принудительная остановка $name..."
                kill -9 "$pid" 2>/dev/null
            fi
            print_success "$name остановлен"
        else
            print_warning "$name уже остановлен"
        fi
        rm -f "$pid_file"
    else
        print_warning "PID файл для $name не найден"
    fi
}

# Функция остановки по порту
stop_by_port() {
    local port=$1
    local name=$2
    
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        print_status "Остановка $name на порту $port (PID: $pid)..."
        kill "$pid" 2>/dev/null
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null
        fi
        print_success "$name остановлен"
    else
        print_warning "$name на порту $port не найден"
    fi
}

# Основная функция
main() {
    echo "🛑 Gregory Trading Agent - Остановка всех компонентов"
    echo "====================================================="
    echo ""
    
    # Остановка по PID файлам
    stop_process "API Server" ".pids/api.pid"
    stop_process "Dashboard" ".pids/dashboard.pid"
    stop_process "Telegram Bot" ".pids/bot.pid"
    
    # Остановка по портам (на случай если PID файлы отсутствуют)
    stop_by_port 8000 "API Server"
    stop_by_port 8501 "Dashboard"
    
    # Остановка всех процессов Python связанных с проектом
    print_status "Остановка всех процессов Gregory Trading Agent..."
    pkill -f "streamlit.*dashboard" 2>/dev/null || true
    pkill -f "uvicorn.*api" 2>/dev/null || true
    pkill -f "run_bot.py" 2>/dev/null || true
    pkill -f "src.main" 2>/dev/null || true
    
    # Очистка PID файлов
    rm -rf .pids
    
    print_success "Все компоненты остановлены"
    echo ""
    echo "💡 Для полной остановки сервисов:"
    echo "   brew services stop postgresql@14"
    echo "   brew services stop redis"
}

# Запуск
main "$@"
