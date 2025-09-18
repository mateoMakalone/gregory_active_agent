"""
Модуль конфигурации системы
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class Config:
    """Класс для управления конфигурацией системы"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Загрузка конфигурации из файла"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
            logger.info(f"Конфигурация загружена из {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Файл конфигурации не найден: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Ошибка парсинга YAML: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения конфигурации по ключу
        
        Args:
            key: Ключ конфигурации (поддерживает вложенные ключи через точку)
            default: Значение по умолчанию
            
        Returns:
            Значение конфигурации или значение по умолчанию
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Установка значения конфигурации
        
        Args:
            key: Ключ конфигурации
            value: Новое значение
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        logger.info(f"Конфигурация обновлена: {key} = {value}")
    
    def save_config(self) -> None:
        """Сохранение конфигурации в файл"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self._config, file, default_flow_style=False, allow_unicode=True)
            logger.info(f"Конфигурация сохранена в {self.config_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            raise
    
    @property
    def api_keys(self) -> Dict[str, Dict[str, str]]:
        """Получение API ключей"""
        return self.get('api', {})
    
    @property
    def trading_config(self) -> Dict[str, Any]:
        """Получение торговой конфигурации"""
        return self.get('trading', {})
    
    @property
    def ml_config(self) -> Dict[str, Any]:
        """Получение ML конфигурации"""
        return self.get('ml', {})
    
    @property
    def indicators_config(self) -> Dict[str, Any]:
        """Получение конфигурации индикаторов"""
        return self.get('indicators', {})
    
    @property
    def dashboard_config(self) -> Dict[str, Any]:
        """Получение конфигурации дашборда"""
        return self.get('dashboard', {})
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Получение конфигурации логирования"""
        return self.get('logging', {})


# Глобальный экземпляр конфигурации
config = Config()

