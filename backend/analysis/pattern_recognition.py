"""Pattern recognition module for technical analysis.

Detects various chart patterns and technical signals:
- RSI divergences (bullish and bearish)
- MACD crossovers (golden cross, death cross)
- Candlestick patterns (hammer, doji, engulfing)
- Higher highs / higher lows sequences
- Double tops/bottoms
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Pattern:
    """Detected pattern with details."""
    pattern_type: str
    description: str
    signal: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float  # 0-100
    detected_at_index: int
    price_level: float


class PatternRecognizer:
    """Recognizes technical patterns in price data."""
    
    def __init__(self, lookback: int = 20):
        """Initialize pattern recognizer.
        
        Args:
            lookback: Number of periods to analyze for patterns
        """
        self.lookback = lookback
    
    def detect_all_patterns(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect all patterns in the data.
        
        Args:
            data: DataFrame with OHLCV data and indicators
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Detect RSI divergences
        patterns.extend(self.detect_rsi_divergence(data))
        
        # Detect MACD crossovers
        patterns.extend(self.detect_macd_crossover(data))
        
        # Detect candlestick patterns
        patterns.extend(self.detect_candlestick_patterns(data))
        
        # Detect trend patterns
        patterns.extend(self.detect_trend_patterns(data))
        
        # Detect double tops/bottoms
        patterns.extend(self.detect_double_patterns(data))
        
        return patterns
    
    def detect_rsi_divergence(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect RSI divergences (bullish and bearish).
        
        Bullish divergence: Price makes lower lows but RSI makes higher lows
        Bearish divergence: Price makes higher highs but RSI makes lower highs
        """
        patterns = []
        
        if 'rsi' not in data.columns or len(data) < self.lookback:
            return patterns
        
        df = data.tail(self.lookback).copy()
        
        # Find local extrema in price
        price_peaks = self._find_peaks(df['close'])
        price_troughs = self._find_troughs(df['close'])
        
        # Find local extrema in RSI
        rsi_peaks = self._find_peaks(df['rsi'])
        rsi_troughs = self._find_troughs(df['rsi'])
        
        # Check for bullish divergence (price lower low, RSI higher low)
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            last_price_trough = price_troughs[-1]
            prev_price_trough = price_troughs[-2]
            last_rsi_trough = rsi_troughs[-1]
            prev_rsi_trough = rsi_troughs[-2]
            
            if (df['close'].iloc[last_price_trough] < df['close'].iloc[prev_price_trough] and
                df['rsi'].iloc[last_rsi_trough] > df['rsi'].iloc[prev_rsi_trough]):
                
                patterns.append(Pattern(
                    pattern_type='RSI_BULLISH_DIVERGENCE',
                    description='Bullish divergence: Price making lower lows while RSI making higher lows',
                    signal='BULLISH',
                    confidence=75.0,
                    detected_at_index=len(data) - 1,
                    price_level=float(df['close'].iloc[-1])
                ))
        
        # Check for bearish divergence (price higher high, RSI lower high)
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            last_price_peak = price_peaks[-1]
            prev_price_peak = price_peaks[-2]
            last_rsi_peak = rsi_peaks[-1]
            prev_rsi_peak = rsi_peaks[-2]
            
            if (df['close'].iloc[last_price_peak] > df['close'].iloc[prev_price_peak] and
                df['rsi'].iloc[last_rsi_peak] < df['rsi'].iloc[prev_rsi_peak]):
                
                patterns.append(Pattern(
                    pattern_type='RSI_BEARISH_DIVERGENCE',
                    description='Bearish divergence: Price making higher highs while RSI making lower highs',
                    signal='BEARISH',
                    confidence=75.0,
                    detected_at_index=len(data) - 1,
                    price_level=float(df['close'].iloc[-1])
                ))
        
        return patterns
    
    def detect_macd_crossover(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect MACD crossovers (golden cross, death cross)."""
        patterns = []
        
        if 'macd' not in data.columns or 'macd_signal' not in data.columns:
            return patterns
        
        if len(data) < 3:
            return patterns
        
        recent = data.tail(3)
        
        # Check for bullish crossover (MACD crosses above signal)
        if (recent['macd'].iloc[-2] < recent['macd_signal'].iloc[-2] and
            recent['macd'].iloc[-1] > recent['macd_signal'].iloc[-1]):
            
            patterns.append(Pattern(
                pattern_type='MACD_GOLDEN_CROSS',
                description='MACD crossed above signal line',
                signal='BULLISH',
                confidence=70.0,
                detected_at_index=len(data) - 1,
                price_level=float(recent['close'].iloc[-1])
            ))
        
        # Check for bearish crossover (MACD crosses below signal)
        if (recent['macd'].iloc[-2] > recent['macd_signal'].iloc[-2] and
            recent['macd'].iloc[-1] < recent['macd_signal'].iloc[-1]):
            
            patterns.append(Pattern(
                pattern_type='MACD_DEATH_CROSS',
                description='MACD crossed below signal line',
                signal='BEARISH',
                confidence=70.0,
                detected_at_index=len(data) - 1,
                price_level=float(recent['close'].iloc[-1])
            ))
        
        return patterns
    
    def detect_candlestick_patterns(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect candlestick patterns (hammer, doji, engulfing)."""
        patterns = []
        
        if len(data) < 2:
            return patterns
        
        current = data.iloc[-1]
        prev = data.iloc[-2]
        
        body = abs(current['close'] - current['open'])
        range_size = current['high'] - current['low']
        
        if range_size == 0:
            return patterns
        
        body_pct = body / range_size
        
        # Hammer (bullish reversal)
        # Small body at top, long lower shadow
        lower_shadow = min(current['open'], current['close']) - current['low']
        upper_shadow = current['high'] - max(current['open'], current['close'])
        
        if (body_pct < 0.3 and 
            lower_shadow > body * 2 and 
            upper_shadow < body * 0.3 and
            current['close'] < prev['close'] * 0.98):  # In downtrend
            
            patterns.append(Pattern(
                pattern_type='HAMMER',
                description='Hammer candlestick pattern - potential bullish reversal',
                signal='BULLISH',
                confidence=65.0,
                detected_at_index=len(data) - 1,
                price_level=float(current['close'])
            ))
        
        # Doji (indecision)
        # Very small body
        if body_pct < 0.1:
            patterns.append(Pattern(
                pattern_type='DOJI',
                description='Doji candlestick - market indecision',
                signal='NEUTRAL',
                confidence=60.0,
                detected_at_index=len(data) - 1,
                price_level=float(current['close'])
            ))
        
        # Bullish engulfing
        # Current candle's body completely engulfs previous candle's body
        if (prev['close'] < prev['open'] and  # Previous bearish
            current['close'] > current['open'] and  # Current bullish
            current['open'] < prev['close'] and
            current['close'] > prev['open']):
            
            patterns.append(Pattern(
                pattern_type='BULLISH_ENGULFING',
                description='Bullish engulfing pattern - strong reversal signal',
                signal='BULLISH',
                confidence=80.0,
                detected_at_index=len(data) - 1,
                price_level=float(current['close'])
            ))
        
        # Bearish engulfing
        if (prev['close'] > prev['open'] and  # Previous bullish
            current['close'] < current['open'] and  # Current bearish
            current['open'] > prev['close'] and
            current['close'] < prev['open']):
            
            patterns.append(Pattern(
                pattern_type='BEARISH_ENGULFING',
                description='Bearish engulfing pattern - strong reversal signal',
                signal='BEARISH',
                confidence=80.0,
                detected_at_index=len(data) - 1,
                price_level=float(current['close'])
            ))
        
        return patterns
    
    def detect_trend_patterns(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect higher highs/higher lows and lower highs/lower lows."""
        patterns = []
        
        if len(data) < self.lookback:
            return patterns
        
        df = data.tail(self.lookback)
        
        # Find local peaks and troughs
        peaks = self._find_peaks(df['high'])
        troughs = self._find_troughs(df['low'])
        
        # Check for higher highs and higher lows (uptrend)
        if len(peaks) >= 2 and len(troughs) >= 2:
            if (df['high'].iloc[peaks[-1]] > df['high'].iloc[peaks[-2]] and
                df['low'].iloc[troughs[-1]] > df['low'].iloc[troughs[-2]]):
                
                patterns.append(Pattern(
                    pattern_type='HIGHER_HIGHS_HIGHER_LOWS',
                    description='Uptrend: Series of higher highs and higher lows',
                    signal='BULLISH',
                    confidence=70.0,
                    detected_at_index=len(data) - 1,
                    price_level=float(df['close'].iloc[-1])
                ))
        
        # Check for lower highs and lower lows (downtrend)
        if len(peaks) >= 2 and len(troughs) >= 2:
            if (df['high'].iloc[peaks[-1]] < df['high'].iloc[peaks[-2]] and
                df['low'].iloc[troughs[-1]] < df['low'].iloc[troughs[-2]]):
                
                patterns.append(Pattern(
                    pattern_type='LOWER_HIGHS_LOWER_LOWS',
                    description='Downtrend: Series of lower highs and lower lows',
                    signal='BEARISH',
                    confidence=70.0,
                    detected_at_index=len(data) - 1,
                    price_level=float(df['close'].iloc[-1])
                ))
        
        return patterns
    
    def detect_double_patterns(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect double tops and double bottoms."""
        patterns = []
        
        if len(data) < self.lookback:
            return patterns
        
        df = data.tail(self.lookback)
        
        # Find peaks and troughs
        peaks = self._find_peaks(df['high'])
        troughs = self._find_troughs(df['low'])
        
        # Double top (bearish reversal)
        if len(peaks) >= 2:
            last_peak = peaks[-1]
            prev_peak = peaks[-2]
            
            # Peaks should be at similar levels (within 2%)
            peak_diff = abs(df['high'].iloc[last_peak] - df['high'].iloc[prev_peak])
            avg_peak = (df['high'].iloc[last_peak] + df['high'].iloc[prev_peak]) / 2
            
            if peak_diff / avg_peak < 0.02 and last_peak - prev_peak >= 5:
                patterns.append(Pattern(
                    pattern_type='DOUBLE_TOP',
                    description='Double top pattern - bearish reversal',
                    signal='BEARISH',
                    confidence=75.0,
                    detected_at_index=len(data) - 1,
                    price_level=avg_peak
                ))
        
        # Double bottom (bullish reversal)
        if len(troughs) >= 2:
            last_trough = troughs[-1]
            prev_trough = troughs[-2]
            
            # Troughs should be at similar levels (within 2%)
            trough_diff = abs(df['low'].iloc[last_trough] - df['low'].iloc[prev_trough])
            avg_trough = (df['low'].iloc[last_trough] + df['low'].iloc[prev_trough]) / 2
            
            if trough_diff / avg_trough < 0.02 and last_trough - prev_trough >= 5:
                patterns.append(Pattern(
                    pattern_type='DOUBLE_BOTTOM',
                    description='Double bottom pattern - bullish reversal',
                    signal='BULLISH',
                    confidence=75.0,
                    detected_at_index=len(data) - 1,
                    price_level=avg_trough
                ))
        
        return patterns
    
    def _find_peaks(self, series: pd.Series, window: int = 3) -> List[int]:
        """Find local peaks in a series.
        
        Args:
            series: Price series
            window: Window size for peak detection
            
        Returns:
            List of indices where peaks occur
        """
        peaks = []
        
        for i in range(window, len(series) - window):
            is_peak = True
            center_val = series.iloc[i]
            
            # Check if center is higher than all neighbors
            for j in range(i - window, i + window + 1):
                if j != i and series.iloc[j] >= center_val:
                    is_peak = False
                    break
            
            if is_peak:
                peaks.append(i)
        
        return peaks
    
    def _find_troughs(self, series: pd.Series, window: int = 3) -> List[int]:
        """Find local troughs in a series.
        
        Args:
            series: Price series
            window: Window size for trough detection
            
        Returns:
            List of indices where troughs occur
        """
        troughs = []
        
        for i in range(window, len(series) - window):
            is_trough = True
            center_val = series.iloc[i]
            
            # Check if center is lower than all neighbors
            for j in range(i - window, i + window + 1):
                if j != i and series.iloc[j] <= center_val:
                    is_trough = False
                    break
            
            if is_trough:
                troughs.append(i)
        
        return troughs
