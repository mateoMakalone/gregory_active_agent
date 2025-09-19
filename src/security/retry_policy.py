"""
Retry политики с идемпотентностью для executions
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass
from loguru import logger

from ..core.config import config


class RetryStrategy(Enum):
    """Стратегии повторных попыток"""
    FIXED = "fixed"           # Фиксированная задержка
    EXPONENTIAL = "exponential"  # Экспоненциальная задержка
    LINEAR = "linear"         # Линейная задержка
    CUSTOM = "custom"         # Пользовательская стратегия


@dataclass
class RetryConfig:
    """Конфигурация retry политики"""
    max_attempts: int = 3
    base_delay: float = 1.0  # секунды
    max_delay: float = 300.0  # 5 минут
    backoff_factor: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True  # Добавлять случайность к задержке
    retry_on_exceptions: tuple = (Exception,)  # Исключения для retry
    stop_on_exceptions: tuple = ()  # Исключения для остановки retry


class IdempotencyManager:
    """Менеджер идемпотентности"""
    
    def __init__(self):
        self.execution_cache = {}  # {idempotency_key: result}
        self.cache_ttl = config.get('security.idempotency.cache_ttl', 3600)  # 1 час
        self.max_cache_size = config.get('security.idempotency.max_cache_size', 10000)
    
    def generate_key(self, execution_id: str, params: Dict[str, Any]) -> str:
        """
        Генерация ключа идемпотентности
        
        Args:
            execution_id: ID выполнения
            params: Параметры выполнения
            
        Returns:
            str: Ключ идемпотентности
        """
        # Сортируем параметры для консистентности
        sorted_params = json.dumps(params, sort_keys=True)
        
        # Создаем хеш
        content = f"{execution_id}:{sorted_params}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_cached_result(self, idempotency_key: str) -> Optional[Any]:
        """
        Получение кэшированного результата
        
        Args:
            idempotency_key: Ключ идемпотентности
            
        Returns:
            Any: Кэшированный результат или None
        """
        if idempotency_key in self.execution_cache:
            result, timestamp = self.execution_cache[idempotency_key]
            
            # Проверяем TTL
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"Возвращен кэшированный результат для ключа: {idempotency_key[:8]}...")
                return result
            else:
                # Удаляем устаревший результат
                del self.execution_cache[idempotency_key]
        
        return None
    
    def cache_result(self, idempotency_key: str, result: Any):
        """
        Кэширование результата
        
        Args:
            idempotency_key: Ключ идемпотентности
            result: Результат выполнения
        """
        # Очищаем кэш если он переполнен
        if len(self.execution_cache) >= self.max_cache_size:
            self._cleanup_cache()
        
        self.execution_cache[idempotency_key] = (result, time.time())
        logger.debug(f"Результат закэширован для ключа: {idempotency_key[:8]}...")
    
    def _cleanup_cache(self):
        """Очистка кэша от устаревших записей"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.execution_cache.items()
            if current_time - timestamp >= self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.execution_cache[key]
        
        logger.info(f"Очищено {len(expired_keys)} устаревших записей из кэша идемпотентности")
    
    def clear_cache(self):
        """Полная очистка кэша"""
        self.execution_cache.clear()
        logger.info("Кэш идемпотентности очищен")


class RetryManager:
    """Менеджер retry политик"""
    
    def __init__(self):
        self.idempotency_manager = IdempotencyManager()
        self.default_config = RetryConfig(
            max_attempts=config.get('security.retry.max_attempts', 3),
            base_delay=config.get('security.retry.base_delay', 1.0),
            max_delay=config.get('security.retry.max_delay', 300.0),
            backoff_factor=config.get('security.retry.backoff_factor', 2.0),
            strategy=RetryStrategy(config.get('security.retry.strategy', 'exponential')),
            jitter=config.get('security.retry.jitter', True)
        )
    
    async def execute_with_retry(
        self,
        func: Callable,
        execution_id: str,
        params: Dict[str, Any],
        retry_config: Optional[RetryConfig] = None,
        idempotent: bool = True
    ) -> Any:
        """
        Выполнение функции с retry и идемпотентностью
        
        Args:
            func: Функция для выполнения
            execution_id: ID выполнения
            params: Параметры функции
            retry_config: Конфигурация retry
            idempotent: Использовать ли идемпотентность
            
        Returns:
            Any: Результат выполнения
        """
        if retry_config is None:
            retry_config = self.default_config
        
        # Проверяем идемпотентность
        if idempotent:
            idempotency_key = self.idempotency_manager.generate_key(execution_id, params)
            cached_result = self.idempotency_manager.get_cached_result(idempotency_key)
            if cached_result is not None:
                return cached_result
        
        # Выполняем с retry
        last_exception = None
        
        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                logger.info(f"Попытка {attempt}/{retry_config.max_attempts} для выполнения {execution_id}")
                
                # Выполняем функцию
                if asyncio.iscoroutinefunction(func):
                    result = await func(**params)
                else:
                    result = func(**params)
                
                # Кэшируем результат если используется идемпотентность
                if idempotent:
                    self.idempotency_manager.cache_result(idempotency_key, result)
                
                logger.info(f"Выполнение {execution_id} успешно завершено с попытки {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Проверяем, нужно ли остановить retry
                if isinstance(e, retry_config.stop_on_exceptions):
                    logger.error(f"Критическая ошибка в выполнении {execution_id}: {e}")
                    raise e
                
                # Проверяем, нужно ли retry для этого исключения
                if not isinstance(e, retry_config.retry_on_exceptions):
                    logger.error(f"Неожиданная ошибка в выполнении {execution_id}: {e}")
                    raise e
                
                # Если это последняя попытка, поднимаем исключение
                if attempt == retry_config.max_attempts:
                    logger.error(f"Все попытки исчерпаны для выполнения {execution_id}")
                    raise e
                
                # Вычисляем задержку
                delay = self._calculate_delay(attempt, retry_config)
                logger.warning(f"Ошибка в попытке {attempt} для {execution_id}: {e}. Повтор через {delay:.2f}с")
                
                # Ждем перед следующей попыткой
                await asyncio.sleep(delay)
        
        # Если дошли сюда, значит все попытки исчерпаны
        raise last_exception
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Вычисление задержки для retry"""
        if config.strategy == RetryStrategy.FIXED:
            delay = config.base_delay
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * attempt
        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.backoff_factor ** (attempt - 1))
        else:
            delay = config.base_delay
        
        # Ограничиваем максимальной задержкой
        delay = min(delay, config.max_delay)
        
        # Добавляем jitter для избежания thundering herd
        if config.jitter:
            import random
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay
    
    def create_retry_config(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        backoff_factor: float = 2.0,
        strategy: Union[str, RetryStrategy] = RetryStrategy.EXPONENTIAL,
        jitter: bool = True,
        retry_on_exceptions: tuple = (Exception,),
        stop_on_exceptions: tuple = ()
    ) -> RetryConfig:
        """Создание конфигурации retry"""
        if isinstance(strategy, str):
            strategy = RetryStrategy(strategy)
        
        return RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            backoff_factor=backoff_factor,
            strategy=strategy,
            jitter=jitter,
            retry_on_exceptions=retry_on_exceptions,
            stop_on_exceptions=stop_on_exceptions
        )


class CircuitBreaker:
    """Circuit Breaker для защиты от каскадных сбоев"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Выполнение функции через circuit breaker"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Сброс счетчика при успехе
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e


# Глобальные экземпляры
retry_manager = RetryManager()
circuit_breaker = CircuitBreaker()
