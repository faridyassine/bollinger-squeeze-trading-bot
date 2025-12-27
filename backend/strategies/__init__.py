"""Trading strategies package."""
from .base import BaseStrategy
from .bollinger_squeeze import BollingerSqueezeStrategy

__all__ = ['BaseStrategy', 'BollingerSqueezeStrategy']
