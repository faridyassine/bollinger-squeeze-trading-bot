"""Core backtesting simulation engine."""
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from backend.core.logging_config import get_logger
from backend.strategies.base import BaseStrategy

logger = get_logger(__name__)


class BacktestEngine:
    """Event-driven backtesting engine."""
    
    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005
    ):
        """Initialize backtest engine.
        
        Args:
            strategy: Trading strategy to backtest
            initial_capital: Starting capital
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.0005 = 0.05%)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        # Portfolio state
        self.capital = initial_capital
        self.equity = initial_capital
        self.positions = {}  # symbol -> position info
        self.trades = []
        self.equity_curve = []
        
        # Performance tracking
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
    
    def run(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Run backtest on historical data.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest for {symbol} with {len(data)} bars")
        
        # Reset state
        self.capital = self.initial_capital
        self.equity = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.peak_equity = self.initial_capital
        self.max_drawdown = 0.0
        
        # Generate signals
        data_with_signals = self.strategy.generate_signals(data)
        
        # Simulate trading
        for i in range(len(data_with_signals)):
            bar = data_with_signals.iloc[i]
            date = data_with_signals.index[i]
            
            # Update equity curve
            self._update_equity(symbol, bar['close'])
            
            # Check exit conditions for open positions
            if symbol in self.positions:
                self._check_exit(symbol, data_with_signals, i)
            
            # Check entry conditions
            if symbol not in self.positions:
                self._check_entry(symbol, data_with_signals, i)
        
        # Close any remaining positions
        if symbol in self.positions:
            last_bar = data_with_signals.iloc[-1]
            self._close_position(
                symbol,
                last_bar['close'],
                data_with_signals.index[-1],
                "End of backtest"
            )
        
        # Calculate results
        results = self._calculate_results(symbol, data_with_signals)
        
        logger.info(f"Backtest complete: {len(self.trades)} trades, "
                   f"Total Return: {results['total_return']:.2f}%, "
                   f"Win Rate: {results['win_rate']:.1f}%")
        
        return results
    
    def _check_entry(self, symbol: str, data: pd.DataFrame, index: int):
        """Check and execute entry signals.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with market data
            index: Current bar index
        """
        should_enter, reason = self.strategy.check_entry_conditions(data, index)
        
        if should_enter:
            bar = data.iloc[index]
            date = data.index[index]
            
            # Calculate position size
            price = bar['close']
            atr = bar.get('atr', price * 0.02)  # Default to 2% of price if no ATR
            
            shares = self.strategy.calculate_position_size(
                self.capital,
                price,
                risk_per_trade=0.02,
                atr=atr
            )
            
            # Apply slippage
            entry_price = price * (1 + self.slippage)
            
            # Check if we have enough capital
            cost = entry_price * shares * (1 + self.commission)
            if cost > self.capital:
                logger.warning(f"Insufficient capital for {symbol}: need ${cost:.2f}, have ${self.capital:.2f}")
                return
            
            # Open position
            self.capital -= cost
            
            # Calculate stop loss and target
            stop_loss = self.strategy.calculate_stop_loss(entry_price, atr, 'LONG')
            target = self.strategy.calculate_target(entry_price, stop_loss, 'LONG')
            
            self.positions[symbol] = {
                'entry_date': date,
                'entry_price': entry_price,
                'shares': shares,
                'stop_loss': stop_loss,
                'target': target,
                'entry_reason': reason
            }
            
            logger.debug(f"Opened {symbol} position: {shares} shares @ ${entry_price:.2f}")
    
    def _check_exit(self, symbol: str, data: pd.DataFrame, index: int):
        """Check and execute exit signals.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with market data
            index: Current bar index
        """
        position = self.positions[symbol]
        bar = data.iloc[index]
        date = data.index[index]
        
        # Check strategy exit conditions
        should_exit, reason = self.strategy.check_exit_conditions(
            data,
            index,
            position['entry_price'],
            position['entry_date']
        )
        
        if should_exit:
            # Apply slippage
            exit_price = bar['close'] * (1 - self.slippage)
            self._close_position(symbol, exit_price, date, reason)
    
    def _close_position(self, symbol: str, exit_price: float, exit_date: datetime, reason: str):
        """Close an open position.
        
        Args:
            symbol: Stock symbol
            exit_price: Exit price
            exit_date: Exit date
            reason: Exit reason
        """
        position = self.positions[symbol]
        
        # Calculate proceeds
        proceeds = exit_price * position['shares'] * (1 - self.commission)
        self.capital += proceeds
        
        # Calculate P&L
        cost = position['entry_price'] * position['shares']
        pnl = proceeds - cost
        pnl_percent = (exit_price / position['entry_price'] - 1) * 100
        
        # Record trade
        trade = {
            'symbol': symbol,
            'side': 'LONG',
            'entry_date': position['entry_date'],
            'entry_price': position['entry_price'],
            'exit_date': exit_date,
            'exit_price': exit_price,
            'shares': position['shares'],
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'entry_reason': position['entry_reason'],
            'exit_reason': reason
        }
        
        self.trades.append(trade)
        
        # Remove position
        del self.positions[symbol]
        
        logger.debug(f"Closed {symbol} position: PnL=${pnl:.2f} ({pnl_percent:.2f}%) - {reason}")
    
    def _update_equity(self, symbol: str, current_price: float):
        """Update equity and track drawdown.
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        """
        # Calculate total equity
        position_value = 0
        if symbol in self.positions:
            position = self.positions[symbol]
            position_value = current_price * position['shares']
        
        self.equity = self.capital + position_value
        self.equity_curve.append(self.equity)
        
        # Track peak and drawdown
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        drawdown = (self.peak_equity - self.equity) / self.peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def _calculate_results(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Calculate backtest performance metrics.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with market data
            
        Returns:
            Dictionary with performance metrics
        """
        if not self.trades:
            return {
                'symbol': symbol,
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'trades': [],
                'equity_curve': self.equity_curve
            }
        
        # Calculate basic metrics
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] <= 0]
        
        total_return = (self.equity / self.initial_capital - 1) * 100
        win_rate = len(wins) / len(self.trades) * 100 if self.trades else 0
        
        # Calculate profit factor
        total_profit = sum([t['pnl'] for t in wins]) if wins else 0
        total_loss = abs(sum([t['pnl'] for t in losses])) if losses else 1
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Calculate Sharpe ratio
        if len(self.equity_curve) > 1:
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Buy and hold comparison
        buy_hold_return = (data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100
        
        return {
            'symbol': symbol,
            'initial_capital': self.initial_capital,
            'final_equity': self.equity,
            'total_return': total_return,
            'buy_hold_return': buy_hold_return,
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': self.max_drawdown * 100,
            'avg_win': np.mean([t['pnl_percent'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl_percent'] for t in losses]) if losses else 0,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'start_date': data.index[0],
            'end_date': data.index[-1]
        }
