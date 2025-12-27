"""Core squeeze detection algorithm."""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from .bollinger import (
    calculate_bollinger_bands,
    calculate_bandwidth_percentile,
    is_squeeze as is_bb_squeeze
)
from .rsi import calculate_rsi, rsi_signal
from .macd import calculate_macd, macd_signal_type
from .volume import calculate_volume_indicators, is_volume_declining
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class SqueezeDetector:
    """Detects Bollinger Squeeze patterns and predicts breakout direction."""
    
    def __init__(
        self,
        bollinger_period: int = 20,
        bollinger_std: float = 2.0,
        squeeze_threshold: float = 0.5,
        min_days_in_squeeze: int = 2,
        max_days_in_squeeze: int = 10
    ):
        """Initialize squeeze detector.
        
        Args:
            bollinger_period: Bollinger Bands period
            bollinger_std: Bollinger Bands standard deviation
            squeeze_threshold: Threshold for squeeze detection
            min_days_in_squeeze: Minimum days to confirm squeeze
            max_days_in_squeeze: Maximum days before squeeze expires
        """
        self.bollinger_period = bollinger_period
        self.bollinger_std = bollinger_std
        self.squeeze_threshold = squeeze_threshold
        self.min_days_in_squeeze = min_days_in_squeeze
        self.max_days_in_squeeze = max_days_in_squeeze
    
    def analyze(self, data: pd.DataFrame) -> Dict:
        """Analyze data for squeeze pattern.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with squeeze analysis results
        """
        if len(data) < self.bollinger_period * 2:
            logger.warning("Insufficient data for squeeze analysis")
            return self._empty_result()
        
        # Calculate all indicators
        df = data.copy()
        df = calculate_bollinger_bands(df, self.bollinger_period, self.bollinger_std)
        df = calculate_rsi(df)
        df = calculate_macd(df)
        df = calculate_volume_indicators(df)
        
        # Calculate squeeze metrics
        df['bb_percentile'] = calculate_bandwidth_percentile(df)
        df['in_squeeze'] = is_bb_squeeze(df, self.squeeze_threshold)
        
        # Get current state
        current = df.iloc[-1]
        
        # Check if currently in squeeze
        if not current['in_squeeze']:
            return self._empty_result()
        
        # Count days in squeeze
        days_in_squeeze = self._count_squeeze_days(df)
        
        # Check if squeeze is valid
        if days_in_squeeze < self.min_days_in_squeeze:
            return self._empty_result()
        
        if days_in_squeeze > self.max_days_in_squeeze:
            logger.debug(f"Squeeze expired (>{self.max_days_in_squeeze} days)")
            return self._empty_result()
        
        # Calculate squeeze strength (0-100)
        squeeze_strength = self._calculate_squeeze_strength(current, df)
        
        # Predict breakout direction
        direction, confidence = self._predict_direction(current, df)
        
        # Check for volume confirmation
        volume_declining = is_volume_declining(df).iloc[-1]
        
        result = {
            'in_squeeze': True,
            'squeeze_strength': round(squeeze_strength, 2),
            'days_in_squeeze': days_in_squeeze,
            'direction': direction,
            'confidence': round(confidence, 2),
            'price': float(current['close']),
            'bb_width': float(current['bb_width']),
            'bb_percentile': float(current['bb_percentile']),
            'rsi': float(current['rsi']),
            'rsi_signal': rsi_signal(current['rsi']),
            'macd': float(current['macd']),
            'macd_signal': macd_signal_type(
                current['macd'],
                current['macd_signal'],
                current['macd_histogram']
            ),
            'volume_ratio': float(current['volume_ratio']),
            'volume_declining': bool(volume_declining),
            'indicators': self._get_indicator_summary(current)
        }
        
        logger.info(f"Squeeze detected: strength={squeeze_strength:.1f}, "
                   f"days={days_in_squeeze}, direction={direction}")
        
        return result
    
    def _count_squeeze_days(self, df: pd.DataFrame) -> int:
        """Count consecutive days in squeeze."""
        in_squeeze = df['in_squeeze'].values
        count = 0
        
        for i in range(len(in_squeeze) - 1, -1, -1):
            if in_squeeze[i]:
                count += 1
            else:
                break
        
        return count
    
    def _calculate_squeeze_strength(self, current: pd.Series, df: pd.DataFrame) -> float:
        """Calculate squeeze strength score (0-100).
        
        Higher score = tighter squeeze = higher probability of significant breakout.
        
        Factors:
        - Band width percentile (lower = stronger)
        - Days in squeeze (more days = stronger)
        - Volume declining (yes = stronger)
        - RSI near neutral (yes = stronger)
        """
        score = 0.0
        
        # Band width percentile (40 points max)
        # Lower percentile = higher score
        percentile_score = (20 - current['bb_percentile']) / 20 * 40
        score += max(0, percentile_score)
        
        # Days in squeeze (30 points max)
        days_score = min(self._count_squeeze_days(df), 10) / 10 * 30
        score += days_score
        
        # Volume declining (15 points)
        if is_volume_declining(df).iloc[-1]:
            score += 15
        
        # RSI near neutral 40-60 (15 points)
        rsi = current['rsi']
        if 40 <= rsi <= 60:
            score += 15
        elif 35 <= rsi <= 65:
            score += 10
        
        return min(100, max(0, score))
    
    def _predict_direction(self, current: pd.Series, df: pd.DataFrame) -> Tuple[str, float]:
        """Predict breakout direction and confidence.
        
        Returns:
            Tuple of (direction, confidence) where direction is BULLISH/BEARISH/NEUTRAL
            and confidence is 0-100
        """
        bullish_score = 0
        bearish_score = 0
        
        # RSI analysis (weight: 2)
        rsi = current['rsi']
        if rsi < 45:
            bullish_score += 2
        elif rsi > 55:
            bearish_score += 2
        
        # MACD analysis (weight: 2)
        if current['macd'] > current['macd_signal']:
            bullish_score += 2
        else:
            bearish_score += 2
        
        # Price position in bands (weight: 2)
        bb_percent = current['bb_percent']
        if bb_percent < 0.4:
            bullish_score += 2
        elif bb_percent > 0.6:
            bearish_score += 2
        
        # Recent price trend (weight: 2)
        if len(df) >= 5:
            recent_trend = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            if recent_trend > 0.01:
                bullish_score += 2
            elif recent_trend < -0.01:
                bearish_score += 2
        
        # Volume trend (weight: 1)
        if current['volume_ratio'] > 1.0:
            # Volume increasing slightly favors continuation
            if bullish_score > bearish_score:
                bullish_score += 1
            else:
                bearish_score += 1
        
        # Determine direction
        total = bullish_score + bearish_score
        if total == 0:
            return 'NEUTRAL', 50.0
        
        if bullish_score > bearish_score:
            confidence = (bullish_score / total) * 100
            return 'BULLISH', confidence
        elif bearish_score > bullish_score:
            confidence = (bearish_score / total) * 100
            return 'BEARISH', confidence
        else:
            return 'NEUTRAL', 50.0
    
    def _get_indicator_summary(self, current: pd.Series) -> Dict:
        """Get summary of all indicators for display."""
        return {
            'bb_width': f"{current['bb_width']:.4f}",
            'bb_percentile': f"{current['bb_percentile']:.1f}",
            'rsi': f"{current['rsi']:.1f}",
            'macd': f"{current['macd']:.3f}",
            'volume_ratio': f"{current['volume_ratio']:.2f}"
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result when no squeeze detected."""
        return {
            'in_squeeze': False,
            'squeeze_strength': 0,
            'days_in_squeeze': 0,
            'direction': 'NEUTRAL',
            'confidence': 0,
            'price': 0,
            'bb_width': 0,
            'bb_percentile': 0,
            'rsi': 0,
            'rsi_signal': 'neutral',
            'macd': 0,
            'macd_signal': 'neutral',
            'volume_ratio': 0,
            'volume_declining': False,
            'indicators': {}
        }
