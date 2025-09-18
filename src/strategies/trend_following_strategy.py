"""
Стратегия следования за трендом
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from .indicators import TechnicalIndicators


class TrendFollowingStrategy(BaseStrategy):
    """
    Стратегия следования за трендом
    
    Использует многотаймфреймовый анализ:
    - 4h: определение основного тренда
    - 1h: подтверждение тренда
    - 5m: поиск точки входа
    """
    
    def __init__(self, config: Dict):
        super().__init__("TrendFollowing", config)
        
        # Параметры стратегии
        self.trend_sma_period = config.get('trend_sma_period', 50)
        self.confirmation_sma_period = config.get('confirmation_sma_period', 20)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.volume_threshold = config.get('volume_threshold', 1.2)  # Множитель среднего объема
        
        logger.info(f"Стратегия TrendFollowing настроена: trend_sma={self.trend_sma_period}, "
                   f"confirmation_sma={self.confirmation_sma_period}")
    
    def get_required_timeframes(self) -> List[str]:
        """Необходимые таймфреймы для анализа"""
        return ['4h', '1h', '5m']
    
    def analyze(self, data: Dict[str, pd.DataFrame]) -> Optional[TradingSignal]:
        """
        Анализ данных и генерация сигнала
        
        Args:
            data: Словарь с данными по таймфреймам
            
        Returns:
            TradingSignal или None
        """
        try:
            # Проверяем наличие всех необходимых таймфреймов
            required_tf = self.get_required_timeframes()
            missing_tf = [tf for tf in required_tf if tf not in data]
            if missing_tf:
                logger.warning(f"Отсутствуют таймфреймы: {missing_tf}")
                return None
            
            # Получаем данные по таймфреймам
            trend_data = data['4h']  # Основной тренд
            confirmation_data = data['1h']  # Подтверждение
            entry_data = data['5m']  # Точка входа
            
            # Проверяем, что данные не пустые
            if any(df.empty for df in [trend_data, confirmation_data, entry_data]):
                logger.warning("Один из таймфреймов содержит пустые данные")
                return None
            
            # Анализируем тренд на 4h
            trend_signal = self._analyze_trend(trend_data)
            if not trend_signal:
                return None
            
            # Подтверждаем тренд на 1h
            confirmation_signal = self._confirm_trend(confirmation_data, trend_signal)
            if not confirmation_signal:
                return None
            
            # Ищем точку входа на 5m
            entry_signal = self._find_entry_point(entry_data, trend_signal)
            if not entry_signal:
                return None
            
            # Создаем финальный сигнал
            signal = self._create_signal(entry_signal, entry_data)
            
            if signal and self.add_signal(signal):
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка анализа в стратегии {self.name}: {e}")
            return None
    
    def _analyze_trend(self, data: pd.DataFrame) -> Optional[str]:
        """
        Анализ основного тренда на 4h
        
        Args:
            data: Данные 4h таймфрейма
            
        Returns:
            'bullish', 'bearish' или None
        """
        try:
            # Рассчитываем индикаторы
            indicators = TechnicalIndicators(data)
            sma = indicators.sma(self.trend_sma_period)
            rsi = indicators.rsi(self.rsi_period)
            
            # Получаем последние значения
            current_price = data['close'].iloc[-1]
            current_sma = sma.iloc[-1]
            current_rsi = rsi.iloc[-1]
            
            # Проверяем на NaN
            if pd.isna(current_sma) or pd.isna(current_rsi):
                return None
            
            # Определяем тренд
            if current_price > current_sma and current_rsi < self.rsi_overbought:
                return 'bullish'
            elif current_price < current_sma and current_rsi > self.rsi_oversold:
                return 'bearish'
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка анализа тренда: {e}")
            return None
    
    def _confirm_trend(self, data: pd.DataFrame, trend: str) -> Optional[str]:
        """
        Подтверждение тренда на 1h
        
        Args:
            data: Данные 1h таймфрейма
            trend: Направление тренда ('bullish' или 'bearish')
            
        Returns:
            'bullish', 'bearish' или None
        """
        try:
            indicators = TechnicalIndicators(data)
            sma = indicators.sma(self.confirmation_sma_period)
            rsi = indicators.rsi(self.rsi_period)
            
            current_price = data['close'].iloc[-1]
            current_sma = sma.iloc[-1]
            current_rsi = rsi.iloc[-1]
            
            if pd.isna(current_sma) or pd.isna(current_rsi):
                return None
            
            # Подтверждаем тренд
            if trend == 'bullish' and current_price > current_sma and current_rsi < self.rsi_overbought:
                return 'bullish'
            elif trend == 'bearish' and current_price < current_sma and current_rsi > self.rsi_oversold:
                return 'bearish'
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка подтверждения тренда: {e}")
            return None
    
    def _find_entry_point(self, data: pd.DataFrame, trend: str) -> Optional[Dict]:
        """
        Поиск точки входа на 5m
        
        Args:
            data: Данные 5m таймфрейма
            trend: Направление тренда
            
        Returns:
            Словарь с информацией о точке входа или None
        """
        try:
            indicators = TechnicalIndicators(data)
            sma_short = indicators.sma(10)
            sma_long = indicators.sma(20)
            rsi = indicators.rsi(self.rsi_period)
            
            current_price = data['close'].iloc[-1]
            current_sma_short = sma_short.iloc[-1]
            current_sma_long = sma_long.iloc[-1]
            current_rsi = rsi.iloc[-1]
            
            if any(pd.isna(x) for x in [current_sma_short, current_sma_long, current_rsi]):
                return None
            
            # Проверяем объем
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            if current_volume < avg_volume * self.volume_threshold:
                return None
            
            # Ищем точку входа
            if trend == 'bullish':
                # Покупаем при пересечении SMA и RSI не в зоне перекупленности
                if (current_sma_short > current_sma_long and 
                    current_rsi < self.rsi_overbought and
                    current_rsi > 30):  # Не в зоне перепроданности
                    return {
                        'trend': 'bullish',
                        'price': current_price,
                        'confidence': self._calculate_confidence(data, 'bullish'),
                        'rsi': current_rsi,
                        'volume_ratio': current_volume / avg_volume
                    }
            
            elif trend == 'bearish':
                # Продаем при пересечении SMA и RSI не в зоне перепроданности
                if (current_sma_short < current_sma_long and 
                    current_rsi > self.rsi_oversold and
                    current_rsi < 70):  # Не в зоне перекупленности
                    return {
                        'trend': 'bearish',
                        'price': current_price,
                        'confidence': self._calculate_confidence(data, 'bearish'),
                        'rsi': current_rsi,
                        'volume_ratio': current_volume / avg_volume
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка поиска точки входа: {e}")
            return None
    
    def _calculate_confidence(self, data: pd.DataFrame, trend: str) -> float:
        """
        Расчет уверенности в сигнале
        
        Args:
            data: Данные для анализа
            trend: Направление тренда
            
        Returns:
            Уверенность от 0 до 1
        """
        try:
            indicators = TechnicalIndicators(data)
            rsi = indicators.rsi(self.rsi_period)
            sma_short = indicators.sma(10)
            sma_long = indicators.sma(20)
            
            current_rsi = rsi.iloc[-1]
            current_sma_short = sma_short.iloc[-1]
            current_sma_long = sma_long.iloc[-1]
            
            confidence = 0.5  # Базовая уверенность
            
            # RSI фактор
            if trend == 'bullish':
                if 30 < current_rsi < 50:
                    confidence += 0.2
                elif 50 <= current_rsi < 70:
                    confidence += 0.1
            else:  # bearish
                if 50 < current_rsi < 70:
                    confidence += 0.2
                elif 30 <= current_rsi < 50:
                    confidence += 0.1
            
            # SMA фактор
            sma_diff = abs(current_sma_short - current_sma_long) / current_sma_long
            if sma_diff > 0.01:  # Разница больше 1%
                confidence += 0.1
            
            # Объем фактор
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > 1.5:
                confidence += 0.1
            elif volume_ratio > 1.2:
                confidence += 0.05
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Ошибка расчета уверенности: {e}")
            return 0.5
    
    def _create_signal(self, entry_info: Dict, data: pd.DataFrame) -> Optional[TradingSignal]:
        """
        Создание торгового сигнала
        
        Args:
            entry_info: Информация о точке входа
            data: Данные 5m таймфрейма
            
        Returns:
            TradingSignal или None
        """
        try:
            trend = entry_info['trend']
            price = entry_info['price']
            confidence = entry_info['confidence']
            
            # Определяем тип сигнала
            signal_type = SignalType.BUY if trend == 'bullish' else SignalType.SELL
            
            # Определяем силу сигнала
            if confidence >= 0.8:
                strength = SignalStrength.STRONG
            elif confidence >= 0.6:
                strength = SignalStrength.MEDIUM
            else:
                strength = SignalStrength.WEAK
            
            # Рассчитываем стоп-лосс и тейк-профит
            atr = TechnicalIndicators(data).atr(14).iloc[-1]
            if not pd.isna(atr):
                if signal_type == SignalType.BUY:
                    stop_loss = price - (atr * 2)
                    take_profit = price + (atr * 3)
                else:
                    stop_loss = price + (atr * 2)
                    take_profit = price - (atr * 3)
            else:
                stop_loss = None
                take_profit = None
            
            # Создаем сигнал
            signal = TradingSignal(
                symbol=data.attrs.get('symbol', 'UNKNOWN'),
                signal_type=signal_type,
                strength=strength,
                price=price,
                timestamp=datetime.now(),
                timeframe='5m',
                strategy_name=self.name,
                confidence=confidence,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    'rsi': entry_info.get('rsi'),
                    'volume_ratio': entry_info.get('volume_ratio'),
                    'atr': atr if not pd.isna(atr) else None
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка создания сигнала: {e}")
            return None

