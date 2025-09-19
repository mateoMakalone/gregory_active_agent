"""
Асинхронный Telegram-бот для отправки торговых сигналов
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from src.core.config import config
from src.strategies.base_strategy import TradingSignal, SignalType, SignalStrength


class AsyncTelegramBot:
    """Асинхронный класс для работы с Telegram-ботом"""
    
    def __init__(self):
        """Инициализация бота"""
        self.bot_token = config.get('api.telegram.bot_token')
        self.chat_id = config.get('api.telegram.chat_id')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram токен или chat_id не настроены")
            self.is_available = False
        else:
            self.is_available = True
            logger.info("Асинхронный Telegram-бот инициализирован")
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Асинхронная отправка сообщения в Telegram
        
        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
            
        Returns:
            True если сообщение отправлено успешно
        """
        if not self.is_available:
            logger.warning("Telegram-бот недоступен")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if result.get('ok'):
                        logger.info("Сообщение отправлено в Telegram")
                        return True
                    else:
                        logger.error(f"Ошибка API Telegram: {result.get('description')}")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error("Таймаут при отправке сообщения в Telegram")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка HTTP при отправке в Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке в Telegram: {e}")
            return False
    
    async def send_signal(self, signal: TradingSignal) -> bool:
        """
        Асинхронная отправка торгового сигнала
        
        Args:
            signal: Торговый сигнал
            
        Returns:
            True если сигнал отправлен успешно
        """
        if not self.is_available:
            logger.warning("Telegram-бот недоступен")
            return False
        
        try:
            # Форматируем сообщение
            message = self._format_signal_message(signal)
            
            # Отправляем сообщение
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка отправки сигнала: {e}")
            return False
    
    def _format_signal_message(self, signal: TradingSignal) -> str:
        """
        Форматирование сообщения с торговым сигналом
        
        Args:
            signal: Торговый сигнал
            
        Returns:
            Отформатированное сообщение
        """
        # Эмодзи для типов сигналов
        signal_emoji = {
            SignalType.BUY: "🟢",
            SignalType.SELL: "🔴",
            SignalType.HOLD: "⚪"
        }
        
        # Эмодзи для силы сигнала
        strength_emoji = {
            SignalStrength.WEAK: "⚡",
            SignalStrength.MEDIUM: "⚡⚡",
            SignalStrength.STRONG: "⚡⚡⚡"
        }
        
        # Основное сообщение
        message = f"""
{signal_emoji.get(signal.signal_type, '❓')} <b>ТОРГОВЫЙ СИГНАЛ</b>

📊 <b>Инструмент:</b> {signal.symbol}
📈 <b>Тип:</b> {signal.signal_type.value}
{strength_emoji.get(signal.strength, '⚡')} <b>Сила:</b> {signal.strength.name}
💰 <b>Цена:</b> {signal.price:.4f}
🎯 <b>Уверенность:</b> {signal.confidence:.1%}
⏰ <b>Время:</b> {signal.timestamp.strftime('%H:%M:%S')}
📅 <b>Дата:</b> {signal.timestamp.strftime('%d.%m.%Y')}
🕐 <b>Таймфрейм:</b> {signal.timeframe}
🤖 <b>Стратегия:</b> {signal.strategy_name}
"""
        
        # Добавляем стоп-лосс и тейк-профит если есть
        if signal.stop_loss:
            message += f"🛑 <b>Стоп-лосс:</b> {signal.stop_loss:.4f}\n"
        
        if signal.take_profit:
            message += f"🎯 <b>Тейк-профит:</b> {signal.take_profit:.4f}\n"
        
        # Добавляем метаданные если есть
        if signal.metadata:
            message += "\n📊 <b>Дополнительно:</b>\n"
            for key, value in signal.metadata.items():
                if value is not None:
                    if isinstance(value, float):
                        message += f"• {key}: {value:.4f}\n"
                    else:
                        message += f"• {key}: {value}\n"
        
        # Добавляем рекомендации
        message += "\n⚠️ <b>Внимание:</b> Это сигнал для ручной торговли. Проверьте рынок перед входом!"
        
        return message.strip()
    
    async def send_alert(self, title: str, message: str, level: str = "INFO") -> bool:
        """
        Асинхронная отправка уведомления
        
        Args:
            title: Заголовок уведомления
            message: Текст уведомления
            level: Уровень (INFO, WARNING, ERROR)
            
        Returns:
            True если уведомление отправлено успешно
        """
        if not self.is_available:
            logger.warning("Telegram-бот недоступен")
            return False
        
        # Эмодзи для уровней
        level_emoji = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }
        
        formatted_message = f"""
{level_emoji.get(level, 'ℹ️')} <b>{title}</b>

{message}

⏰ {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}
"""
        
        return await self.send_message(formatted_message)
    
    async def send_performance_report(self, metrics: Dict[str, Any]) -> bool:
        """
        Асинхронная отправка отчета о производительности
        
        Args:
            metrics: Метрики производительности
            
        Returns:
            True если отчет отправлен успешно
        """
        if not self.is_available:
            logger.warning("Telegram-бот недоступен")
            return False
        
        try:
            message = f"""
📊 <b>ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ</b>

🤖 <b>Стратегия:</b> {metrics.get('strategy_name', 'Unknown')}
📈 <b>Всего сигналов:</b> {metrics.get('total_signals', 0)}
🟢 <b>Покупки:</b> {metrics.get('buy_signals', 0)}
🔴 <b>Продажи:</b> {metrics.get('sell_signals', 0)}
🎯 <b>Средняя уверенность:</b> {metrics.get('avg_confidence', 0):.1%}
🔄 <b>Статус:</b> {'Активна' if metrics.get('is_active', False) else 'Неактивна'}

⏰ {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}
"""
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка отправки отчета: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """
        Асинхронное тестирование подключения к Telegram API
        
        Returns:
            True если подключение успешно
        """
        if not self.is_available:
            return False
        
        try:
            url = f"{self.base_url}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if result.get('ok'):
                        bot_info = result['result']
                        logger.info(f"Telegram-бот подключен: @{bot_info['username']}")
                        return True
                    else:
                        logger.error("Ошибка получения информации о боте")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error("Таймаут при подключении к Telegram API")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка подключения к Telegram API: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при тестировании подключения: {e}")
            return False


# Глобальный экземпляр асинхронного бота
async_telegram_bot = AsyncTelegramBot()
