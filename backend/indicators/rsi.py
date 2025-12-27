"""RSI (Relative Strength Index) indicator."""
import pandas as pd
import numpy as np


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate RSI indicator.
    
    Args:
        data: DataFrame with 'close' column
        period: RSI period
        
    Returns:
        DataFrame with 'rsi' column added
    """
    df = data.copy()
    
    # Calculate price changes
    delta = df['close'].diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calculate average gains and losses
    avg_gains = gains.rolling(window=period).mean()
    avg_losses = losses.rolling(window=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Handle edge cases
    df['rsi'] = df['rsi'].fillna(50)
    
    return df


def rsi_signal(rsi: float) -> str:
    """Get RSI signal interpretation.
    
    Args:
        rsi: RSI value
        
    Returns:
        Signal string: 'oversold', 'neutral', 'overbought'
    """
    if rsi < 30:
        return 'oversold'
    elif rsi > 70:
        return 'overbought'
    else:
        return 'neutral'
