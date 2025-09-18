"""
Веб-дашборд для торгового AI-агента
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Добавляем путь к src в sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.config import config
from src.core.logger import logger
from src.strategies.base_strategy import SignalType, SignalStrength


class TradingDashboard:
    """Класс для веб-дашборда"""
    
    def __init__(self):
        """Инициализация дашборда"""
        self.setup_page_config()
        self.setup_sidebar()
    
    def setup_page_config(self):
        """Настройка страницы"""
        st.set_page_config(
            page_title="Trading AI Agent",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def setup_sidebar(self):
        """Настройка боковой панели"""
        st.sidebar.title("🤖 Trading AI Agent")
        st.sidebar.markdown("---")
        
        # Навигация
        self.page = st.sidebar.selectbox(
            "Выберите страницу",
            ["📊 Обзор", "📈 Графики", "📋 Сигналы", "📊 Аналитика", "⚙️ Настройки"]
        )
        
        st.sidebar.markdown("---")
        
        # Статус системы
        st.sidebar.subheader("Статус системы")
        st.sidebar.success("🟢 Система активна")
        
        # Последнее обновление
        st.sidebar.info(f"🕐 Последнее обновление: {datetime.now().strftime('%H:%M:%S')}")
    
    def run(self):
        """Запуск дашборда"""
        if self.page == "📊 Обзор":
            self.show_overview()
        elif self.page == "📈 Графики":
            self.show_charts()
        elif self.page == "📋 Сигналы":
            self.show_signals()
        elif self.page == "📊 Аналитика":
            self.show_analytics()
        elif self.page == "⚙️ Настройки":
            self.show_settings()
    
    def show_overview(self):
        """Страница обзора"""
        st.title("📊 Обзор системы")
        
        # Основные метрики
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Активных стратегий",
                value="2",
                delta="+1"
            )
        
        with col2:
            st.metric(
                label="Сигналов сегодня",
                value="15",
                delta="+3"
            )
        
        with col3:
            st.metric(
                label="Успешных сделок",
                value="12",
                delta="+2"
            )
        
        with col4:
            st.metric(
                label="Общая прибыль",
                value="+2.4%",
                delta="+0.3%"
            )
        
        st.markdown("---")
        
        # График производительности
        st.subheader("📈 Производительность")
        
        # Создаем тестовые данные
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        performance_data = pd.DataFrame({
            'date': dates,
            'equity': 10000 + (dates - dates[0]).days * 10 + pd.Series(range(len(dates))) * 0.5
        })
        
        fig = px.line(performance_data, x='date', y='equity', title='Кривая капитала')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Последние сигналы
        st.subheader("🔔 Последние сигналы")
        
        # Создаем тестовые данные сигналов
        signals_data = pd.DataFrame({
            'Время': [datetime.now() - timedelta(hours=i) for i in range(5)],
            'Символ': ['EURUSD', 'GBPUSD', 'BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
            'Тип': ['BUY', 'SELL', 'BUY', 'SELL', 'BUY'],
            'Цена': [1.0850, 1.2650, 43250, 2650, 0.4850],
            'Уверенность': [0.85, 0.72, 0.91, 0.68, 0.79],
            'Статус': ['Выполнен', 'Ожидает', 'Выполнен', 'Отменен', 'Ожидает']
        })
        
        st.dataframe(signals_data, use_container_width=True)
    
    def show_charts(self):
        """Страница графиков"""
        st.title("📈 Графики и анализ")
        
        # Выбор инструмента
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbol = st.selectbox("Выберите инструмент", ["EURUSD", "GBPUSD", "BTCUSDT", "ETHUSDT"])
        
        with col2:
            timeframe = st.selectbox("Таймфрейм", ["1m", "5m", "15m", "1h", "4h", "1d"])
        
        with col3:
            period = st.selectbox("Период", ["1 день", "1 неделя", "1 месяц", "3 месяца"])
        
        # Создаем тестовые данные
        if st.button("🔄 Обновить данные"):
            st.success("Данные обновлены!")
        
        # Основной график
        st.subheader(f"📊 {symbol} - {timeframe}")
        
        # Создаем тестовые OHLC данные
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='H')
        base_price = 1.0850 if 'USD' in symbol else 43250
        
        ohlc_data = pd.DataFrame({
            'timestamp': dates,
            'open': base_price + pd.Series(range(len(dates))) * 0.0001,
            'high': base_price + pd.Series(range(len(dates))) * 0.0001 + 0.001,
            'low': base_price + pd.Series(range(len(dates))) * 0.0001 - 0.001,
            'close': base_price + pd.Series(range(len(dates))) * 0.0001 + 0.0005,
            'volume': 1000 + pd.Series(range(len(dates))) * 10
        })
        
        # Создаем свечной график
        fig = go.Figure(data=go.Candlestick(
            x=ohlc_data['timestamp'],
            open=ohlc_data['open'],
            high=ohlc_data['high'],
            low=ohlc_data['low'],
            close=ohlc_data['close'],
            name=symbol
        ))
        
        # Добавляем скользящие средние
        ohlc_data['sma_20'] = ohlc_data['close'].rolling(20).mean()
        ohlc_data['sma_50'] = ohlc_data['close'].rolling(50).mean()
        
        fig.add_trace(go.Scatter(
            x=ohlc_data['timestamp'],
            y=ohlc_data['sma_20'],
            mode='lines',
            name='SMA 20',
            line=dict(color='orange', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=ohlc_data['timestamp'],
            y=ohlc_data['sma_50'],
            mode='lines',
            name='SMA 50',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title=f"{symbol} - {timeframe}",
            xaxis_title="Время",
            yaxis_title="Цена",
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Индикаторы
        st.subheader("📊 Технические индикаторы")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # RSI
            rsi_data = pd.DataFrame({
                'timestamp': ohlc_data['timestamp'],
                'rsi': 50 + pd.Series(range(len(ohlc_data))) * 0.1
            })
            
            fig_rsi = px.line(rsi_data, x='timestamp', y='rsi', title='RSI (14)')
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Перекупленность")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Перепроданность")
            st.plotly_chart(fig_rsi, use_container_width=True)
        
        with col2:
            # MACD
            macd_data = pd.DataFrame({
                'timestamp': ohlc_data['timestamp'],
                'macd': pd.Series(range(len(ohlc_data))) * 0.01,
                'signal': pd.Series(range(len(ohlc_data))) * 0.008,
                'histogram': pd.Series(range(len(ohlc_data))) * 0.002
            })
            
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(x=macd_data['timestamp'], y=macd_data['macd'], name='MACD', line=dict(color='blue')))
            fig_macd.add_trace(go.Scatter(x=macd_data['timestamp'], y=macd_data['signal'], name='Signal', line=dict(color='red')))
            fig_macd.add_trace(go.Bar(x=macd_data['timestamp'], y=macd_data['histogram'], name='Histogram', marker_color='gray'))
            fig_macd.update_layout(title='MACD', height=300)
            st.plotly_chart(fig_macd, use_container_width=True)
    
    def show_signals(self):
        """Страница сигналов"""
        st.title("📋 Торговые сигналы")
        
        # Фильтры
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            signal_type = st.selectbox("Тип сигнала", ["Все", "BUY", "SELL"])
        
        with col2:
            symbol_filter = st.selectbox("Инструмент", ["Все", "EURUSD", "GBPUSD", "BTCUSDT", "ETHUSDT"])
        
        with col3:
            strength_filter = st.selectbox("Сила сигнала", ["Все", "WEAK", "MEDIUM", "STRONG"])
        
        with col4:
            date_range = st.selectbox("Период", ["Сегодня", "Неделя", "Месяц", "Все время"])
        
        # Создаем тестовые данные сигналов
        signals_data = pd.DataFrame({
            'Время': [datetime.now() - timedelta(hours=i) for i in range(20)],
            'Символ': ['EURUSD', 'GBPUSD', 'BTCUSDT', 'ETHUSDT', 'ADAUSDT'] * 4,
            'Тип': ['BUY', 'SELL', 'BUY', 'SELL', 'BUY'] * 4,
            'Цена': [1.0850, 1.2650, 43250, 2650, 0.4850] * 4,
            'Уверенность': [0.85, 0.72, 0.91, 0.68, 0.79] * 4,
            'Сила': ['STRONG', 'MEDIUM', 'STRONG', 'WEAK', 'MEDIUM'] * 4,
            'Стоп-лосс': [1.0800, 1.2700, 42500, 2700, 0.4900] * 4,
            'Тейк-профит': [1.0900, 1.2600, 44000, 2600, 0.4800] * 4,
            'Статус': ['Выполнен', 'Ожидает', 'Выполнен', 'Отменен', 'Ожидает'] * 4
        })
        
        # Применяем фильтры
        if signal_type != "Все":
            signals_data = signals_data[signals_data['Тип'] == signal_type]
        
        if symbol_filter != "Все":
            signals_data = signals_data[signals_data['Символ'] == symbol_filter]
        
        if strength_filter != "Все":
            signals_data = signals_data[signals_data['Сила'] == strength_filter]
        
        # Отображаем таблицу
        st.dataframe(signals_data, use_container_width=True)
        
        # Статистика сигналов
        st.subheader("📊 Статистика сигналов")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_signals = len(signals_data)
            st.metric("Всего сигналов", total_signals)
        
        with col2:
            buy_signals = len(signals_data[signals_data['Тип'] == 'BUY'])
            st.metric("Покупки", buy_signals)
        
        with col3:
            sell_signals = len(signals_data[signals_data['Тип'] == 'SELL'])
            st.metric("Продажи", sell_signals)
    
    def show_analytics(self):
        """Страница аналитики"""
        st.title("📊 Аналитика и отчеты")
        
        # Выбор периода
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Начальная дата", value=datetime.now() - timedelta(days=30))
        
        with col2:
            end_date = st.date_input("Конечная дата", value=datetime.now())
        
        # Основные метрики
        st.subheader("📈 Основные метрики")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Общая доходность", "+12.5%", "+2.1%")
        
        with col2:
            st.metric("Sharpe Ratio", "1.85", "+0.15")
        
        with col3:
            st.metric("Максимальная просадка", "-3.2%", "-0.5%")
        
        with col4:
            st.metric("Коэффициент прибыльности", "68%", "+5%")
        
        # График доходности
        st.subheader("📊 График доходности")
        
        # Создаем тестовые данные
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        returns_data = pd.DataFrame({
            'date': dates,
            'cumulative_return': (dates - dates[0]).days * 0.4 + pd.Series(range(len(dates))) * 0.1
        })
        
        fig = px.line(returns_data, x='date', y='cumulative_return', title='Кумулятивная доходность')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение сигналов по типам
        st.subheader("📊 Распределение сигналов")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Круговая диаграмма типов сигналов
            signal_counts = {'BUY': 45, 'SELL': 35, 'HOLD': 20}
            fig_pie = px.pie(values=list(signal_counts.values()), names=list(signal_counts.keys()), 
                           title='Распределение по типам сигналов')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Столбчатая диаграмма по инструментам
            symbol_counts = {'EURUSD': 25, 'GBPUSD': 20, 'BTCUSDT': 15, 'ETHUSDT': 12, 'ADAUSDT': 8}
            fig_bar = px.bar(x=list(symbol_counts.keys()), y=list(symbol_counts.values()), 
                           title='Сигналы по инструментам')
            st.plotly_chart(fig_bar, use_container_width=True)
    
    def show_settings(self):
        """Страница настроек"""
        st.title("⚙️ Настройки системы")
        
        # Настройки стратегий
        st.subheader("🤖 Настройки стратегий")
        
        with st.expander("Стратегия следования за трендом"):
            col1, col2 = st.columns(2)
            
            with col1:
                trend_sma = st.slider("SMA для тренда", 20, 100, 50)
                confirmation_sma = st.slider("SMA для подтверждения", 10, 50, 20)
            
            with col2:
                rsi_period = st.slider("Период RSI", 5, 30, 14)
                min_confidence = st.slider("Минимальная уверенность", 0.0, 1.0, 0.6)
        
        # Настройки уведомлений
        st.subheader("🔔 Настройки уведомлений")
        
        col1, col2 = st.columns(2)
        
        with col1:
            telegram_enabled = st.checkbox("Включить Telegram уведомления", value=True)
            email_enabled = st.checkbox("Включить email уведомления", value=False)
        
        with col2:
            signal_frequency = st.selectbox("Частота сигналов", ["Все", "Только сильные", "Только средние и сильные"])
            max_signals_per_day = st.number_input("Максимум сигналов в день", 1, 50, 10)
        
        # Настройки риска
        st.subheader("⚠️ Настройки риска")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_position_size = st.slider("Максимальный размер позиции (%)", 0.1, 10.0, 2.0)
            stop_loss_pct = st.slider("Стоп-лосс (%)", 0.1, 5.0, 1.0)
        
        with col2:
            take_profit_pct = st.slider("Тейк-профит (%)", 0.1, 10.0, 2.0)
            max_drawdown = st.slider("Максимальная просадка (%)", 1.0, 20.0, 5.0)
        
        # Кнопки действий
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Сохранить настройки"):
                st.success("Настройки сохранены!")
        
        with col2:
            if st.button("🔄 Сбросить к умолчаниям"):
                st.warning("Настройки сброшены!")
        
        with col3:
            if st.button("📤 Экспорт конфигурации"):
                st.info("Конфигурация экспортирована!")


def main():
    """Главная функция для запуска дашборда"""
    dashboard = TradingDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()

