"""
Скрипт для запуска всех компонентов торгового AI-агента
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path
from threading import Thread

class TradingAgentManager:
    """Менеджер для запуска всех компонентов системы"""
    
    def __init__(self):
        self.processes = {}
        self.running = False
    
    def start_component(self, name, command, cwd=None):
        """Запуск компонента"""
        try:
            print(f"🚀 Запуск {name}...")
            
            if isinstance(command, str):
                command = command.split()
            
            process = subprocess.Popen(
                command,
                cwd=cwd or Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[name] = process
            print(f"✅ {name} запущен (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска {name}: {e}")
            return False
    
    def stop_component(self, name):
        """Остановка компонента"""
        if name in self.processes:
            process = self.processes[name]
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"🛑 {name} остановлен")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"🔪 {name} принудительно остановлен")
            except Exception as e:
                print(f"❌ Ошибка остановки {name}: {e}")
            finally:
                del self.processes[name]
    
    def stop_all(self):
        """Остановка всех компонентов"""
        print("\n🛑 Остановка всех компонентов...")
        for name in list(self.processes.keys()):
            self.stop_component(name)
        self.running = False
        print("✅ Все компоненты остановлены")
    
    def check_processes(self):
        """Проверка состояния процессов"""
        for name, process in list(self.processes.items()):
            if process.poll() is not None:
                print(f"⚠️ {name} завершился неожиданно")
                del self.processes[name]
    
    def run(self):
        """Запуск всех компонентов"""
        print("🤖 Запуск торгового AI-агента")
        print("=" * 50)
        
        # Проверяем Python
        if sys.version_info < (3, 9):
            print("❌ Требуется Python 3.9+")
            sys.exit(1)
        
        # Проверяем зависимости
        try:
            import streamlit
            import pandas
            import plotly
            print("✅ Основные зависимости найдены")
        except ImportError as e:
            print(f"❌ Отсутствуют зависимости: {e}")
            print("Установите: pip install -r requirements.txt")
            sys.exit(1)
        
        # Запускаем компоненты
        components = [
            ("Dashboard", [sys.executable, "-m", "streamlit", "run", "app/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]),
            ("Telegram Bot", [sys.executable, "scripts/run_bot.py"]),
            ("Trading Agent", [sys.executable, "scripts/run_async.py"])
        ]
        
        # Запускаем все компоненты
        for name, command in components:
            if not self.start_component(name, command):
                print(f"❌ Не удалось запустить {name}")
                self.stop_all()
                sys.exit(1)
        
        self.running = True
        
        # Обработчик сигналов для корректного завершения
        def signal_handler(signum, frame):
            print(f"\n📡 Получен сигнал {signum}")
            self.stop_all()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("\n🎉 Все компоненты запущены!")
        print("📊 Дашборд: http://localhost:8501")
        print("📱 Telegram: проверьте уведомления")
        print("📝 Логи: папка logs/")
        print("\nНажмите Ctrl+C для остановки")
        
        # Основной цикл мониторинга
        try:
            while self.running:
                self.check_processes()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n📡 Получен сигнал остановки")
        finally:
            self.stop_all()


def main():
    """Главная функция"""
    manager = TradingAgentManager()
    manager.run()


if __name__ == "__main__":
    main()

