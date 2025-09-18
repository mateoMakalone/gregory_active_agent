"""
Технические индикаторы для анализа рынка
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib не установлен, используются собственные реализации индикаторов")


class TechnicalIndicators:
    """Класс для расчета технических индикаторов"""
    
    def __init__(self, data: pd.DataFrame):
        """
        Инициализация с данными
        
        Args:
            data: DataFrame с OHLCV данными
        """
        self.data = data.copy()
        self._validate_data()
    
    def _validate_data(self):
        """Валидация входных данных"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"Отсутствуют необходимые колонки: {missing_columns}")
        
        if self.data.empty:
            raise ValueError("Данные пусты")
    
    def sma(self, period: int, column: str = 'close') -> pd.Series:
        """Простое скользящее среднее"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.SMA(self.data[column].values, timeperiod=period), 
                           index=self.data.index)
        else:
            return self.data[column].rolling(window=period).mean()
    
    def ema(self, period: int, column: str = 'close') -> pd.Series:
        """Экспоненциальное скользящее среднее"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.EMA(self.data[column].values, timeperiod=period), 
                           index=self.data.index)
        else:
            return self.data[column].ewm(span=period).mean()
    
    def rsi(self, period: int = 14) -> pd.Series:
        """Индекс относительной силы (RSI)"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.RSI(self.data['close'].values, timeperiod=period), 
                           index=self.data.index)
        else:
            return self._calculate_rsi(period)
    
    def _calculate_rsi(self, period: int) -> pd.Series:
        """Собственная реализация RSI"""
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def bollinger_bands(self, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Полосы Боллинджера"""
        if TALIB_AVAILABLE:
            upper, middle, lower = talib.BBANDS(
                self.data['close'].values, 
                timeperiod=period, 
                nbdevup=std_dev, 
                nbdevdn=std_dev
            )
            return (pd.Series(upper, index=self.data.index),
                    pd.Series(middle, index=self.data.index),
                    pd.Series(lower, index=self.data.index))
        else:
            return self._calculate_bollinger_bands(period, std_dev)
    
    def _calculate_bollinger_bands(self, period: int, std_dev: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Собственная реализация полос Боллинджера"""
        middle = self.sma(period)
        std = self.data['close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        if TALIB_AVAILABLE:
            macd_line, signal_line, histogram = talib.MACD(
                self.data['close'].values, 
                fastperiod=fast, 
                slowperiod=slow, 
                signalperiod=signal
            )
            return (pd.Series(macd_line, index=self.data.index),
                    pd.Series(signal_line, index=self.data.index),
                    pd.Series(histogram, index=self.data.index))
        else:
            return self._calculate_macd(fast, slow, signal)
    
    def _calculate_macd(self, fast: int, slow: int, signal: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Собственная реализация MACD"""
        ema_fast = self.ema(fast)
        ema_slow = self.ema(slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def stochastic(self, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Стохастический осциллятор"""
        if TALIB_AVAILABLE:
            k_percent, d_percent = talib.STOCH(
                self.data['high'].values,
                self.data['low'].values,
                self.data['close'].values,
                fastk_period=k_period,
                slowk_period=d_period,
                slowd_period=d_period
            )
            return (pd.Series(k_percent, index=self.data.index),
                    pd.Series(d_percent, index=self.data.index))
        else:
            return self._calculate_stochastic(k_period, d_period)
    
    def _calculate_stochastic(self, k_period: int, d_period: int) -> Tuple[pd.Series, pd.Series]:
        """Собственная реализация стохастического осциллятора"""
        lowest_low = self.data['low'].rolling(window=k_period).min()
        highest_high = self.data['high'].rolling(window=k_period).max()
        k_percent = 100 * ((self.data['close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent
    
    def atr(self, period: int = 14) -> pd.Series:
        """Average True Range (ATR)"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.ATR(self.data['high'].values, 
                                     self.data['low'].values, 
                                     self.data['close'].values, 
                                     timeperiod=period), 
                           index=self.data.index)
        else:
            return self._calculate_atr(period)
    
    def _calculate_atr(self, period: int) -> pd.Series:
        """Собственная реализация ATR"""
        high_low = self.data['high'] - self.data['low']
        high_close = np.abs(self.data['high'] - self.data['close'].shift())
        low_close = np.abs(self.data['low'] - self.data['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def williams_r(self, period: int = 14) -> pd.Series:
        """Williams %R"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.WILLR(self.data['high'].values,
                                       self.data['low'].values,
                                       self.data['close'].values,
                                       timeperiod=period),
                           index=self.data.index)
        else:
            return self._calculate_williams_r(period)
    
    def _calculate_williams_r(self, period: int) -> pd.Series:
        """Собственная реализация Williams %R"""
        highest_high = self.data['high'].rolling(window=period).max()
        lowest_low = self.data['low'].rolling(window=period).min()
        williams_r = -100 * ((highest_high - self.data['close']) / (highest_high - lowest_low))
        return williams_r
    
    def adx(self, period: int = 14) -> pd.Series:
        """Average Directional Index (ADX)"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.ADX(self.data['high'].values,
                                     self.data['low'].values,
                                     self.data['close'].values,
                                     timeperiod=period),
                           index=self.data.index)
        else:
            return self._calculate_adx(period)
    
    def _calculate_adx(self, period: int) -> pd.Series:
        """Собственная реализация ADX"""
        # Упрощенная реализация ADX
        high_low = self.data['high'] - self.data['low']
        high_close = np.abs(self.data['high'] - self.data['close'].shift())
        low_close = np.abs(self.data['low'] - self.data['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        
        # Упрощенный расчет ADX
        adx = atr.rolling(window=period).mean() / self.data['close'] * 100
        return adx
    
    def calculate_all_indicators(self, config: Dict) -> pd.DataFrame:
        """
        Расчет всех индикаторов согласно конфигурации
        
        Args:
            config: Конфигурация индикаторов
            
        Returns:
            DataFrame с рассчитанными индикаторами
        """
        result = self.data.copy()
        
        try:
            # SMA
            sma_periods = config.get('sma', {}).get('periods', [])
            for period in sma_periods:
                result[f'sma_{period}'] = self.sma(period)
            
            # EMA
            ema_periods = config.get('ema', {}).get('periods', [])
            for period in ema_periods:
                result[f'ema_{period}'] = self.ema(period)
            
            # RSI
            rsi_config = config.get('rsi', {})
            if rsi_config:
                period = rsi_config.get('period', 14)
                result['rsi'] = self.rsi(period)
            
            # Bollinger Bands
            bb_config = config.get('bollinger', {})
            if bb_config:
                period = bb_config.get('period', 20)
                std_dev = bb_config.get('std_dev', 2)
                bb_upper, bb_middle, bb_lower = self.bollinger_bands(period, std_dev)
                result['bb_upper'] = bb_upper
                result['bb_middle'] = bb_middle
                result['bb_lower'] = bb_lower
            
            # MACD
            macd_config = config.get('macd', {})
            if macd_config:
                fast = macd_config.get('fast', 12)
                slow = macd_config.get('slow', 26)
                signal = macd_config.get('signal', 9)
                macd_line, signal_line, histogram = self.macd(fast, slow, signal)
                result['macd'] = macd_line
                result['macd_signal'] = signal_line
                result['macd_histogram'] = histogram
            
            # Stochastic
            stoch_config = config.get('stochastic', {})
            if stoch_config:
                k_period = stoch_config.get('k_period', 14)
                d_period = stoch_config.get('d_period', 3)
                k_percent, d_percent = self.stochastic(k_period, d_period)
                result['stoch_k'] = k_percent
                result['stoch_d'] = d_percent
            
            # ATR
            atr_config = config.get('atr', {})
            if atr_config:
                period = atr_config.get('period', 14)
                result['atr'] = self.atr(period)
            
            # Williams %R
            williams_config = config.get('williams', {})
            if williams_config:
                period = williams_config.get('period', 14)
                result['williams_r'] = self.williams_r(period)
            
            # ADX
            adx_config = config.get('adx', {})
            if adx_config:
                period = adx_config.get('period', 14)
                result['adx'] = self.adx(period)
            
            logger.info(f"Рассчитаны индикаторы для {len(result)} свечей")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета индикаторов: {e}")
            raise

