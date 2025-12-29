"""Comprehensive technical indicators calculation module.

This module provides vectorized calculations for all technical indicators
used in the Bollinger Squeeze trading strategy, optimized for performance
with pandas DataFrames.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def calculate_rsi(data: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
    """Calculate RSI (Relative Strength Index) with customizable period.
    
    Args:
        data: DataFrame with OHLCV data
        period: RSI period (default: 14)
        column: Column name to calculate RSI on (default: 'close')
        
    Returns:
        DataFrame with 'rsi' column added
    """
    df = data.copy()
    
    # Calculate price changes
    delta = df[column].diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calculate average gains and losses using Wilder's smoothing
    avg_gains = gains.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_losses = losses.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Handle edge cases
    df['rsi'] = df['rsi'].fillna(50)
    
    return df


def calculate_macd(
    data: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    column: str = 'close'
) -> pd.DataFrame:
    """Calculate MACD (Moving Average Convergence Divergence) with histogram.
    
    Args:
        data: DataFrame with OHLCV data
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)
        column: Column name to calculate MACD on (default: 'close')
        
    Returns:
        DataFrame with 'macd', 'macd_signal', 'macd_histogram' columns added
    """
    df = data.copy()
    
    # Calculate EMAs
    ema_fast = df[column].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow_period, adjust=False).mean()
    
    # Calculate MACD line
    df['macd'] = ema_fast - ema_slow
    
    # Calculate signal line
    df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
    
    # Calculate histogram
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    return df


def calculate_bollinger_bands(
    data: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = 'close'
) -> pd.DataFrame:
    """Calculate Bollinger Bands (upper, middle, lower, width, %B).
    
    Args:
        data: DataFrame with OHLCV data
        period: Moving average period (default: 20)
        std_dev: Number of standard deviations (default: 2.0)
        column: Column name to calculate bands on (default: 'close')
        
    Returns:
        DataFrame with BB columns added
    """
    df = data.copy()
    
    # Calculate middle band (SMA)
    df['bb_middle'] = df[column].rolling(window=period).mean()
    
    # Calculate standard deviation
    rolling_std = df[column].rolling(window=period).std()
    
    # Calculate upper and lower bands
    df['bb_upper'] = df['bb_middle'] + (rolling_std * std_dev)
    df['bb_lower'] = df['bb_middle'] - (rolling_std * std_dev)
    
    # Calculate band width (normalized by middle band)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # Calculate %B (price position within bands, 0-1)
    df['bb_percent'] = (df[column] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # Calculate bandwidth percentile (for squeeze detection)
    df['bb_width_percentile'] = df['bb_width'].rolling(window=125).apply(
        lambda x: (x < x.iloc[-1]).sum() / (len(x) - 1) * 100 if len(x) > 1 else 50.0
    )
    
    return df


def calculate_moving_averages(
    data: pd.DataFrame,
    periods: Optional[list] = None,
    column: str = 'close'
) -> pd.DataFrame:
    """Calculate multiple Simple Moving Averages (MA9, MA20, MA50, MA200).
    
    Args:
        data: DataFrame with OHLCV data
        periods: List of periods for MAs (default: [9, 20, 50, 200])
        column: Column name to calculate MAs on (default: 'close')
        
    Returns:
        DataFrame with MA columns added (ma_9, ma_20, ma_50, ma_200)
    """
    if periods is None:
        periods = [9, 20, 50, 200]
    
    df = data.copy()
    
    for period in periods:
        col_name = f'ma_{period}'
        df[col_name] = df[column].rolling(window=period).mean()
    
    return df


def calculate_volume_indicators(
    data: pd.DataFrame,
    period: int = 20
) -> pd.DataFrame:
    """Calculate volume indicators (average volume, volume oscillator, volume ratio).
    
    Args:
        data: DataFrame with OHLCV data
        period: Period for volume calculations (default: 20)
        
    Returns:
        DataFrame with volume indicator columns added
    """
    df = data.copy()
    
    # Average volume
    df['avg_volume'] = df['volume'].rolling(window=period).mean()
    
    # Volume ratio (current volume / average volume)
    df['volume_ratio'] = df['volume'] / df['avg_volume']
    
    # Volume oscillator (short-term vs long-term volume)
    short_vol = df['volume'].rolling(window=5).mean()
    long_vol = df['volume'].rolling(window=20).mean()
    df['volume_oscillator'] = (short_vol - long_vol) / long_vol * 100
    
    # Volume trend (is volume declining?)
    df['volume_declining'] = df['volume'].rolling(window=5).mean() < df['volume'].rolling(window=10).mean()
    
    return df


def calculate_all_indicators(
    data: pd.DataFrame,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_period: int = 20,
    bb_std: float = 2.0,
    ma_periods: Optional[list] = None,
    volume_period: int = 20
) -> pd.DataFrame:
    """Calculate all technical indicators in one pass (optimized).
    
    Args:
        data: DataFrame with OHLCV data
        rsi_period: RSI period
        macd_fast: MACD fast period
        macd_slow: MACD slow period
        macd_signal: MACD signal period
        bb_period: Bollinger Bands period
        bb_std: Bollinger Bands standard deviation
        ma_periods: List of moving average periods
        volume_period: Volume indicators period
        
    Returns:
        DataFrame with all indicator columns added
    """
    df = data.copy()
    
    # Calculate all indicators
    df = calculate_rsi(df, period=rsi_period)
    df = calculate_macd(df, fast_period=macd_fast, slow_period=macd_slow, signal_period=macd_signal)
    df = calculate_bollinger_bands(df, period=bb_period, std_dev=bb_std)
    df = calculate_moving_averages(df, periods=ma_periods)
    df = calculate_volume_indicators(df, period=volume_period)
    
    return df


def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate Average True Range (ATR) for volatility measurement.
    
    Args:
        data: DataFrame with OHLCV data
        period: ATR period (default: 14)
        
    Returns:
        DataFrame with 'atr' column added
    """
    df = data.copy()
    
    # Calculate True Range
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate ATR using Wilder's smoothing
    df['atr'] = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    return df


def calculate_support_resistance(
    data: pd.DataFrame,
    lookback: int = 20
) -> Tuple[float, float]:
    """Calculate support and resistance levels based on recent price action.
    
    Args:
        data: DataFrame with OHLCV data
        lookback: Number of periods to look back (default: 20)
        
    Returns:
        Tuple of (support_level, resistance_level)
    """
    recent_data = data.tail(lookback)
    
    # Support: recent lows and lower Bollinger Band
    support_candidates = []
    if 'bb_lower' in recent_data.columns:
        support_candidates.append(recent_data['bb_lower'].iloc[-1])
    support_candidates.append(recent_data['low'].min())
    support_candidates.append(recent_data['close'].quantile(0.1))
    
    # Resistance: recent highs and upper Bollinger Band
    resistance_candidates = []
    if 'bb_upper' in recent_data.columns:
        resistance_candidates.append(recent_data['bb_upper'].iloc[-1])
    resistance_candidates.append(recent_data['high'].max())
    resistance_candidates.append(recent_data['close'].quantile(0.9))
    
    support = np.mean(support_candidates)
    resistance = np.mean(resistance_candidates)
    
    return support, resistance
