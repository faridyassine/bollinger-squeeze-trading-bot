"""Bollinger Bands indicator."""
import pandas as pd
import numpy as np


def calculate_bollinger_bands(
    data: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.DataFrame:
    """Calculate Bollinger Bands.
    
    Args:
        data: DataFrame with 'close' column
        period: Moving average period
        std_dev: Number of standard deviations
        
    Returns:
        DataFrame with bb_upper, bb_middle, bb_lower, bb_width columns
    """
    df = data.copy()
    
    # Calculate middle band (SMA)
    df['bb_middle'] = df['close'].rolling(window=period).mean()
    
    # Calculate standard deviation
    rolling_std = df['close'].rolling(window=period).std()
    
    # Calculate upper and lower bands
    df['bb_upper'] = df['bb_middle'] + (rolling_std * std_dev)
    df['bb_lower'] = df['bb_middle'] - (rolling_std * std_dev)
    
    # Calculate band width (normalized)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # Calculate %B (price position within bands)
    df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    return df


def calculate_bandwidth_percentile(data: pd.DataFrame, lookback: int = 125) -> pd.Series:
    """Calculate Bollinger Band width percentile.
    
    Shows where current bandwidth ranks relative to recent history.
    Lower percentile = tighter squeeze.
    
    Args:
        data: DataFrame with 'bb_width' column
        lookback: Number of periods for percentile calculation (default: 6 months)
        
    Returns:
        Series with bandwidth percentile (0-100)
    """
    def percentile_rank(series):
        if len(series) < 2:
            return 50.0
        rank = (series < series.iloc[-1]).sum()
        return (rank / (len(series) - 1)) * 100
    
    return data['bb_width'].rolling(window=lookback).apply(percentile_rank, raw=False)


def is_squeeze(data: pd.DataFrame, threshold: float = 0.5) -> pd.Series:
    """Detect if bands are in squeeze (compressed).
    
    Args:
        data: DataFrame with 'bb_width' column
        threshold: Threshold for squeeze detection (lower = tighter squeeze)
        
    Returns:
        Boolean Series indicating squeeze periods
    """
    # Calculate historical average and percentile
    avg_width = data['bb_width'].rolling(window=100).mean()
    percentile = calculate_bandwidth_percentile(data, lookback=125)
    
    # Squeeze if width is below threshold relative to average
    # AND in bottom 20th percentile
    is_compressed = (data['bb_width'] < avg_width * threshold) & (percentile < 20)
    
    return is_compressed
