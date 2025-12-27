"""Performance metrics calculation."""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime


def calculate_sortino_ratio(returns: pd.Series, target_return: float = 0.0) -> float:
    """Calculate Sortino ratio (variation of Sharpe that only considers downside volatility).
    
    Args:
        returns: Series of returns
        target_return: Target or risk-free rate
        
    Returns:
        Sortino ratio
    """
    excess_returns = returns - target_return
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0
    
    return (excess_returns.mean() / downside_returns.std()) * np.sqrt(252)


def calculate_calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
    """Calculate Calmar ratio (annual return / max drawdown).
    
    Args:
        returns: Series of returns
        max_drawdown: Maximum drawdown as decimal
        
    Returns:
        Calmar ratio
    """
    if max_drawdown == 0:
        return 0.0
    
    annual_return = returns.mean() * 252
    return annual_return / max_drawdown


def calculate_information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculate Information ratio (excess return / tracking error).
    
    Args:
        returns: Series of strategy returns
        benchmark_returns: Series of benchmark returns
        
    Returns:
        Information ratio
    """
    excess_returns = returns - benchmark_returns
    tracking_error = excess_returns.std()
    
    if tracking_error == 0:
        return 0.0
    
    return (excess_returns.mean() / tracking_error) * np.sqrt(252)


def calculate_trade_metrics(trades: List[Dict]) -> Dict:
    """Calculate detailed trade statistics.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Dictionary with trade metrics
    """
    if not trades:
        return {}
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    
    # Calculate hold times
    hold_times = []
    for trade in trades:
        if isinstance(trade['entry_date'], datetime) and isinstance(trade['exit_date'], datetime):
            hold_time = (trade['exit_date'] - trade['entry_date']).days
            hold_times.append(hold_time)
    
    # Consecutive wins/losses
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_streak = 0
    last_was_win = None
    
    for trade in trades:
        is_win = trade['pnl'] > 0
        if last_was_win is None or last_was_win == is_win:
            current_streak += 1
        else:
            if last_was_win:
                max_consecutive_wins = max(max_consecutive_wins, current_streak)
            else:
                max_consecutive_losses = max(max_consecutive_losses, current_streak)
            current_streak = 1
        last_was_win = is_win
    
    # Update final streak
    if last_was_win:
        max_consecutive_wins = max(max_consecutive_wins, current_streak)
    else:
        max_consecutive_losses = max(max_consecutive_losses, current_streak)
    
    return {
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_win_pct': np.mean([t['pnl_percent'] for t in wins]) if wins else 0,
        'avg_loss_pct': np.mean([t['pnl_percent'] for t in losses]) if losses else 0,
        'avg_win_amount': np.mean([t['pnl'] for t in wins]) if wins else 0,
        'avg_loss_amount': np.mean([t['pnl'] for t in losses]) if losses else 0,
        'largest_win': max([t['pnl'] for t in wins]) if wins else 0,
        'largest_loss': min([t['pnl'] for t in losses]) if losses else 0,
        'avg_hold_time_days': np.mean(hold_times) if hold_times else 0,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,
        'total_pnl': sum([t['pnl'] for t in trades]),
        'profit_factor': sum([t['pnl'] for t in wins]) / abs(sum([t['pnl'] for t in losses])) if losses and sum([t['pnl'] for t in losses]) != 0 else 0
    }


def calculate_monthly_returns(equity_curve: List[float], dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Calculate monthly returns breakdown.
    
    Args:
        equity_curve: List of equity values
        dates: DatetimeIndex corresponding to equity values
        
    Returns:
        DataFrame with monthly returns
    """
    df = pd.DataFrame({
        'equity': equity_curve
    }, index=dates)
    
    df['returns'] = df['equity'].pct_change()
    
    monthly = df.groupby([df.index.year, df.index.month])['returns'].sum() * 100
    monthly.index.names = ['Year', 'Month']
    
    return monthly.reset_index()


def calculate_risk_metrics(equity_curve: List[float]) -> Dict:
    """Calculate risk-adjusted metrics.
    
    Args:
        equity_curve: List of equity values
        
    Returns:
        Dictionary with risk metrics
    """
    if len(equity_curve) < 2:
        return {}
    
    returns = pd.Series(equity_curve).pct_change().dropna()
    
    # Value at Risk (95% confidence)
    var_95 = returns.quantile(0.05)
    
    # Conditional Value at Risk (expected shortfall)
    cvar_95 = returns[returns <= var_95].mean()
    
    # Downside deviation
    downside_returns = returns[returns < 0]
    downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0
    
    # Ulcer Index (measure of drawdown depth and duration)
    cumulative_returns = (1 + returns).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    ulcer_index = np.sqrt((drawdown ** 2).mean())
    
    return {
        'value_at_risk_95': var_95 * 100,
        'cvar_95': cvar_95 * 100,
        'downside_deviation': downside_deviation,
        'ulcer_index': ulcer_index,
        'volatility': returns.std() * np.sqrt(252) * 100
    }
