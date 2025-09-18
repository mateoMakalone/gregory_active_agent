#!/bin/bash

# Gregory Trading Agent - Проверка статуса системы

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

# Функция проверки сервиса
check_service() {
    local name=$1
    local url=$2
    local port=$3
    
    if curl -f "$url" > /dev/null 2>&1; then
        print_success "$name доступен ($url)"
        return 0
    else
        print_error "$name недоступен ($url)"
        return 1
    fi
}

# Функция проверки порта
check_port() {
    local port=$1
    local name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -ti:$port)
        print_success "$name слушает порт $port (PID: $pid)"
        return 0
    else
        print_error "$name не слушает порт $port"
        return 1
    fi
}

# Функция проверки процесса
check_process() {
    local name=$1
    local pattern=$2
    
    if pgrep -f "$pattern" > /dev/null; then
        local pid=$(pgrep -f "$pattern")
        print_success "$name запущен (PID: $pid)"
        return 0
    else
        print_error "$name не запущен"
        return 1
    fi
}

# Основная функция
main() {
    echo "📊 Gregory Trading Agent - Статус системы"
    echo "========================================"
    echo ""
    
    # Проверка сервисов
    print_status "Проверка сервисов..."
    echo ""
    
    # PostgreSQL
    if brew services list | grep postgresql@14 | grep started > /dev/null; then
        print_success "PostgreSQL запущен"
    else
        print_error "PostgreSQL не запущен"
    fi
    
    # Redis
    if brew services list | grep redis | grep started > /dev/null; then
        print_success "Redis запущен"
    else
        print_error "Redis не запущен"
    fi
    
    echo ""
    print_status "Проверка компонентов..."
    echo ""
    
    # API Server
    check_port 8000 "API Server"
    check_service "API Server" "http://127.0.0.1:8000/health" 8000
    
    # Dashboard
    check_port 8501 "Dashboard"
    check_service "Dashboard" "http://127.0.0.1:8501" 8501
    
    # Telegram Bot
    check_process "Telegram Bot" "run_bot.py"
    
    echo ""
    print_status "Проверка базы данных..."
    echo ""
    
    # Проверка подключения к БД
    if psql -d gregory_orchestration -c "SELECT 1;" > /dev/null 2>&1; then
        print_success "База данных gregory_orchestration доступна"
        
        # Проверка таблиц
        table_count=$(psql -d gregory_orchestration -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
        if [ "$table_count" -gt 0 ]; then
            print_success "Найдено $table_count таблиц в БД"
        else
            print_warning "Таблицы в БД не найдены"
        fi
    else
        print_error "База данных gregory_orchestration недоступна"
    fi
    
    echo ""
    print_status "Проверка логов..."
    echo ""
    
    # Проверка логов
    if [ -f "logs/api.log" ]; then
        local api_size=$(wc -l < logs/api.log 2>/dev/null || echo "0")
        print_success "API лог: $api_size строк"
    else
        print_warning "API лог не найден"
    fi
    
    if [ -f "logs/dashboard.log" ]; then
        local dashboard_size=$(wc -l < logs/dashboard.log 2>/dev/null || echo "0")
        print_success "Dashboard лог: $dashboard_size строк"
    else
        print_warning "Dashboard лог не найден"
    fi
    
    if [ -f "logs/bot.log" ]; then
        local bot_size=$(wc -l < logs/bot.log 2>/dev/null || echo "0")
        print_success "Bot лог: $bot_size строк"
    else
        print_warning "Bot лог не найден"
    fi
    
    echo ""
    print_status "Сводка..."
    echo ""
    
    # Подсчет работающих компонентов
    local running=0
    local total=5
    
    if brew services list | grep postgresql@14 | grep started > /dev/null; then ((running++)); fi
    if brew services list | grep redis | grep started > /dev/null; then ((running++)); fi
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then ((running++)); fi
    if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then ((running++)); fi
    if pgrep -f "run_bot.py" > /dev/null; then ((running++)); fi
    
    echo "Работает: $running из $total компонентов"
    
    if [ $running -eq $total ]; then
        print_success "Все компоненты работают!"
    elif [ $running -gt 0 ]; then
        print_warning "Некоторые компоненты работают"
    else
        print_error "Ни один компонент не работает"
    fi
    
    echo ""
    echo "🔗 Ссылки:"
    echo "   Dashboard: http://127.0.0.1:8501"
    echo "   API:       http://127.0.0.1:8000"
    echo "   API Docs:  http://127.0.0.1:8000/docs"
    echo ""
    echo "🛠️  Команды:"
    echo "   Запуск:    ./start_all.sh"
    echo "   Остановка: ./stop_all.sh"
    echo "   Статус:    ./status.sh"
}

# Запуск
main "$@"

