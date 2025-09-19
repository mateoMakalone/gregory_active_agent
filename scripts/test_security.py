#!/usr/bin/env python3
"""
Скрипт для тестирования системы безопасности
"""

import sys
import asyncio
import aiohttp
import json
import time
import hmac
import hashlib
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.security.webhook_auth import WebhookAuthenticator
from src.security.retry_policy import RetryManager, RetryConfig
from src.security.rate_limiter import RateLimiter, RateLimitConfig
from src.core.logger import setup_logging
from loguru import logger


class SecurityTester:
    """Тестер системы безопасности"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.webhook_secret = "test_secret_key"
        self.authenticator = WebhookAuthenticator()
        self.retry_manager = RetryManager()
        self.rate_limiter = RateLimiter(RateLimitConfig(requests_per_second=5.0))
    
    def create_webhook_signature(self, payload: str, timestamp: str) -> str:
        """Создание подписи для веб-хука"""
        message = f"{timestamp}.{payload}"
        signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def test_webhook_auth(self):
        """Тест аутентификации веб-хуков"""
        logger.info("🧪 Тестирование аутентификации веб-хуков...")
        
        # Валидный webhook
        payload = json.dumps({"type": "test", "data": "valid"})
        timestamp = str(int(time.time()))
        signature = self.create_webhook_signature(payload, timestamp)
        
        headers = {
            "X-Signature-256": signature,
            "X-Timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/webhook/n8n",
                data=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    logger.info("✅ Валидный webhook принят")
                else:
                    logger.error(f"❌ Валидный webhook отклонен: {response.status}")
        
        # Невалидный webhook (неправильная подпись)
        invalid_signature = "sha256=invalid_signature"
        headers["X-Signature-256"] = invalid_signature
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/webhook/n8n",
                data=payload,
                headers=headers
            ) as response:
                if response.status == 401:
                    logger.info("✅ Невалидный webhook корректно отклонен")
                else:
                    logger.error(f"❌ Невалидный webhook не отклонен: {response.status}")
    
    async def test_rate_limiting(self):
        """Тест rate limiting"""
        logger.info("🧪 Тестирование rate limiting...")
        
        # Отправляем много запросов быстро
        async with aiohttp.ClientSession() as session:
            success_count = 0
            rate_limited_count = 0
            
            for i in range(20):  # Больше чем лимит
                try:
                    async with session.get(f"{self.base_url}/health") as response:
                        if response.status == 200:
                            success_count += 1
                        elif response.status == 429:
                            rate_limited_count += 1
                            logger.info(f"✅ Rate limit сработал на запросе {i+1}")
                            break
                except Exception as e:
                    logger.error(f"Ошибка запроса {i+1}: {e}")
                
                # Небольшая задержка между запросами
                await asyncio.sleep(0.1)
            
            logger.info(f"📊 Успешных запросов: {success_count}, Rate limited: {rate_limited_count}")
    
    async def test_backpressure(self):
        """Тест backpressure"""
        logger.info("🧪 Тестирование backpressure...")
        
        # Создаем много одновременных запросов
        async def make_request(session, i):
            try:
                async with session.post(
                    f"{self.base_url}/signals",
                    json={
                        "strategy_id": f"test_strategy_{i}",
                        "symbol": "EURUSD",
                        "timeframe": "1h",
                        "signal_type": "BUY",
                        "strength": "MEDIUM",
                        "price": 1.1000,
                        "confidence": 0.75
                    }
                ) as response:
                    return response.status
            except Exception as e:
                logger.error(f"Ошибка запроса {i}: {e}")
                return 500
        
        async with aiohttp.ClientSession() as session:
            # Создаем много задач одновременно
            tasks = [make_request(session, i) for i in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if r == 200)
            overloaded_count = sum(1 for r in results if r == 503)
            
            logger.info(f"📊 Успешных запросов: {success_count}, Overloaded: {overloaded_count}")
    
    async def test_retry_policy(self):
        """Тест retry политики"""
        logger.info("🧪 Тестирование retry политики...")
        
        # Функция, которая иногда падает
        call_count = 0
        
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Временная ошибка")
            return "Успех!"
        
        try:
            result = await self.retry_manager.execute_with_retry(
                func=flaky_function,
                execution_id="test_retry",
                params={},
                retry_config=RetryConfig(max_attempts=3, base_delay=0.1)
            )
            
            logger.info(f"✅ Retry политика работает: {result}")
            logger.info(f"📊 Функция вызвана {call_count} раз")
            
        except Exception as e:
            logger.error(f"❌ Retry политика не сработала: {e}")
    
    async def test_idempotency(self):
        """Тест идемпотентности"""
        logger.info("🧪 Тестирование идемпотентности...")
        
        # Функция, которая должна выполняться только один раз
        execution_count = 0
        
        async def expensive_function():
            nonlocal execution_count
            execution_count += 1
            await asyncio.sleep(0.1)  # Имитация долгой операции
            return f"Результат {execution_count}"
        
        # Выполняем одну и ту же операцию несколько раз
        tasks = []
        for i in range(5):
            task = self.retry_manager.execute_with_retry(
                func=expensive_function,
                execution_id="test_idempotency",
                params={"param": "value"},
                idempotent=True
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Все результаты должны быть одинаковыми
        if all(r == results[0] for r in results):
            logger.info("✅ Идемпотентность работает корректно")
            logger.info(f"📊 Функция выполнена {execution_count} раз, но вернула {len(set(results))} уникальных результатов")
        else:
            logger.error("❌ Идемпотентность не работает")
    
    async def test_circuit_breaker(self):
        """Тест circuit breaker"""
        logger.info("🧪 Тестирование circuit breaker...")
        
        from src.security.retry_policy import circuit_breaker
        
        # Функция, которая всегда падает
        async def failing_function():
            raise Exception("Всегда падает")
        
        # Выполняем несколько раз, чтобы открыть circuit breaker
        for i in range(7):  # Больше чем failure_threshold (5)
            try:
                await circuit_breaker.call(failing_function)
            except Exception as e:
                if "Circuit breaker is OPEN" in str(e):
                    logger.info(f"✅ Circuit breaker открылся на попытке {i+1}")
                    break
                elif i < 6:  # Не последняя попытка
                    logger.info(f"Попытка {i+1}: {e}")
        
        # Проверяем, что circuit breaker открыт
        try:
            await circuit_breaker.call(failing_function)
        except Exception as e:
            if "Circuit breaker is OPEN" in str(e):
                logger.info("✅ Circuit breaker корректно открыт")
            else:
                logger.error("❌ Circuit breaker не открылся")
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        logger.info("🚀 Запуск тестов системы безопасности...")
        
        try:
            await self.test_webhook_auth()
            await asyncio.sleep(1)
            
            await self.test_rate_limiting()
            await asyncio.sleep(1)
            
            await self.test_backpressure()
            await asyncio.sleep(1)
            
            await self.test_retry_policy()
            await asyncio.sleep(1)
            
            await self.test_idempotency()
            await asyncio.sleep(1)
            
            await self.test_circuit_breaker()
            
            logger.info("✅ Все тесты безопасности завершены!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в тестах безопасности: {e}")


async def main():
    """Основная функция"""
    print("🔒 Тестирование системы безопасности торгового AI-агента")
    print("=" * 60)
    
    # Настраиваем логирование
    setup_logging()
    
    tester = SecurityTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
