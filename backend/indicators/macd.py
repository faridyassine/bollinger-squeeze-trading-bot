"""MACD (Moving Average Convergence Divergence) indicator."""
import pandas as pd
import numpy as np


def calculate_macd(
    data: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """Calculate MACD indicator.
    
    Args:
        data: DataFrame with 'close' column
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line EMA period
        
    Returns:
        DataFrame with macd, macd_signal, macd_histogram columns
    """
    df = data.copy()
    
    # Calculate EMAs
    ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
    
    # Calculate MACD line
    df['macd'] = ema_fast - ema_slow
    
    # Calculate signal line
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    
    # Calculate histogram
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    return df


def macd_signal_type(macd: float, signal: float, histogram: float) -> str:
    """Get MACD signal interpretation.
    
    Args:
        macd: MACD line value
        signal: Signal line value
        histogram: Histogram value
        
    Returns:
        Signal string: 'bullish', 'bearish', 'neutral'
    """
    if histogram > 0 and macd > signal:
        return 'bullish'
    elif histogram < 0 and macd < signal:
        return 'bearish'
    else:
        return 'neutral'
