"""Base strategy class with common methods."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str, params: Dict = None):
        """Initialize strategy.
        
        Args:
            name: Strategy name
            params: Strategy parameters
        """
        self.name = name
        self.params = params or {}
        self.positions = []
        self.trades = []
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals.
        
        Args:
            data: DataFrame with OHLCV data and indicators
            
        Returns:
            DataFrame with 'signal' column (1=buy, -1=sell, 0=hold)
        """
        pass
    
    @abstractmethod
    def check_entry_conditions(self, data: pd.DataFrame, index: int) -> Tuple[bool, str]:
        """Check if entry conditions are met.
        
        Args:
            data: DataFrame with market data
            index: Current bar index
            
        Returns:
            Tuple of (should_enter, reason)
        """
        pass
    
    @abstractmethod
    def check_exit_conditions(
        self,
        data: pd.DataFrame,
        index: int,
        entry_price: float,
        entry_date: datetime
    ) -> Tuple[bool, str]:
        """Check if exit conditions are met.
        
        Args:
            data: DataFrame with market data
            index: Current bar index
            entry_price: Entry price of position
            entry_date: Entry date of position
            
        Returns:
            Tuple of (should_exit, reason)
        """
        pass
    
    def calculate_position_size(
        self,
        capital: float,
        price: float,
        risk_per_trade: float = 0.02,
        atr: float = None
    ) -> int:
        """Calculate position size based on risk.
        
        Args:
            capital: Available capital
            price: Entry price
            risk_per_trade: Maximum risk per trade (default: 2%)
            atr: Average True Range for stop loss calculation
            
        Returns:
            Number of shares to buy
        """
        risk_amount = capital * risk_per_trade
        
        if atr and atr > 0:
            # Use ATR-based position sizing
            stop_distance = atr * self.params.get('stop_loss_atr_multiplier', 2.0)
            shares = int(risk_amount / stop_distance)
        else:
            # Use fixed percentage position sizing
            position_size = capital * self.params.get('position_size', 0.1)
            shares = int(position_size / price)
        
        return max(1, shares)
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range.
        
        Args:
            data: DataFrame with OHLCV data
            period: ATR period
            
        Returns:
            Series with ATR values
        """
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_stop_loss(self, entry_price: float, atr: float, side: str = 'LONG') -> float:
        """Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            side: Position side (LONG or SHORT)
            
        Returns:
            Stop loss price
        """
        multiplier = self.params.get('stop_loss_atr_multiplier', 2.0)
        
        if side == 'LONG':
            return entry_price - (atr * multiplier)
        else:
            return entry_price + (atr * multiplier)
    
    def calculate_target(self, entry_price: float, stop_loss: float, side: str = 'LONG') -> float:
        """Calculate profit target price.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: Position side (LONG or SHORT)
            
        Returns:
            Target price
        """
        risk = abs(entry_price - stop_loss)
        reward_multiplier = self.params.get('target_multiplier', 3.0)
        
        if side == 'LONG':
            return entry_price + (risk * reward_multiplier)
        else:
            return entry_price - (risk * reward_multiplier)
    
    def log_trade(
        self,
        symbol: str,
        side: str,
        entry_date: datetime,
        entry_price: float,
        exit_date: datetime,
        exit_price: float,
        quantity: int,
        reason: str
    ):
        """Log completed trade.
        
        Args:
            symbol: Stock symbol
            side: Position side
            entry_date: Entry date
            entry_price: Entry price
            exit_date: Exit date
            exit_price: Exit price
            quantity: Number of shares
            reason: Exit reason
        """
        pnl = (exit_price - entry_price) * quantity if side == 'LONG' else (entry_price - exit_price) * quantity
        pnl_percent = ((exit_price / entry_price) - 1) * 100 if side == 'LONG' else ((entry_price / exit_price) - 1) * 100
        
        trade = {
            'symbol': symbol,
            'side': side,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'exit_date': exit_date,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'reason': reason
        }
        
        self.trades.append(trade)
        logger.info(f"Trade closed: {symbol} {side} PnL=${pnl:.2f} ({pnl_percent:.2f}%) - {reason}")
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary of all trades.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'avg_pnl_percent': 0,
                'total_pnl': 0
            }
        
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] <= 0]
        
        return {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.trades) * 100,
            'avg_pnl': np.mean([t['pnl'] for t in self.trades]),
            'avg_pnl_percent': np.mean([t['pnl_percent'] for t in self.trades]),
            'total_pnl': sum([t['pnl'] for t in self.trades]),
            'avg_win': np.mean([t['pnl'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl'] for t in losses]) if losses else 0
        }
