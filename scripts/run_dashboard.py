"""
Скрипт для запуска веб-дашборда
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Запуск дашборда"""
    # Получаем путь к дашборду
    dashboard_path = Path(__file__).parent / "app" / "dashboard.py"
    
    if not dashboard_path.exists():
        print(f"Ошибка: файл дашборда не найден: {dashboard_path}")
        sys.exit(1)
    
    # Запускаем Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска дашборда: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nДашборд остановлен")
        sys.exit(0)

if __name__ == "__main__":
    main()

