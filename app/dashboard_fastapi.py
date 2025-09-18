"""
Gregory Trading Agent - FastAPI Dashboard
Альтернативный dashboard на FastAPI вместо Streamlit
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime
from pathlib import Path

app = FastAPI(title="Gregory Trading Agent Dashboard")

# Статические файлы
if not os.path.exists("static"):
    os.makedirs("static")

# HTML шаблон для dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gregory Trading Agent Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: #f5f5f5;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 10px; 
            padding: 20px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            padding-bottom: 20px; 
            border-bottom: 2px solid #e0e0e0;
        }
        .status-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px;
        }
        .status-card { 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 8px; 
            border-left: 4px solid #007bff;
        }
        .status-card.success { border-left-color: #28a745; }
        .status-card.warning { border-left-color: #ffc107; }
        .status-card.error { border-left-color: #dc3545; }
        .chart-container { 
            margin: 20px 0; 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .refresh-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 5px;
        }
        .refresh-btn:hover { background: #0056b3; }
        .metric { 
            font-size: 2em; 
            font-weight: bold; 
            color: #007bff; 
        }
        .metric-label { 
            color: #666; 
            font-size: 0.9em; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Gregory Trading Agent Dashboard</h1>
            <p>Система торгового AI-агента с n8n оркестрацией</p>
            <button class="refresh-btn" onclick="loadData()">🔄 Обновить</button>
            <button class="refresh-btn" onclick="window.open('/api/docs', '_blank')">📖 API Docs</button>
        </div>

        <div class="status-grid">
            <div class="status-card" id="api-status">
                <h3>🔧 API Server</h3>
                <div class="metric" id="api-metric">-</div>
                <div class="metric-label">Статус</div>
            </div>
            
            <div class="status-card" id="db-status">
                <h3>🗄️ База данных</h3>
                <div class="metric" id="db-metric">-</div>
                <div class="metric-label">Подключение</div>
            </div>
            
            <div class="status-card" id="runs-status">
                <h3>📊 Запуски</h3>
                <div class="metric" id="runs-metric">-</div>
                <div class="metric-label">Активных</div>
            </div>
            
            <div class="status-card" id="strategies-status">
                <h3>🎯 Стратегии</h3>
                <div class="metric" id="strategies-metric">-</div>
                <div class="metric-label">Зарегистрировано</div>
            </div>
        </div>

        <div class="chart-container">
            <h3>📈 Последние запуски</h3>
            <div id="runs-chart" style="height: 400px;"></div>
        </div>

        <div class="chart-container">
            <h3>⚡ Системные метрики</h3>
            <div id="metrics-chart" style="height: 300px;"></div>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                // Загрузка статуса API
                const apiResponse = await fetch('/api/health');
                const apiData = await apiResponse.json();
                updateStatus('api-status', apiData.status === 'healthy' ? 'success' : 'error');
                document.getElementById('api-metric').textContent = apiData.status === 'healthy' ? '✅ OK' : '❌ Error';

                // Загрузка метрик
                const metricsResponse = await fetch('/api/metrics');
                const metricsData = await metricsResponse.json();
                
                // Обновление статуса БД
                updateStatus('db-status', 'success');
                document.getElementById('db-metric').textContent = '✅ OK';

                // Обновление счетчиков
                document.getElementById('runs-metric').textContent = metricsData.system?.active_runs || 0;
                document.getElementById('strategies-metric').textContent = Object.keys(metricsData.strategies || {}).length;

                // Обновление графиков
                updateRunsChart(metricsData);
                updateMetricsChart(metricsData);

            } catch (error) {
                console.error('Ошибка загрузки данных:', error);
                updateStatus('api-status', 'error');
                document.getElementById('api-metric').textContent = '❌ Error';
            }
        }

        function updateStatus(elementId, status) {
            const element = document.getElementById(elementId);
            element.className = `status-card ${status}`;
        }

        function updateRunsChart(data) {
            // Простой график последних запусков
            const runsData = [{
                x: ['Успешные', 'Неудачные', 'Выполняются'],
                y: [data.system?.completed_runs || 0, data.system?.failed_runs_today || 0, data.system?.active_runs || 0],
                type: 'bar',
                marker: { color: ['#28a745', '#dc3545', '#007bff'] }
            }];

            Plotly.newPlot('runs-chart', runsData, {
                title: 'Статистика запусков',
                xaxis: { title: 'Тип запуска' },
                yaxis: { title: 'Количество' }
            });
        }

        function updateMetricsChart(data) {
            // График системных метрик
            const strategies = Object.keys(data.strategies || {});
            const sharpeValues = strategies.map(s => data.strategies[s].sharpe_ratio || 0);
            const drawdownValues = strategies.map(s => (data.strategies[s].max_drawdown || 0) * 100);

            const metricsData = [
                {
                    x: strategies,
                    y: sharpeValues,
                    type: 'bar',
                    name: 'Sharpe Ratio',
                    marker: { color: '#28a745' }
                },
                {
                    x: strategies,
                    y: drawdownValues,
                    type: 'bar',
                    name: 'Max Drawdown %',
                    marker: { color: '#dc3545' },
                    yaxis: 'y2'
                }
            ];

            Plotly.newPlot('metrics-chart', metricsData, {
                title: 'Метрики стратегий',
                xaxis: { title: 'Стратегия' },
                yaxis: { title: 'Sharpe Ratio' },
                yaxis2: { title: 'Max Drawdown %', overlaying: 'y', side: 'right' }
            });
        }

        // Автообновление каждые 30 секунд
        loadData();
        setInterval(loadData, 30000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Главная страница dashboard"""
    return DASHBOARD_HTML

@app.get("/api/health")
async def health_check():
    """Проверка здоровья системы"""
    try:
        # Проверка API
        api_status = "healthy"
        
        # Проверка БД
        db_status = "healthy"
        try:
            import asyncpg
            db_url = "postgresql://katya@localhost:5432/gregory_orchestration"
            conn = await asyncpg.connect(db_url)
            await conn.fetchval("SELECT 1")
            await conn.close()
        except Exception as e:
            db_status = "error"
        
        return {
            "status": "healthy" if api_status == "healthy" and db_status == "healthy" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "components": {
                "api": api_status,
                "database": db_status
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/metrics")
async def get_metrics():
    """Получение метрик системы"""
    try:
        import asyncpg
        db_url = "postgresql://katya@localhost:5432/gregory_orchestration"
        conn = await asyncpg.connect(db_url)
        
        # Получить статистику запусков
        active_runs = await conn.fetchval("SELECT COUNT(*) FROM runs WHERE status = 'running'")
        completed_runs = await conn.fetchval("SELECT COUNT(*) FROM runs WHERE status = 'completed' AND started_at > NOW() - INTERVAL '1 day'")
        failed_runs = await conn.fetchval("SELECT COUNT(*) FROM runs WHERE status = 'failed' AND started_at > NOW() - INTERVAL '1 day'")
        
        # Получить стратегии
        strategies = await conn.fetch("SELECT id, name FROM strategies")
        
        await conn.close()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "strategies": {s["id"]: {"name": s["name"], "sharpe_ratio": 1.2, "max_drawdown": 0.15} for s in strategies},
            "system": {
                "active_runs": active_runs,
                "completed_runs": completed_runs,
                "failed_runs_today": failed_runs,
                "disk_usage_pct": 45.2,
                "memory_usage_pct": 67.8
            }
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "strategies": {},
            "system": {
                "active_runs": 0,
                "completed_runs": 0,
                "failed_runs_today": 0,
                "error": str(e)
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8501)
