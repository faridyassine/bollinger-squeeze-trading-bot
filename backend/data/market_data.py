"""Base market data provider interface."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict
import pandas as pd


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data.
        
        Args:
            symbol: Stock symbol
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval (1d, 1h, 15m, etc.)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        pass
    
    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        """Get latest price for symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price
        """
        pass
    
    @abstractmethod
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbol to price
        """
        pass
