"""Main Bollinger Squeeze trading strategy."""
from typing import Dict, Tuple
import pandas as pd
from datetime import datetime
from .base import BaseStrategy
from backend.indicators import (
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_macd,
    calculate_volume_indicators,
    is_volume_spike,
    SqueezeDetector
)
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class BollingerSqueezeStrategy(BaseStrategy):
    """Bollinger Squeeze breakout strategy.
    
    Entry conditions:
    - In squeeze for min_days_in_squeeze
    - Breakout confirmed (price closes outside bands)
    - Volume confirmation (if required)
    - RSI confirmation (if required)
    
    Exit conditions:
    - Target reached (reward:risk ratio)
    - Stop loss hit
    - Reverse squeeze detected
    """
    
    def __init__(self, params: Dict = None):
        """Initialize Bollinger Squeeze strategy.
        
        Args:
            params: Strategy parameters
        """
        default_params = {
            'bollinger_period': 20,
            'bollinger_std': 2.0,
            'squeeze_threshold': 0.5,
            'min_days_in_squeeze': 2,
            'max_days_in_squeeze': 10,
            'require_volume_confirmation': True,
            'volume_spike_multiplier': 1.5,
            'require_rsi_confirmation': True,
            'rsi_min': 40,
            'rsi_max': 70,
            'target_multiplier': 3.0,
            'stop_loss_atr_multiplier': 2.0,
            'position_size': 0.1
        }
        
        if params:
            default_params.update(params)
        
        super().__init__('BollingerSqueeze', default_params)
        
        self.detector = SqueezeDetector(
            bollinger_period=self.params['bollinger_period'],
            bollinger_std=self.params['bollinger_std'],
            squeeze_threshold=self.params['squeeze_threshold'],
            min_days_in_squeeze=self.params['min_days_in_squeeze'],
            max_days_in_squeeze=self.params['max_days_in_squeeze']
        )
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on squeeze breakout.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with signals
        """
        df = data.copy()
        
        # Calculate indicators
        df = calculate_bollinger_bands(df, self.params['bollinger_period'], self.params['bollinger_std'])
        df = calculate_rsi(df)
        df = calculate_macd(df)
        df = calculate_volume_indicators(df)
        df['atr'] = self.calculate_atr(df)
        
        # Analyze squeeze
        squeeze_result = self.detector.analyze(df)
        
        # Initialize signal column
        df['signal'] = 0
        
        # Generate signals for each bar
        for i in range(len(df)):
            if i < self.params['bollinger_period'] * 2:
                continue
            
            should_enter, reason = self.check_entry_conditions(df, i)
            if should_enter:
                # Determine direction based on breakout
                if df['close'].iloc[i] > df['bb_upper'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 1  # Buy signal
                    df.loc[df.index[i], 'entry_reason'] = reason
                elif df['close'].iloc[i] < df['bb_lower'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = -1  # Short signal
                    df.loc[df.index[i], 'entry_reason'] = reason
        
        return df
    
    def check_entry_conditions(self, data: pd.DataFrame, index: int) -> Tuple[bool, str]:
        """Check if entry conditions are met.
        
        Args:
            data: DataFrame with market data and indicators
            index: Current bar index
            
        Returns:
            Tuple of (should_enter, reason)
        """
        if index < self.params['bollinger_period'] * 2:
            return False, "Insufficient data"
        
        current = data.iloc[index]
        previous = data.iloc[index - 1]
        
        # Check if was in squeeze on previous bar
        squeeze_data = data.iloc[:index + 1]
        squeeze_result = self.detector.analyze(squeeze_data)
        
        if not squeeze_result['in_squeeze']:
            return False, "Not in squeeze"
        
        # Check for breakout (price closes outside bands)
        breakout_up = current['close'] > current['bb_upper'] and previous['close'] <= previous['bb_upper']
        breakout_down = current['close'] < current['bb_lower'] and previous['close'] >= previous['bb_lower']
        
        if not (breakout_up or breakout_down):
            return False, "No breakout"
        
        # Volume confirmation
        if self.params['require_volume_confirmation']:
            if not is_volume_spike(
                data.iloc[:index + 1],
                self.params['volume_spike_multiplier']
            ).iloc[-1]:
                return False, "Insufficient volume"
        
        # RSI confirmation
        if self.params['require_rsi_confirmation']:
            rsi = current['rsi']
            if not (self.params['rsi_min'] <= rsi <= self.params['rsi_max']):
                return False, f"RSI out of range: {rsi:.1f}"
        
        direction = "BULLISH" if breakout_up else "BEARISH"
        reason = f"Squeeze breakout {direction} - Strength: {squeeze_result['squeeze_strength']:.0f}, Days: {squeeze_result['days_in_squeeze']}"
        
        return True, reason
    
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
        current = data.iloc[index]
        current_price = current['close']
        
        # Determine position side from signal direction
        # Assuming we have stored the signal at entry
        signal = data['signal'].iloc[data.index.get_loc(entry_date)]
        is_long = signal > 0
        
        # Calculate stop loss and target
        atr = current['atr']
        stop_loss = self.calculate_stop_loss(entry_price, atr, 'LONG' if is_long else 'SHORT')
        target = self.calculate_target(entry_price, stop_loss, 'LONG' if is_long else 'SHORT')
        
        # Check stop loss
        if is_long and current['low'] <= stop_loss:
            return True, "Stop loss hit"
        if not is_long and current['high'] >= stop_loss:
            return True, "Stop loss hit"
        
        # Check target
        if is_long and current['high'] >= target:
            return True, "Target reached"
        if not is_long and current['low'] <= target:
            return True, "Target reached"
        
        # Check for reverse squeeze (optional exit)
        if index - data.index.get_loc(entry_date) >= 5:
            # Check if entering opposite squeeze
            squeeze_result = self.detector.analyze(data.iloc[:index + 1])
            if squeeze_result['in_squeeze']:
                if (is_long and squeeze_result['direction'] == 'BEARISH' and squeeze_result['confidence'] > 60) or \
                   (not is_long and squeeze_result['direction'] == 'BULLISH' and squeeze_result['confidence'] > 60):
                    return True, "Reverse squeeze detected"
        
        return False, "Hold"
