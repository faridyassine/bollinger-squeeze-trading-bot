"""Advanced Bollinger Squeeze detection with comprehensive analysis.

This module implements sophisticated squeeze detection logic with:
- Squeeze strength scoring (0-100)
- Breakout probability calculation
- Support/resistance identification
- Target price calculation
- Trading recommendations
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
from datetime import datetime

from .indicators import (
    calculate_all_indicators,
    calculate_atr,
    calculate_support_resistance
)


@dataclass
class SqueezeSignal:
    """Complete squeeze analysis signal with all metrics and recommendations."""
    
    # Basic info
    symbol: str
    timestamp: datetime
    price: float
    
    # Squeeze metrics
    in_squeeze: bool
    squeeze_strength: float  # 0-100 score
    days_in_squeeze: int
    
    # Direction prediction
    direction: str  # BULLISH, BEARISH, NEUTRAL
    bullish_probability: float  # 0-100
    bearish_probability: float  # 0-100
    confidence: float  # 0-100
    
    # Technical indicators
    bb_width: float
    bb_percentile: float
    bb_percent: float  # %B position
    rsi: float
    rsi_signal: str
    macd: float
    macd_signal: float
    macd_histogram: float
    macd_signal_type: str
    volume_ratio: float
    volume_declining: bool
    atr: float
    
    # Moving averages
    ma_9: Optional[float] = None
    ma_20: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    
    # Support/Resistance
    support_level: float = 0.0
    resistance_level: float = 0.0
    
    # Breakout targets
    target_1: float = 0.0  # Conservative
    target_2: float = 0.0  # Moderate
    target_3: float = 0.0  # Aggressive
    stop_loss: float = 0.0
    
    # Trading recommendation
    recommendation: str = "NEUTRAL"  # BUY, SELL, HOLD, NEUTRAL
    risk_reward_ratio: float = 0.0
    position_size_pct: float = 0.0  # Suggested % of portfolio
    
    # Additional context
    indicators: Dict = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


class SqueezeDetector:
    """Advanced Bollinger Squeeze pattern detector with comprehensive analysis."""
    
    def __init__(
        self,
        bollinger_period: int = 20,
        bollinger_std: float = 2.0,
        squeeze_threshold: float = 1.0,  # BB width threshold (% of price)
        min_days_in_squeeze: int = 2,
        max_days_in_squeeze: int = 15,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9
    ):
        """Initialize squeeze detector with strategy parameters.
        
        Args:
            bollinger_period: Bollinger Bands period
            bollinger_std: Bollinger Bands standard deviation
            squeeze_threshold: Threshold for squeeze detection (BB width < X%)
            min_days_in_squeeze: Minimum days to confirm squeeze
            max_days_in_squeeze: Maximum days before squeeze expires
            rsi_period: RSI period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
        """
        self.bollinger_period = bollinger_period
        self.bollinger_std = bollinger_std
        self.squeeze_threshold = squeeze_threshold
        self.min_days_in_squeeze = min_days_in_squeeze
        self.max_days_in_squeeze = max_days_in_squeeze
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal_period = macd_signal
    
    def detect(self, symbol: str, data: pd.DataFrame) -> SqueezeSignal:
        """Detect squeeze pattern and generate complete analysis.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV data
            
        Returns:
            SqueezeSignal with complete analysis or None if no squeeze
        """
        # Calculate all indicators
        df = calculate_all_indicators(
            data,
            rsi_period=self.rsi_period,
            macd_fast=self.macd_fast,
            macd_slow=self.macd_slow,
            macd_signal=self.macd_signal_period,
            bb_period=self.bollinger_period,
            bb_std=self.bollinger_std
        )
        df = calculate_atr(df)
        
        # Get current state
        current = df.iloc[-1]
        
        # Check if in squeeze (BB width < threshold)
        in_squeeze = current['bb_width'] < (self.squeeze_threshold / 100.0)
        
        # Count consecutive days in squeeze
        days_in_squeeze = self._count_squeeze_days(df, self.squeeze_threshold / 100.0)
        
        # Calculate squeeze strength (0-100)
        squeeze_strength = self._calculate_squeeze_strength(current, df, days_in_squeeze)
        
        # Predict breakout direction and calculate probabilities
        direction, bullish_prob, bearish_prob, confidence = self._predict_breakout(current, df)
        
        # Calculate support/resistance levels
        support, resistance = calculate_support_resistance(df)
        
        # Calculate breakout targets and stop loss
        target_1, target_2, target_3, stop_loss = self._calculate_targets(
            current, support, resistance, df
        )
        
        # Generate trading recommendation
        recommendation, risk_reward, position_size = self._generate_recommendation(
            in_squeeze, squeeze_strength, days_in_squeeze,
            direction, confidence, current, target_2, stop_loss
        )
        
        # Get RSI and MACD signals
        rsi_signal = self._get_rsi_signal(current['rsi'])
        macd_signal_type = self._get_macd_signal(
            current['macd'], current['macd_signal'], current['macd_histogram']
        )
        
        # Build squeeze signal
        signal = SqueezeSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            price=float(current['close']),
            in_squeeze=in_squeeze,
            squeeze_strength=squeeze_strength,
            days_in_squeeze=days_in_squeeze,
            direction=direction,
            bullish_probability=bullish_prob,
            bearish_probability=bearish_prob,
            confidence=confidence,
            bb_width=float(current['bb_width']),
            bb_percentile=float(current['bb_width_percentile']),
            bb_percent=float(current['bb_percent']),
            rsi=float(current['rsi']),
            rsi_signal=rsi_signal,
            macd=float(current['macd']),
            macd_signal=float(current['macd_signal']),
            macd_histogram=float(current['macd_histogram']),
            macd_signal_type=macd_signal_type,
            volume_ratio=float(current['volume_ratio']),
            volume_declining=bool(current['volume_declining']),
            atr=float(current['atr']),
            ma_9=float(current.get('ma_9', 0)),
            ma_20=float(current.get('ma_20', 0)),
            ma_50=float(current.get('ma_50', 0)),
            ma_200=float(current.get('ma_200', 0)),
            support_level=support,
            resistance_level=resistance,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            stop_loss=stop_loss,
            recommendation=recommendation,
            risk_reward_ratio=risk_reward,
            position_size_pct=position_size,
            indicators=self._get_indicator_summary(current),
            notes=self._generate_notes(in_squeeze, days_in_squeeze, squeeze_strength, direction)
        )
        
        return signal
    
    def _count_squeeze_days(self, df: pd.DataFrame, threshold: float) -> int:
        """Count consecutive days in squeeze."""
        in_squeeze = (df['bb_width'] < threshold).values
        count = 0
        
        for i in range(len(in_squeeze) - 1, -1, -1):
            if in_squeeze[i]:
                count += 1
            else:
                break
        
        return count
    
    def _calculate_squeeze_strength(
        self, current: pd.Series, df: pd.DataFrame, days_in_squeeze: int
    ) -> float:
        """Calculate squeeze strength score (0-100).
        
        Factors (weights):
        - BB width compression (40 points): Tighter bands = higher score
        - Volume decline (30 points): Declining volume = higher score
        - MA convergence (30 points): MAs close together = higher score
        """
        score = 0.0
        
        # 1. BB width compression (40 points max)
        # Lower width percentile = higher score
        percentile = current['bb_width_percentile']
        if percentile <= 5:
            score += 40
        elif percentile <= 10:
            score += 35
        elif percentile <= 15:
            score += 30
        elif percentile <= 20:
            score += 20
        else:
            score += max(0, (100 - percentile) / 100 * 20)
        
        # 2. Volume decline (30 points max)
        if current['volume_declining']:
            score += 15
        
        # Recent volume trend
        recent_vol_avg = df['volume'].tail(5).mean()
        older_vol_avg = df['volume'].tail(20).mean()
        vol_decline_pct = (older_vol_avg - recent_vol_avg) / older_vol_avg
        score += min(15, max(0, vol_decline_pct * 100))
        
        # 3. MA convergence (30 points max)
        if 'ma_9' in current.index and 'ma_50' in current.index:
            ma_9 = current['ma_9']
            ma_20 = current.get('ma_20', current['close'])
            ma_50 = current['ma_50']
            
            if not (np.isnan(ma_9) or np.isnan(ma_50)):
                # Calculate MA spread as % of price
                ma_spread = abs(ma_50 - ma_9) / current['close']
                # Tighter convergence = higher score
                convergence_score = max(0, (0.05 - ma_spread) / 0.05 * 30)
                score += convergence_score
        
        return min(100.0, max(0.0, score))
    
    def _predict_breakout(
        self, current: pd.Series, df: pd.DataFrame
    ) -> Tuple[str, float, float, float]:
        """Predict breakout direction with probabilities.
        
        Returns:
            Tuple of (direction, bullish_prob, bearish_prob, confidence)
        """
        bullish_score = 0.0
        bearish_score = 0.0
        
        # 1. RSI position (15 points)
        rsi = current['rsi']
        if rsi < 40:
            bullish_score += 15
        elif rsi < 50:
            bullish_score += 10
        elif rsi > 60:
            bearish_score += 15
        elif rsi > 50:
            bearish_score += 10
        
        # 2. MACD histogram (20 points)
        if current['macd_histogram'] > 0:
            bullish_score += 20 * min(1.0, abs(current['macd_histogram']) / 0.5)
        else:
            bearish_score += 20 * min(1.0, abs(current['macd_histogram']) / 0.5)
        
        # 3. Price vs MA50 (15 points)
        if 'ma_50' in current.index and not np.isnan(current['ma_50']):
            price_vs_ma = (current['close'] - current['ma_50']) / current['ma_50']
            if price_vs_ma > 0.02:
                bullish_score += 15
            elif price_vs_ma < -0.02:
                bearish_score += 15
            else:
                # Proportional scoring
                if price_vs_ma > 0:
                    bullish_score += abs(price_vs_ma) / 0.02 * 15
                else:
                    bearish_score += abs(price_vs_ma) / 0.02 * 15
        
        # 4. BB %B position (10 points)
        bb_percent = current['bb_percent']
        if bb_percent < 0.3:
            bullish_score += 10
        elif bb_percent > 0.7:
            bearish_score += 10
        
        # 5. Recent trend (10 points)
        if len(df) >= 10:
            recent_trend = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
            if recent_trend > 0.02:
                bullish_score += 10
            elif recent_trend < -0.02:
                bearish_score += 10
        
        # Calculate probabilities
        total = bullish_score + bearish_score
        if total == 0:
            return 'NEUTRAL', 50.0, 50.0, 0.0
        
        bullish_prob = (bullish_score / total) * 100
        bearish_prob = (bearish_score / total) * 100
        
        # Determine direction and confidence
        if bullish_score > bearish_score:
            direction = 'BULLISH'
            confidence = min(100.0, (bullish_score / 70) * 100)  # 70 is max theoretical score
        elif bearish_score > bullish_score:
            direction = 'BEARISH'
            confidence = min(100.0, (bearish_score / 70) * 100)
        else:
            direction = 'NEUTRAL'
            confidence = 50.0
        
        return direction, bullish_prob, bearish_prob, confidence
    
    def _calculate_targets(
        self, current: pd.Series, support: float, resistance: float, df: pd.DataFrame
    ) -> Tuple[float, float, float, float]:
        """Calculate breakout targets (T1, T2, T3) and stop loss.
        
        Targets based on:
        - BB width (measure of expected move)
        - ATR (volatility-adjusted)
        - Support/resistance levels
        """
        price = current['close']
        atr = current['atr']
        bb_width_dollars = current['bb_upper'] - current['bb_lower']
        
        # Stop loss: 2x ATR or support level
        stop_loss = min(price - (2 * atr), support)
        
        # Targets based on BB width and ATR
        # T1 (Conservative): 1x BB width or 1.5x ATR
        target_1 = price + max(bb_width_dollars, 1.5 * atr)
        
        # T2 (Moderate): 1.5x BB width or 2.5x ATR
        target_2 = price + max(bb_width_dollars * 1.5, 2.5 * atr)
        
        # T3 (Aggressive): 2x BB width or 3.5x ATR
        target_3 = price + max(bb_width_dollars * 2, 3.5 * atr)
        
        # Adjust targets to align with resistance if close
        if resistance > price:
            if abs(target_1 - resistance) < atr:
                target_1 = resistance * 1.01
            if abs(target_2 - resistance) < atr:
                target_2 = resistance * 1.02
        
        return target_1, target_2, target_3, stop_loss
    
    def _generate_recommendation(
        self,
        in_squeeze: bool,
        squeeze_strength: float,
        days_in_squeeze: int,
        direction: str,
        confidence: float,
        current: pd.Series,
        target: float,
        stop_loss: float
    ) -> Tuple[str, float, float]:
        """Generate trading recommendation with risk/reward and position size.
        
        Returns:
            Tuple of (recommendation, risk_reward_ratio, position_size_pct)
        """
        # Default values
        recommendation = "NEUTRAL"
        risk_reward = 0.0
        position_size = 0.0
        
        # Only recommend if valid squeeze
        if not in_squeeze or days_in_squeeze < self.min_days_in_squeeze:
            return recommendation, risk_reward, position_size
        
        # Calculate risk/reward
        price = current['close']
        potential_gain = target - price
        potential_loss = price - stop_loss
        
        if potential_loss > 0:
            risk_reward = potential_gain / potential_loss
        
        # Generate recommendation based on criteria
        if (squeeze_strength >= 60 and 
            confidence >= 65 and 
            self.min_days_in_squeeze <= days_in_squeeze <= self.max_days_in_squeeze and
            risk_reward >= 2.0):
            
            if direction == 'BULLISH':
                recommendation = "BUY"
            elif direction == 'BEARISH':
                recommendation = "SELL"
            else:
                recommendation = "HOLD"
            
            # Position size based on confidence and risk/reward
            # Higher confidence and R/R = larger position (max 5% of portfolio)
            base_size = 2.0  # Base 2%
            confidence_multiplier = confidence / 100.0
            rr_multiplier = min(1.5, risk_reward / 3.0)
            position_size = base_size * confidence_multiplier * rr_multiplier
            position_size = min(5.0, max(1.0, position_size))
        
        elif squeeze_strength >= 50 and confidence >= 60 and risk_reward >= 1.5:
            recommendation = "HOLD"  # Wait for better setup
            position_size = 1.0
        
        else:
            recommendation = "NEUTRAL"
            position_size = 0.0
        
        return recommendation, risk_reward, position_size
    
    def _get_rsi_signal(self, rsi: float) -> str:
        """Get RSI signal interpretation."""
        if rsi < 30:
            return 'oversold'
        elif rsi > 70:
            return 'overbought'
        elif rsi < 40:
            return 'bullish'
        elif rsi > 60:
            return 'bearish'
        else:
            return 'neutral'
    
    def _get_macd_signal(self, macd: float, signal: float, histogram: float) -> str:
        """Get MACD signal interpretation."""
        if macd > signal and histogram > 0:
            return 'bullish'
        elif macd < signal and histogram < 0:
            return 'bearish'
        elif histogram > 0 and histogram > abs(histogram) * 0.5:
            return 'strengthening_bullish'
        elif histogram < 0 and abs(histogram) > histogram * 0.5:
            return 'strengthening_bearish'
        else:
            return 'neutral'
    
    def _get_indicator_summary(self, current: pd.Series) -> Dict:
        """Get formatted summary of all indicators."""
        return {
            'bb_width': f"{current['bb_width']*100:.2f}%",
            'bb_percentile': f"{current['bb_width_percentile']:.1f}",
            'bb_percent': f"{current['bb_percent']*100:.1f}%",
            'rsi': f"{current['rsi']:.1f}",
            'macd': f"{current['macd']:.3f}",
            'macd_histogram': f"{current['macd_histogram']:.3f}",
            'volume_ratio': f"{current['volume_ratio']:.2f}x",
            'atr': f"{current['atr']:.2f}"
        }
    
    def _generate_notes(
        self, in_squeeze: bool, days: int, strength: float, direction: str
    ) -> List[str]:
        """Generate contextual notes about the squeeze."""
        notes = []
        
        if not in_squeeze:
            notes.append("No squeeze detected - BB width above threshold")
        elif days < self.min_days_in_squeeze:
            notes.append(f"Squeeze too new ({days} days, need {self.min_days_in_squeeze})")
        elif days > self.max_days_in_squeeze:
            notes.append(f"Squeeze expired ({days} days, max {self.max_days_in_squeeze})")
        else:
            notes.append(f"Valid squeeze detected ({days} days)")
        
        if strength >= 80:
            notes.append("⚡ Exceptionally strong squeeze - high breakout potential")
        elif strength >= 60:
            notes.append("✓ Strong squeeze - good breakout potential")
        elif strength >= 40:
            notes.append("~ Moderate squeeze - watch for confirmation")
        else:
            notes.append("⚠ Weak squeeze - low probability setup")
        
        if direction != 'NEUTRAL':
            notes.append(f"Bias: {direction}")
        
        return notes
