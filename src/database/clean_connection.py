"""
Чистый менеджер подключений к базам данных без loop на уровне модуля
"""

from __future__ import annotations
from typing import Optional, Dict, Any, Union
from pathlib import Path
from loguru import logger

import sqlite3
import asyncio

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg не установлен, PostgreSQL недоступен")

from ..core.config import config


class CleanDatabaseManager:
    """Чистый менеджер для работы с базами данных без loop на уровне модуля"""
    
    def __init__(self):
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        self.db_type = config.get('database.type', 'sqlite')
        self.db_url = config.get('database.url', 'sqlite:///data/trading_agent.db')
        
    async def connect(self) -> bool:
        """Подключение к базе данных"""
        try:
            if self.db_type == 'postgresql' and ASYNCPG_AVAILABLE:
                return await self._connect_postgresql()
            else:
                return await self._connect_sqlite()
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return False
    
    async def _connect_postgresql(self) -> bool:
        """Подключение к PostgreSQL"""
        try:
            # Парсим URL подключения
            db_url = self.db_url.replace('postgresql://', '')
            if '@' in db_url:
                auth, host_db = db_url.split('@')
                user, password = auth.split(':')
                host, db = host_db.split('/')
            else:
                user = config.get('database.user', 'postgres')
                password = config.get('database.password', 'password')
                host = config.get('database.host', 'localhost')
                db = config.get('database.name', 'trading_agent')
            
            # Создаем пул подключений
            self.postgres_pool = await asyncpg.create_pool(
                host=host,
                port=config.get('database.port', 5432),
                user=user,
                password=password,
                database=db,
                min_size=1,
                max_size=10
            )
            
            logger.info(f"Подключение к PostgreSQL установлено: {host}:{db}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            return False
    
    async def _connect_sqlite(self) -> bool:
        """Подключение к SQLite"""
        try:
            # Создаем папку для базы данных
            db_path = Path(self.db_url.replace('sqlite:///', ''))
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Создаем подключение
            self.sqlite_conn = sqlite3.connect(
                str(db_path),
                check_same_thread=False
            )
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # Инициализируем схему в отдельном потоке
            await self._init_sqlite_schema()
            
            logger.info(f"Подключение к SQLite установлено: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к SQLite: {e}")
            return False
    
    async def _init_sqlite_schema(self):
        """Инициализация схемы SQLite"""
        try:
            schema_path = Path(__file__).parent.parent.parent / "ops" / "sql" / "sqlite_schema.sql"
            
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # Выполняем SQL в отдельном потоке
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.sqlite_conn.executescript(schema_sql)
                )
                
                logger.info("Схема SQLite инициализирована")
            else:
                logger.warning(f"Файл схемы не найден: {schema_path}")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации схемы SQLite: {e}")
    
    async def disconnect(self):
        """Отключение от базы данных"""
        try:
            if self.postgres_pool:
                await self.postgres_pool.close()
                self.postgres_pool = None
                logger.info("Отключение от PostgreSQL")
            
            if self.sqlite_conn:
                self.sqlite_conn.close()
                self.sqlite_conn = None
                logger.info("Отключение от SQLite")
                
        except Exception as e:
            logger.error(f"Ошибка отключения от БД: {e}")
    
    def get_connection(self):
        """Получить подключение к БД"""
        if self.db_type == 'postgresql' and self.postgres_pool:
            return self.postgres_pool
        elif self.db_type == 'sqlite' and self.sqlite_conn:
            return self.sqlite_conn
        else:
            raise ConnectionError("База данных не подключена")


# Глобальный экземпляр менеджера
clean_db_manager = CleanDatabaseManager()
