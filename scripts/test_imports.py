#!/usr/bin/env python3
"""
Тест импортов для проверки работоспособности
"""

import sys
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

def test_imports():
    """Тест всех критичных импортов"""
    print("🧪 Тестирование импортов...")
    
    try:
        # Тест адаптеров данных
        from src.data.adapters import AsyncFundingPipsAdapter, AsyncHashHedgeAdapter, create_test_data
        print("✅ src.data.adapters - OK")
        
        # Тест контрактов
        from src.contracts.data_feed import DataFeed, Bar, Tick
        from src.contracts.broker import Broker, Order, Position
        from src.contracts.risk_engine import RiskEngine, RiskLimits
        from src.contracts.portfolio_manager import PortfolioManager
        from src.contracts.strategy_runtime import StrategyRuntime
        print("✅ src.contracts - OK")
        
        # Тест execution
        from src.execution.paper_broker import PaperBroker
        print("✅ src.execution.paper_broker - OK")
        
        # Тест API
        from src.api.v2.server import APIServerV2
        print("✅ src.api.v2.server - OK")
        
        # Тест безопасности
        from src.security.webhook_auth import WebhookAuthenticator
        from src.security.rate_limiter import RateLimiter
        from src.security.retry_policy import RetryManager
        print("✅ src.security - OK")
        
        # Тест базы данных
        from src.database.connection import db_manager
        from src.database.models import Signal, Position, Order
        from src.database.services import SignalService, PositionService
        print("✅ src.database - OK")
        
        # Тест стратегий
        from src.strategies.trend_following_strategy import TrendFollowingStrategy
        from src.strategies.indicators import TechnicalIndicators
        print("✅ src.strategies - OK")
        
        # Тест Telegram бота
        from telegram_bot.bot import async_telegram_bot
        print("✅ telegram_bot.bot - OK")
        
        # Тест создания тестовых данных
        import pandas as pd
        test_data = create_test_data("EURUSD", days=1)
        assert len(test_data) > 0
        print("✅ create_test_data - OK")
        
        print("\n🎉 Все импорты работают корректно!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
