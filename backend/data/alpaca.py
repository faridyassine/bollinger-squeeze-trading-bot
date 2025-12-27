"""Alpaca data provider implementation."""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import alpaca_trade_api as tradeapi
from .market_data import MarketDataProvider
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class AlpacaDataProvider(MarketDataProvider):
    """Alpaca market data provider with real-time data and high rate limits."""
    
    def __init__(self):
        """Initialize Alpaca provider with API credentials from environment."""
        # Load credentials from environment
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.paper = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
        
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API credentials not found. "
                "Please set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
            )
        
        # Determine base URL based on paper vs live trading
        base_url = 'https://paper-api.alpaca.markets' if self.paper else 'https://api.alpaca.markets'
        
        # Initialize Alpaca REST API client
        try:
            self.api = tradeapi.REST(
                self.api_key,
                self.secret_key,
                base_url,
                api_version='v2'
            )
            logger.info(f"Alpaca provider initialized (Paper: {self.paper})")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API: {e}")
            raise
    
    def _convert_period_to_dates(self, period: str) -> tuple:
        """Convert period string to start and end dates.
        
        Args:
            period: Period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            Tuple of (start_date, end_date)
        """
        end_date = datetime.now()
        
        period_map = {
            '1d': timedelta(days=1),
            '5d': timedelta(days=5),
            '1mo': timedelta(days=30),
            '3mo': timedelta(days=90),
            '6mo': timedelta(days=180),
            '1y': timedelta(days=365),
            '2y': timedelta(days=730),
            '5y': timedelta(days=1825),
            '10y': timedelta(days=3650),
            'ytd': None,  # Special case: year to date
            'max': timedelta(days=7300)  # ~20 years
        }
        
        if period == 'ytd':
            start_date = datetime(end_date.year, 1, 1)
        elif period in period_map:
            delta = period_map[period]
            start_date = end_date - delta
        else:
            # Default to 6 months if unknown period
            logger.warning(f"Unknown period '{period}', defaulting to 6 months")
            start_date = end_date - timedelta(days=180)
        
        return start_date, end_date
    
    def _convert_timeframe_to_alpaca(self, timeframe: str) -> str:
        """Convert timeframe to Alpaca format.
        
        Args:
            timeframe: Timeframe string (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)
            
        Returns:
            Alpaca timeframe string (1Min, 5Min, 15Min, 1Hour, 1Day, 1Week, 1Month)
        """
        timeframe_map = {
            '1m': '1Min',
            '5m': '5Min',
            '15m': '15Min',
            '30m': '30Min',
            '1h': '1Hour',
            '1d': '1Day',
            '1wk': '1Week',
            '1mo': '1Month'
        }
        
        alpaca_timeframe = timeframe_map.get(timeframe)
        if not alpaca_timeframe:
            logger.warning(f"Unknown timeframe '{timeframe}', defaulting to 1Day")
            alpaca_timeframe = '1Day'
        
        return alpaca_timeframe
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data from Alpaca.
        
        Args:
            symbol: Stock symbol
            start_date: Start date for data (default: 1 year ago)
            end_date: End date for data (default: today)
            interval: Data interval (1d, 1h, 15m, etc.)
            
        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        try:
            # Default date range
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=365)
            
            # Convert timeframe to Alpaca format
            alpaca_timeframe = self._convert_timeframe_to_alpaca(interval)
            
            logger.info(f"Fetching {symbol} data from {start_date.date()} to {end_date.date()} ({alpaca_timeframe})")
            
            # Fetch bars using Alpaca API
            bars = self.api.get_bars(
                symbol,
                alpaca_timeframe,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                adjustment='raw'
            ).df
            
            if bars.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Alpaca returns data with timezone info, remove it for consistency
            if bars.index.tz is not None:
                bars.index = bars.index.tz_localize(None)
            
            # Standardize column names to lowercase (Alpaca uses lowercase by default)
            bars = bars.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Keep only OHLCV columns
            bars = bars[['open', 'high', 'low', 'close', 'volume']]
            
            logger.info(f"Retrieved {len(bars)} bars for {symbol}")
            return bars
        
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_data(self, symbol: str, period: str = "6mo", timeframe: str = "1d") -> pd.DataFrame:
        """Get historical data using period-based interface (Yahoo Finance compatible).
        
        Args:
            symbol: Stock symbol
            period: Period string (1d, 5d, 1mo, 6mo, 1y, etc.)
            timeframe: Data timeframe (1m, 5m, 15m, 1h, 1d, 1wk)
            
        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        start_date, end_date = self._convert_period_to_dates(period)
        return self.get_historical_data(symbol, start_date, end_date, timeframe)
    
    def get_latest_price(self, symbol: str) -> float:
        """Get latest price for symbol using Alpaca's latest trade endpoint.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price
        """
        try:
            # Get the latest trade
            trade = self.api.get_latest_trade(symbol)
            price = float(trade.price)
            logger.debug(f"Latest price for {symbol}: ${price:.2f}")
            return price
        
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return 0.0
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbol to price
        """
        prices = {}
        
        try:
            # Alpaca doesn't have a bulk latest trade endpoint, so fetch individually
            for symbol in symbols:
                try:
                    price = self.get_latest_price(symbol)
                    prices[symbol] = price
                except Exception as e:
                    logger.error(f"Error getting price for {symbol}: {e}")
                    prices[symbol] = 0.0
        
        except Exception as e:
            logger.error(f"Error fetching multiple prices: {e}")
            # Ensure all symbols have a value
            for symbol in symbols:
                if symbol not in prices:
                    prices[symbol] = 0.0
        
        return prices
    
    def is_market_open(self) -> bool:
        """Check if the market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        try:
            clock = self.api.get_clock()
            is_open = clock.is_open
            logger.debug(f"Market is {'open' if is_open else 'closed'}")
            return is_open
        
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
