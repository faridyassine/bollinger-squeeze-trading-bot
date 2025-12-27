"""Yahoo Finance data provider implementation."""
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from .market_data import MarketDataProvider
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance data provider."""
    
    def __init__(self, cache_enabled: bool = True):
        """Initialize Yahoo Finance provider.
        
        Args:
            cache_enabled: Enable caching of data
        """
        self.cache_enabled = cache_enabled
        self._cache = {}
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data from Yahoo Finance.
        
        Args:
            symbol: Stock symbol
            start_date: Start date for data (default: 1 year ago)
            end_date: End date for data (default: today)
            interval: Data interval (1d, 1h, 15m, etc.)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        try:
            # Default date range
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=365)
            
            # Check cache
            cache_key = f"{symbol}_{start_date}_{end_date}_{interval}"
            if self.cache_enabled and cache_key in self._cache:
                logger.debug(f"Cache hit for {symbol}")
                return self._cache[cache_key].copy()
            
            # Download data
            logger.info(f"Downloading data for {symbol} from {start_date} to {end_date}")
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            
            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Standardize column names
            data = data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Keep only OHLCV columns
            data = data[['open', 'high', 'low', 'close', 'volume']]
            
            # Cache data
            if self.cache_enabled:
                self._cache[cache_key] = data.copy()
            
            logger.info(f"Downloaded {len(data)} rows for {symbol}")
            return data
        
        except Exception as e:
            logger.error(f"Error downloading data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_latest_price(self, symbol: str) -> float:
        """Get latest price for symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if data.empty:
                logger.warning(f"No price data for {symbol}")
                return 0.0
            
            price = float(data['Close'].iloc[-1])
            logger.debug(f"Latest price for {symbol}: {price}")
            return price
        
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return 0.0
    
    def get_multiple_prices(self, symbols: list[str]) -> dict[str, float]:
        """Get latest prices for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbol to price
        """
        prices = {}
        
        try:
            # Download data for all symbols at once
            data = yf.download(
                symbols,
                period="1d",
                interval="1m",
                group_by='ticker',
                threads=True,
                progress=False
            )
            
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        symbol_data = data
                    else:
                        symbol_data = data[symbol]
                    
                    if not symbol_data.empty:
                        prices[symbol] = float(symbol_data['Close'].iloc[-1])
                    else:
                        prices[symbol] = 0.0
                
                except Exception as e:
                    logger.error(f"Error parsing price for {symbol}: {e}")
                    prices[symbol] = 0.0
        
        except Exception as e:
            logger.error(f"Error downloading multiple prices: {e}")
            # Fallback to individual downloads
            for symbol in symbols:
                prices[symbol] = self.get_latest_price(symbol)
        
        return prices
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()
        logger.info("Cache cleared")
