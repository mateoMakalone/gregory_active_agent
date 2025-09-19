"""
Управление подключениями к базам данных
"""

import sqlite3
import asyncio
from typing import Optional, Dict, Any, Union
from pathlib import Path
from loguru import logger

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg не установлен, PostgreSQL недоступен")

from ..core.config import config


class DatabaseManager:
    """Менеджер для работы с базами данных"""
    
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
                password = config.get('database.password', '')
                host = config.get('database.host', 'localhost')
                db = config.get('database.name', 'trading_agent')
            
            # Создаем пул подключений
            self.postgres_pool = await asyncpg.create_pool(
                user=user,
                password=password,
                host=host,
                database=db,
                min_size=1,
                max_size=10
            )
            
            logger.info("Подключение к PostgreSQL установлено")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            return False
    
    async def _connect_sqlite(self) -> bool:
        """Подключение к SQLite"""
        try:
            # Извлекаем путь к файлу из URL
            db_path = self.db_url.replace('sqlite:///', '')
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Создаем подключение
            self.sqlite_conn = sqlite3.connect(
                str(db_path),
                check_same_thread=False
            )
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # Инициализируем схему
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
                logger.warning("Файл схемы SQLite не найден")
                
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
    
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Выполнение SQL запроса"""
        try:
            if self.postgres_pool:
                async with self.postgres_pool.acquire() as conn:
                    return await conn.fetch(query, *params)
            elif self.sqlite_conn:
                # Выполняем в отдельном потоке
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: self.sqlite_conn.execute(query, params).fetchall()
                )
            else:
                raise ConnectionError("Нет подключения к БД")
                
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
    
    async def execute_one(self, query: str, params: tuple = ()) -> Any:
        """Выполнение SQL запроса с возвратом одной записи"""
        try:
            if self.postgres_pool:
                async with self.postgres_pool.acquire() as conn:
                    return await conn.fetchrow(query, *params)
            elif self.sqlite_conn:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.sqlite_conn.execute(query, params).fetchone()
                )
                return result
            else:
                raise ConnectionError("Нет подключения к БД")
                
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
    
    async def execute_many(self, query: str, params_list: list) -> Any:
        """Выполнение SQL запроса с множественными параметрами"""
        try:
            if self.postgres_pool:
                async with self.postgres_pool.acquire() as conn:
                    return await conn.executemany(query, params_list)
            elif self.sqlite_conn:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: self.sqlite_conn.executemany(query, params_list)
                )
            else:
                raise ConnectionError("Нет подключения к БД")
                
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
    
    async def commit(self):
        """Подтверждение транзакции"""
        try:
            if self.sqlite_conn:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.sqlite_conn.commit)
            # PostgreSQL автоматически коммитит в asyncpg
                
        except Exception as e:
            logger.error(f"Ошибка коммита: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.sqlite_conn is not None or self.postgres_pool is not None


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()
