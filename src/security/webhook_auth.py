"""
Аутентификация и авторизация веб-хуков
"""

import hmac
import hashlib
import time
from typing import Optional, Dict, Any, List
from functools import wraps
from loguru import logger

from ..core.config import config


class WebhookAuthenticator:
    """Аутентификатор веб-хуков"""
    
    def __init__(self):
        self.secret_key = config.get('security.webhook.secret_key', '')
        self.allowed_ips = config.get('security.webhook.allowed_ips', [])
        self.max_timestamp_diff = config.get('security.webhook.max_timestamp_diff', 300)  # 5 минут
        
    def verify_signature(self, payload: bytes, signature: str, timestamp: str) -> bool:
        """
        Проверка подписи веб-хука
        
        Args:
            payload: Тело запроса
            signature: Подпись из заголовка
            timestamp: Временная метка из заголовка
            
        Returns:
            bool: True если подпись валидна
        """
        try:
            # Проверяем временную метку
            if not self._verify_timestamp(timestamp):
                logger.warning("Невалидная временная метка в веб-хуке")
                return False
            
            # Создаем ожидаемую подпись
            expected_signature = self._create_signature(payload, timestamp)
            
            # Сравниваем подписи безопасно
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Ошибка проверки подписи веб-хука: {e}")
            return False
    
    def _verify_timestamp(self, timestamp: str) -> bool:
        """Проверка временной метки"""
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            
            # Проверяем, что запрос не слишком старый
            if current_time - request_time > self.max_timestamp_diff:
                return False
            
            # Проверяем, что запрос не из будущего (с запасом в 60 секунд)
            if request_time > current_time + 60:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def _create_signature(self, payload: bytes, timestamp: str) -> str:
        """Создание подписи для веб-хука"""
        message = f"{timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_ip(self, client_ip: str) -> bool:
        """
        Проверка IP адреса клиента
        
        Args:
            client_ip: IP адрес клиента
            
        Returns:
            bool: True если IP разрешен
        """
        if not self.allowed_ips:
            logger.warning("Список разрешенных IP не настроен")
            return True  # Разрешаем все IP если список пуст
        
        # Проверяем точное совпадение
        if client_ip in self.allowed_ips:
            return True
        
        # Проверяем CIDR блоки
        import ipaddress
        try:
            client_addr = ipaddress.ip_address(client_ip)
            for allowed_ip in self.allowed_ips:
                try:
                    if '/' in allowed_ip:
                        # CIDR блок
                        network = ipaddress.ip_network(allowed_ip, strict=False)
                        if client_addr in network:
                            return True
                    else:
                        # Точный IP
                        if str(client_addr) == allowed_ip:
                            return True
                except ValueError:
                    continue
        except ValueError:
            logger.error(f"Невалидный IP адрес: {client_ip}")
            return False
        
        return False
    
    def verify_webhook(self, payload: bytes, headers: Dict[str, str], client_ip: str) -> bool:
        """
        Полная проверка веб-хука
        
        Args:
            payload: Тело запроса
            headers: Заголовки запроса
            client_ip: IP адрес клиента
            
        Returns:
            bool: True если веб-хук валиден
        """
        # Проверяем IP
        if not self.verify_ip(client_ip):
            logger.warning(f"Заблокирован запрос с IP: {client_ip}")
            return False
        
        # Проверяем подпись
        signature = headers.get('X-Signature-256', '')
        timestamp = headers.get('X-Timestamp', '')
        
        if not signature or not timestamp:
            logger.warning("Отсутствуют обязательные заголовки веб-хука")
            return False
        
        if not self.verify_signature(payload, signature, timestamp):
            logger.warning("Невалидная подпись веб-хука")
            return False
        
        return True


def require_webhook_auth(f):
    """Декоратор для проверки аутентификации веб-хука"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Получаем данные запроса из kwargs
        request = kwargs.get('request')
        if not request:
            logger.error("Отсутствует объект request")
            return {"error": "Invalid request"}, 400
        
        # Извлекаем данные
        payload = await request.body()
        headers = dict(request.headers)
        client_ip = request.client.host
        
        # Проверяем веб-хук
        authenticator = WebhookAuthenticator()
        if not authenticator.verify_webhook(payload, headers, client_ip):
            logger.warning(f"Неавторизованный веб-хук от {client_ip}")
            return {"error": "Unauthorized"}, 401
        
        # Добавляем данные в kwargs для использования в функции
        kwargs['payload'] = payload
        kwargs['headers'] = headers
        kwargs['client_ip'] = client_ip
        
        return await f(*args, **kwargs)
    
    return decorated_function


class WebhookRateLimiter:
    """Rate limiter для веб-хуков"""
    
    def __init__(self):
        self.requests = {}  # {ip: [(timestamp, endpoint), ...]}
        self.max_requests = config.get('security.rate_limit.max_requests', 100)
        self.window_seconds = config.get('security.rate_limit.window_seconds', 3600)  # 1 час
        self.burst_limit = config.get('security.rate_limit.burst_limit', 10)  # 10 запросов в минуту
        self.burst_window = config.get('security.rate_limit.burst_window', 60)  # 1 минута
    
    def is_allowed(self, client_ip: str, endpoint: str = 'default') -> bool:
        """
        Проверка, разрешен ли запрос
        
        Args:
            client_ip: IP адрес клиента
            endpoint: Конечная точка
            
        Returns:
            bool: True если запрос разрешен
        """
        current_time = time.time()
        
        # Очищаем старые записи
        self._cleanup_old_requests(current_time)
        
        # Получаем записи для IP
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        ip_requests = self.requests[client_ip]
        
        # Проверяем общий лимит
        recent_requests = [
            req for req in ip_requests 
            if current_time - req[0] <= self.window_seconds
        ]
        
        if len(recent_requests) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return False
        
        # Проверяем burst лимит
        burst_requests = [
            req for req in ip_requests 
            if current_time - req[0] <= self.burst_window
        ]
        
        if len(burst_requests) >= self.burst_limit:
            logger.warning(f"Burst limit exceeded for IP {client_ip}")
            return False
        
        # Добавляем текущий запрос
        ip_requests.append((current_time, endpoint))
        
        return True
    
    def _cleanup_old_requests(self, current_time: float):
        """Очистка старых запросов"""
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req for req in self.requests[ip]
                if current_time - req[0] <= self.window_seconds
            ]
            
            # Удаляем IP без активных запросов
            if not self.requests[ip]:
                del self.requests[ip]
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Получение количества оставшихся запросов"""
        current_time = time.time()
        
        if client_ip not in self.requests:
            return self.max_requests
        
        recent_requests = [
            req for req in self.requests[client_ip]
            if current_time - req[0] <= self.window_seconds
        ]
        
        return max(0, self.max_requests - len(recent_requests))


# Глобальные экземпляры
webhook_authenticator = WebhookAuthenticator()
rate_limiter = WebhookRateLimiter()
