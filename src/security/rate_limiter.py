"""
Rate limiting и backpressure для системы
"""

import asyncio
import time
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from ..core.config import config


class RateLimitStrategy(Enum):
    """Стратегии rate limiting"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Конфигурация rate limiting"""
    requests_per_second: float = 10.0
    burst_size: int = 20
    window_size: int = 60  # секунды
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    enabled: bool = True


class TokenBucket:
    """Token Bucket алгоритм для rate limiting"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # токенов в секунду
        self.capacity = capacity  # максимальная вместимость
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Потребление токенов
        
        Args:
            tokens: Количество токенов для потребления
            
        Returns:
            bool: True если токены доступны
        """
        async with self._lock:
            now = time.time()
            # Добавляем токены за прошедшее время
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            # Проверяем, достаточно ли токенов
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        Ожидание доступности токенов
        
        Args:
            tokens: Количество токенов
            timeout: Таймаут ожидания
            
        Returns:
            bool: True если токены стали доступны
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.consume(tokens):
                return True
            
            # Ждем немного перед следующей попыткой
            await asyncio.sleep(0.1)
        
        return False


class SlidingWindow:
    """Sliding Window алгоритм для rate limiting"""
    
    def __init__(self, max_requests: int, window_size: int):
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """
        Проверка, разрешен ли запрос
        
        Returns:
            bool: True если запрос разрешен
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_size
            
            # Удаляем старые запросы
            self.requests = [req_time for req_time in self.requests if req_time > window_start]
            
            # Проверяем лимит
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    async def wait_for_slot(self, timeout: float = 30.0) -> bool:
        """
        Ожидание доступного слота
        
        Args:
            timeout: Таймаут ожидания
            
        Returns:
            bool: True если слот стал доступен
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.is_allowed():
                return True
            
            await asyncio.sleep(0.1)
        
        return False


class RateLimiter:
    """Основной rate limiter"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.buckets: Dict[str, TokenBucket] = {}
        self.windows: Dict[str, SlidingWindow] = {}
        self._lock = asyncio.Lock()
    
    def _get_bucket(self, key: str) -> TokenBucket:
        """Получение или создание bucket для ключа"""
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(
                rate=self.config.requests_per_second,
                capacity=self.config.burst_size
            )
        return self.buckets[key]
    
    def _get_window(self, key: str) -> SlidingWindow:
        """Получение или создание window для ключа"""
        if key not in self.windows:
            self.windows[key] = SlidingWindow(
                max_requests=int(self.config.requests_per_second * self.config.window_size),
                window_size=self.config.window_size
            )
        return self.windows[key]
    
    async def is_allowed(self, key: str = "default") -> bool:
        """
        Проверка, разрешен ли запрос
        
        Args:
            key: Ключ для группировки запросов
            
        Returns:
            bool: True если запрос разрешен
        """
        if not self.config.enabled:
            return True
        
        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            bucket = self._get_bucket(key)
            return await bucket.consume()
        
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            window = self._get_window(key)
            return await window.is_allowed()
        
        return True
    
    async def wait_for_permission(self, key: str = "default", timeout: float = 30.0) -> bool:
        """
        Ожидание разрешения на выполнение запроса
        
        Args:
            key: Ключ для группировки запросов
            timeout: Таймаут ожидания
            
        Returns:
            bool: True если разрешение получено
        """
        if not self.config.enabled:
            return True
        
        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            bucket = self._get_bucket(key)
            return await bucket.wait_for_tokens(timeout=timeout)
        
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            window = self._get_window(key)
            return await window.wait_for_slot(timeout=timeout)
        
        return True
    
    async def cleanup_old_entries(self):
        """Очистка старых записей"""
        async with self._lock:
            # Очищаем старые bucket'ы (старше 1 часа)
            current_time = time.time()
            keys_to_remove = []
            
            for key, bucket in self.buckets.items():
                if current_time - bucket.last_update > 3600:  # 1 час
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.buckets[key]
            
            if keys_to_remove:
                logger.info(f"Очищено {len(keys_to_remove)} старых rate limit записей")


class BackpressureManager:
    """Менеджер backpressure для защиты от перегрузки"""
    
    def __init__(self):
        self.max_queue_size = config.get('security.backpressure.max_queue_size', 1000)
        self.current_queue_size = 0
        self.queue_full_threshold = config.get('security.backpressure.queue_full_threshold', 0.8)
        self.backpressure_delay = config.get('security.backpressure.delay', 0.1)
        self._lock = asyncio.Lock()
    
    async def check_capacity(self) -> bool:
        """
        Проверка доступности места в очереди
        
        Returns:
            bool: True если есть место
        """
        async with self._lock:
            return self.current_queue_size < self.max_queue_size
    
    async def acquire_slot(self) -> bool:
        """
        Получение слота в очереди
        
        Returns:
            bool: True если слот получен
        """
        async with self._lock:
            if self.current_queue_size < self.max_queue_size:
                self.current_queue_size += 1
                return True
            return False
    
    async def release_slot(self):
        """Освобождение слота в очереди"""
        async with self._lock:
            if self.current_queue_size > 0:
                self.current_queue_size -= 1
    
    async def get_backpressure_delay(self) -> float:
        """
        Получение задержки для backpressure
        
        Returns:
            float: Задержка в секундах
        """
        async with self._lock:
            utilization = self.current_queue_size / self.max_queue_size
            
            if utilization >= self.queue_full_threshold:
                # Увеличиваем задержку при высокой загрузке
                return self.backpressure_delay * (1 + utilization)
            
            return 0.0
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Получение статуса очереди"""
        return {
            'current_size': self.current_queue_size,
            'max_size': self.max_queue_size,
            'utilization': self.current_queue_size / self.max_queue_size,
            'is_full': self.current_queue_size >= self.max_queue_size
        }


def rate_limit(requests_per_second: float = 10.0, key_func: Optional[Callable] = None):
    """
    Декоратор для rate limiting
    
    Args:
        requests_per_second: Количество запросов в секунду
        key_func: Функция для генерации ключа (по умолчанию используется IP)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Генерируем ключ
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = "default"
            
            # Создаем rate limiter
            config = RateLimitConfig(requests_per_second=requests_per_second)
            limiter = RateLimiter(config)
            
            # Проверяем разрешение
            if not await limiter.is_allowed(key):
                raise Exception("Rate limit exceeded")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def backpressure_protection(max_queue_size: int = 1000):
    """
    Декоратор для backpressure защиты
    
    Args:
        max_queue_size: Максимальный размер очереди
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Создаем менеджер backpressure
            manager = BackpressureManager()
            manager.max_queue_size = max_queue_size
            
            # Проверяем доступность
            if not await manager.acquire_slot():
                raise Exception("System overloaded, please try again later")
            
            try:
                # Добавляем задержку если нужно
                delay = await manager.get_backpressure_delay()
                if delay > 0:
                    await asyncio.sleep(delay)
                
                return await func(*args, **kwargs)
            finally:
                await manager.release_slot()
        
        return wrapper
    return decorator


# Глобальные экземпляры
default_rate_limiter = RateLimiter(RateLimitConfig())
backpressure_manager = BackpressureManager()
