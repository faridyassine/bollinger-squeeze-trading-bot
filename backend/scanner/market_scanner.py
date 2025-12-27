"""Multi-symbol parallel market scanner."""
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from datetime import datetime, timedelta
import pandas as pd
from backend.core.config import config
from backend.core.logging_config import get_logger
from backend.data import YahooFinanceProvider
from backend.indicators import SqueezeDetector

logger = get_logger(__name__)


class MarketScanner:
    """Scans multiple symbols for squeeze patterns in parallel."""
    
    def __init__(self, symbols: List[str] = None, max_workers: int = 10):
        """Initialize market scanner.
        
        Args:
            symbols: List of symbols to scan (default: from config)
            max_workers: Maximum parallel workers
        """
        self.symbols = symbols or config.watchlist.get('symbols', [])
        # Validate and limit max_workers
        cpu_limit = os.cpu_count() * 2 if os.cpu_count() else 10
        self.max_workers = min(max_workers, len(self.symbols) if self.symbols else 10, cpu_limit)
        self.data_provider = YahooFinanceProvider(cache_enabled=True)
        
        # Get strategy params from config
        strategy_config = config.strategy.get('bollinger_squeeze', {})
        self.detector = SqueezeDetector(
            bollinger_period=strategy_config.get('bollinger_period', 20),
            bollinger_std=strategy_config.get('bollinger_std', 2.0),
            squeeze_threshold=strategy_config.get('squeeze_threshold', 0.5),
            min_days_in_squeeze=strategy_config.get('min_days_in_squeeze', 2),
            max_days_in_squeeze=strategy_config.get('max_days_in_squeeze', 10)
        )
        
        # Scanner filters
        scanner_config = config.scanner.get('filters', {})
        self.min_price = scanner_config.get('min_price', 10.0)
        self.max_price = scanner_config.get('max_price', 1000.0)
        self.min_volume = scanner_config.get('min_volume', 1000000)
    
    def scan_symbol(self, symbol: str) -> Dict:
        """Scan a single symbol for squeeze pattern.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with scan results
        """
        try:
            logger.debug(f"Scanning {symbol}")
            
            # Download historical data (6 months)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)
            data = self.data_provider.get_historical_data(
                symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if data.empty or len(data) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Get current price and volume
            current_price = float(data['close'].iloc[-1])
            current_volume = float(data['volume'].iloc[-1])
            avg_volume = float(data['volume'].tail(20).mean())
            
            # Apply filters
            if current_price < self.min_price or current_price > self.max_price:
                logger.debug(f"{symbol} filtered by price: ${current_price:.2f}")
                return None
            
            if avg_volume < self.min_volume:
                logger.debug(f"{symbol} filtered by volume: {avg_volume:.0f}")
                return None
            
            # Analyze squeeze
            squeeze_result = self.detector.analyze(data)
            
            if not squeeze_result['in_squeeze']:
                logger.debug(f"{symbol} not in squeeze")
                return None
            
            # Add symbol info
            squeeze_result['symbol'] = symbol
            squeeze_result['timestamp'] = datetime.now()
            squeeze_result['avg_volume'] = avg_volume
            
            logger.info(f"✓ Squeeze found: {symbol} - Strength: {squeeze_result['squeeze_strength']:.0f}, "
                       f"Days: {squeeze_result['days_in_squeeze']}")
            
            return squeeze_result
        
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None
    
    def scan_market(self, symbols: List[str] = None) -> List[Dict]:
        """Scan multiple symbols in parallel.
        
        Args:
            symbols: List of symbols to scan (default: self.symbols)
            
        Returns:
            List of squeeze results sorted by strength
        """
        symbols = symbols or self.symbols
        
        logger.info(f"Starting market scan of {len(symbols)} symbols with {self.max_workers} workers")
        start_time = time.time()
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.scan_symbol, symbol): symbol
                for symbol in symbols
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
        
        # Sort by squeeze strength
        results.sort(key=lambda x: x['squeeze_strength'], reverse=True)
        
        elapsed = time.time() - start_time
        logger.info(f"Market scan complete: {len(results)} squeezes found in {elapsed:.1f}s")
        
        return results
    
    def get_top_opportunities(self, n: int = 10) -> List[Dict]:
        """Get top N squeeze opportunities.
        
        Args:
            n: Number of top opportunities to return
            
        Returns:
            List of top squeeze opportunities
        """
        results = self.scan_market()
        return results[:n]
    
    def scan_single_symbol_detailed(self, symbol: str) -> Dict:
        """Get detailed scan result for a single symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Detailed squeeze analysis
        """
        result = self.scan_symbol(symbol)
        
        if not result:
            return {
                'symbol': symbol,
                'in_squeeze': False,
                'message': 'No squeeze detected or symbol filtered out'
            }
        
        return result
