"""
Скрипт для запуска примера торгового AI-агента
"""

import sys
import os
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent))

def main():
    """Запуск примера"""
    print("🤖 Запуск примера торгового AI-агента")
    print("=" * 50)
    
    try:
        # Импортируем и запускаем пример
        from example_usage import main as run_example
        run_example()
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Убедитесь, что все зависимости установлены:")
        print("pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")
        sys.exit(1)
    
    print("\n✅ Пример выполнен успешно!")
    print("\n📚 Для полной настройки системы:")
    print("1. Скопируйте config/settings.example.yaml в config/settings.yaml")
    print("2. Заполните реальные API ключи")
    print("3. Запустите: python -m src.main")

if __name__ == "__main__":
    main()

