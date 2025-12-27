"""Volume analysis indicators."""
import pandas as pd
import numpy as np


def calculate_volume_indicators(data: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Calculate volume-based indicators.
    
    Args:
        data: DataFrame with 'volume' column
        period: Period for moving averages
        
    Returns:
        DataFrame with volume indicators
    """
    df = data.copy()
    
    # Average volume
    df['volume_sma'] = df['volume'].rolling(window=period).mean()
    
    # Volume ratio (current vs average)
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    
    # Volume trend (increasing or decreasing)
    df['volume_trend'] = df['volume'].rolling(window=5).mean() / df['volume_sma']
    
    return df


def is_volume_spike(data: pd.DataFrame, multiplier: float = 1.5) -> pd.Series:
    """Detect volume spikes.
    
    Args:
        data: DataFrame with 'volume' and 'volume_sma' columns
        multiplier: Multiplier for spike detection
        
    Returns:
        Boolean Series indicating volume spikes
    """
    return data['volume'] > (data['volume_sma'] * multiplier)


def is_volume_declining(data: pd.DataFrame) -> pd.Series:
    """Detect declining volume (often precedes squeeze breakout).
    
    Args:
        data: DataFrame with 'volume_trend' column
        
    Returns:
        Boolean Series indicating declining volume
    """
    return data['volume_trend'] < 1.0


def calculate_obv(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate On-Balance Volume (OBV).
    
    Args:
        data: DataFrame with 'close' and 'volume' columns
        
    Returns:
        DataFrame with 'obv' column
    """
    df = data.copy()
    
    # Calculate price direction
    price_direction = np.sign(df['close'].diff())
    
    # Calculate OBV
    df['obv'] = (price_direction * df['volume']).cumsum()
    
    return df
