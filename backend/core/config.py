"""Configuration management for trading bot."""
import os
import yaml
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv
import string


class Config:
    """Configuration loader with environment variable interpolation."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        load_dotenv()
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Interpolate environment variables
        return self._interpolate_env(config)
    
    def _interpolate_env(self, obj: Any) -> Any:
        """Recursively interpolate environment variables in config.
        
        Replaces ${VAR_NAME} with value from environment.
        """
        if isinstance(obj, dict):
            return {k: self._interpolate_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._interpolate_env(item) for item in obj]
        elif isinstance(obj, str):
            # Replace ${VAR} with environment variable value
            template = string.Template(obj)
            try:
                return template.substitute(os.environ)
            except KeyError:
                # Keep original if env var not found
                return obj
        else:
            return obj
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key.
        
        Args:
            key: Dot-separated key (e.g., 'strategy.bollinger_squeeze.enabled')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def reload(self):
        """Reload configuration from file."""
        self._config = self._load_config()
    
    @property
    def data(self) -> Dict[str, Any]:
        """Get data configuration."""
        return self._config.get('data', {})
    
    @property
    def watchlist(self) -> Dict[str, Any]:
        """Get watchlist configuration."""
        return self._config.get('watchlist', {})
    
    @property
    def strategy(self) -> Dict[str, Any]:
        """Get strategy configuration."""
        return self._config.get('strategy', {})
    
    @property
    def scanner(self) -> Dict[str, Any]:
        """Get scanner configuration."""
        return self._config.get('scanner', {})
    
    @property
    def alerts(self) -> Dict[str, Any]:
        """Get alerts configuration."""
        return self._config.get('alerts', {})
    
    @property
    def backtesting(self) -> Dict[str, Any]:
        """Get backtesting configuration."""
        return self._config.get('backtesting', {})
    
    @property
    def api(self) -> Dict[str, Any]:
        """Get API configuration."""
        return self._config.get('api', {})
    
    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self._config.get('database', {})
    
    @property
    def logging(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config.get('logging', {})


# Global config instance
config = Config()
