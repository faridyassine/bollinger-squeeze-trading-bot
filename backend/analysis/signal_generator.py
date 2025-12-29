"""Signal generation module for trading decisions.

Generates buy/sell signals based on squeeze analysis and patterns with:
- Entry prices and timing
- Stop loss calculations
- Target levels (T1, T2, T3)
- Risk/reward ratios
- Position sizing recommendations
- Signal strength and confidence
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

from .squeeze_detector import SqueezeSignal
from .pattern_recognition import Pattern


@dataclass
class TradingSignal:
    """Complete trading signal with entry/exit strategy."""
    
    # Signal basics
    symbol: str
    timestamp: datetime
    signal_type: str  # BUY, SELL, HOLD, CLOSE
    signal_strength: float  # 0-100
    confidence: float  # 0-100
    
    # Entry strategy
    entry_price: float
    entry_timing: str  # IMMEDIATE, ON_BREAKOUT, ON_PULLBACK
    entry_conditions: List[str]
    
    # Exit strategy
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    trailing_stop_pct: float  # For active position management
    
    # Risk management
    risk_amount: float  # $ risk per share
    risk_pct: float  # % risk of entry
    reward_amount: float  # $ potential reward (to T2)
    risk_reward_ratio: float
    
    # Position sizing
    position_size_pct: float  # % of portfolio
    position_size_shares: Optional[int] = None  # If capital known
    capital_required: Optional[float] = None
    
    # Supporting analysis
    squeeze_signal: Optional[SqueezeSignal] = None
    patterns: List[Pattern] = None
    rationale: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.patterns is None:
            self.patterns = []
        if self.rationale is None:
            self.rationale = []
        if self.warnings is None:
            self.warnings = []


class SignalGenerator:
    """Generates trading signals from squeeze analysis and patterns."""
    
    def __init__(
        self,
        min_squeeze_strength: float = 50.0,
        min_confidence: float = 60.0,
        min_risk_reward: float = 2.0,
        max_risk_pct: float = 2.0,  # Max 2% risk per trade
        portfolio_value: Optional[float] = None
    ):
        """Initialize signal generator.
        
        Args:
            min_squeeze_strength: Minimum squeeze strength to generate signal
            min_confidence: Minimum confidence to generate signal
            min_risk_reward: Minimum risk/reward ratio
            max_risk_pct: Maximum risk per trade (% of portfolio)
            portfolio_value: Total portfolio value for position sizing
        """
        self.min_squeeze_strength = min_squeeze_strength
        self.min_confidence = min_confidence
        self.min_risk_reward = min_risk_reward
        self.max_risk_pct = max_risk_pct
        self.portfolio_value = portfolio_value
    
    def generate_signal(
        self,
        squeeze_signal: SqueezeSignal,
        patterns: Optional[List[Pattern]] = None,
        current_position: Optional[Dict] = None
    ) -> Optional[TradingSignal]:
        """Generate trading signal from squeeze analysis.
        
        Args:
            squeeze_signal: Squeeze detection results
            patterns: Optional list of detected patterns
            current_position: Optional dict with current position info
            
        Returns:
            TradingSignal or None if no valid signal
        """
        if patterns is None:
            patterns = []
        
        # Check if we already have a position
        if current_position and current_position.get('quantity', 0) > 0:
            return self._generate_exit_signal(squeeze_signal, current_position, patterns)
        
        # Check minimum requirements for entry signal
        if not self._meets_entry_requirements(squeeze_signal):
            return None
        
        # Determine signal type and strength
        signal_type, signal_strength = self._determine_signal_type(squeeze_signal, patterns)
        
        if signal_type == "HOLD":
            return None
        
        # Calculate entry price and timing
        entry_price, entry_timing, entry_conditions = self._calculate_entry_strategy(
            squeeze_signal, patterns
        )
        
        # Calculate stop loss and targets
        stop_loss = self._calculate_stop_loss(squeeze_signal, entry_price)
        target_1 = squeeze_signal.target_1
        target_2 = squeeze_signal.target_2
        target_3 = squeeze_signal.target_3
        
        # Calculate risk/reward
        risk_amount = entry_price - stop_loss
        reward_amount = target_2 - entry_price
        risk_pct = (risk_amount / entry_price) * 100
        risk_reward = reward_amount / risk_amount if risk_amount > 0 else 0
        
        # Skip if R/R is too low
        if risk_reward < self.min_risk_reward:
            return None
        
        # Calculate position size
        position_size_pct = self._calculate_position_size(
            signal_strength,
            risk_reward,
            risk_pct,
            squeeze_signal.confidence
        )
        
        # Calculate shares if portfolio value is known
        position_size_shares = None
        capital_required = None
        if self.portfolio_value:
            capital_required = self.portfolio_value * (position_size_pct / 100)
            position_size_shares = int(capital_required / entry_price)
        
        # Generate rationale and warnings
        rationale = self._generate_rationale(squeeze_signal, patterns, signal_type)
        warnings = self._generate_warnings(squeeze_signal, risk_pct, risk_reward)
        
        # Calculate trailing stop
        trailing_stop_pct = min(15.0, risk_pct * 1.5)
        
        return TradingSignal(
            symbol=squeeze_signal.symbol,
            timestamp=datetime.now(),
            signal_type=signal_type,
            signal_strength=signal_strength,
            confidence=squeeze_signal.confidence,
            entry_price=entry_price,
            entry_timing=entry_timing,
            entry_conditions=entry_conditions,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            trailing_stop_pct=trailing_stop_pct,
            risk_amount=risk_amount,
            risk_pct=risk_pct,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward,
            position_size_pct=position_size_pct,
            position_size_shares=position_size_shares,
            capital_required=capital_required,
            squeeze_signal=squeeze_signal,
            patterns=patterns,
            rationale=rationale,
            warnings=warnings
        )
    
    def _meets_entry_requirements(self, signal: SqueezeSignal) -> bool:
        """Check if squeeze signal meets minimum requirements."""
        return (
            signal.in_squeeze and
            signal.squeeze_strength >= self.min_squeeze_strength and
            signal.confidence >= self.min_confidence and
            signal.days_in_squeeze >= 2 and
            signal.recommendation in ['BUY', 'SELL']
        )
    
    def _determine_signal_type(
        self, signal: SqueezeSignal, patterns: List[Pattern]
    ) -> tuple:
        """Determine signal type and strength.
        
        Returns:
            Tuple of (signal_type, signal_strength)
        """
        base_strength = (signal.squeeze_strength + signal.confidence) / 2
        
        # Adjust strength based on patterns
        pattern_boost = 0.0
        bullish_patterns = sum(1 for p in patterns if p.signal == 'BULLISH')
        bearish_patterns = sum(1 for p in patterns if p.signal == 'BEARISH')
        
        if signal.direction == 'BULLISH':
            pattern_boost = bullish_patterns * 5.0
            signal_type = 'BUY'
        elif signal.direction == 'BEARISH':
            pattern_boost = bearish_patterns * 5.0
            signal_type = 'SELL'
        else:
            signal_type = 'HOLD'
        
        signal_strength = min(100.0, base_strength + pattern_boost)
        
        return signal_type, signal_strength
    
    def _calculate_entry_strategy(
        self, signal: SqueezeSignal, patterns: List[Pattern]
    ) -> tuple:
        """Calculate entry price, timing, and conditions.
        
        Returns:
            Tuple of (entry_price, entry_timing, entry_conditions)
        """
        entry_price = signal.price
        entry_conditions = []
        
        # Determine entry timing based on squeeze characteristics
        if signal.squeeze_strength >= 75:
            # Very strong squeeze - wait for breakout
            entry_timing = "ON_BREAKOUT"
            if signal.direction == 'BULLISH':
                entry_price = signal.resistance_level * 1.002  # 0.2% above resistance
                entry_conditions.append("Wait for breakout above resistance")
                entry_conditions.append("Confirm with increased volume")
            else:
                entry_price = signal.support_level * 0.998  # 0.2% below support
                entry_conditions.append("Wait for breakdown below support")
                entry_conditions.append("Confirm with increased volume")
        
        elif signal.squeeze_strength >= 60:
            # Strong squeeze - can enter on pullback
            entry_timing = "ON_PULLBACK"
            if signal.direction == 'BULLISH':
                entry_price = signal.price * 0.995  # 0.5% pullback
                entry_conditions.append("Enter on minor pullback")
                entry_conditions.append("Watch for RSI < 50")
            else:
                entry_price = signal.price * 1.005  # 0.5% bounce
                entry_conditions.append("Enter on minor bounce")
                entry_conditions.append("Watch for RSI > 50")
        
        else:
            # Moderate squeeze - immediate entry acceptable
            entry_timing = "IMMEDIATE"
            entry_conditions.append("Can enter at current price")
            entry_conditions.append("Monitor squeeze progression")
        
        # Add pattern-based conditions
        for pattern in patterns:
            if pattern.signal == signal.direction:
                entry_conditions.append(f"Confirmed by {pattern.pattern_type}")
        
        return entry_price, entry_timing, entry_conditions
    
    def _calculate_stop_loss(self, signal: SqueezeSignal, entry_price: float) -> float:
        """Calculate optimal stop loss level."""
        # Use the squeeze signal's calculated stop loss
        stop_loss = signal.stop_loss
        
        # Ensure stop loss is reasonable (max 5% from entry)
        max_stop_distance = entry_price * 0.05
        
        if signal.direction == 'BULLISH':
            min_stop = entry_price - max_stop_distance
            stop_loss = max(stop_loss, min_stop)
        else:
            max_stop = entry_price + max_stop_distance
            stop_loss = min(stop_loss, max_stop)
        
        return stop_loss
    
    def _calculate_position_size(
        self,
        signal_strength: float,
        risk_reward: float,
        risk_pct: float,
        confidence: float
    ) -> float:
        """Calculate position size as % of portfolio.
        
        Based on:
        - Signal strength
        - Risk/reward ratio
        - Confidence level
        - Risk per trade
        """
        # Base size: 2% of portfolio
        base_size = 2.0
        
        # Scale by signal strength (0.5x to 1.5x)
        strength_multiplier = 0.5 + (signal_strength / 100.0)
        
        # Scale by confidence (0.7x to 1.3x)
        confidence_multiplier = 0.7 + (confidence / 100.0) * 0.6
        
        # Scale by risk/reward (1.0x to 1.5x for R/R 2:1 to 4:1)
        rr_multiplier = min(1.5, 0.5 + (risk_reward / 4.0))
        
        # Calculate position size
        position_size = base_size * strength_multiplier * confidence_multiplier * rr_multiplier
        
        # Cap at maximum based on risk
        max_size_by_risk = (self.max_risk_pct / risk_pct) * 100
        position_size = min(position_size, max_size_by_risk, 10.0)  # Max 10% position
        
        return round(position_size, 2)
    
    def _generate_exit_signal(
        self,
        signal: SqueezeSignal,
        position: Dict,
        patterns: List[Pattern]
    ) -> Optional[TradingSignal]:
        """Generate exit signal for existing position."""
        # Check if squeeze has resolved (width expanding)
        if signal.bb_width > 0.015:  # 1.5% width
            return TradingSignal(
                symbol=signal.symbol,
                timestamp=datetime.now(),
                signal_type='CLOSE',
                signal_strength=75.0,
                confidence=80.0,
                entry_price=position['entry_price'],
                entry_timing='IMMEDIATE',
                entry_conditions=['Squeeze resolved'],
                stop_loss=position['stop_loss'],
                target_1=signal.target_1,
                target_2=signal.target_2,
                target_3=signal.target_3,
                trailing_stop_pct=10.0,
                risk_amount=position['entry_price'] - position['stop_loss'],
                risk_pct=2.0,
                reward_amount=signal.target_2 - position['entry_price'],
                risk_reward_ratio=2.0,
                position_size_pct=0.0,
                squeeze_signal=signal,
                rationale=['Squeeze has resolved - take profits'],
                warnings=[]
            )
        
        return None
    
    def _generate_rationale(
        self, signal: SqueezeSignal, patterns: List[Pattern], signal_type: str
    ) -> List[str]:
        """Generate trade rationale."""
        rationale = []
        
        # Squeeze analysis
        rationale.append(
            f"Strong squeeze detected: {signal.squeeze_strength:.0f}/100 strength, "
            f"{signal.days_in_squeeze} days"
        )
        
        # Direction bias
        rationale.append(
            f"{signal.direction} bias with {signal.confidence:.0f}% confidence"
        )
        
        # Technical indicators
        if signal.rsi_signal in ['oversold', 'overbought']:
            rationale.append(f"RSI {signal.rsi:.0f} is {signal.rsi_signal}")
        
        if signal.macd_signal_type != 'neutral':
            rationale.append(f"MACD is {signal.macd_signal_type}")
        
        # Patterns
        for pattern in patterns:
            if pattern.signal == signal.direction:
                rationale.append(f"Confirmed by {pattern.description}")
        
        # Risk/reward
        rationale.append(
            f"Risk/Reward: {signal.risk_reward_ratio:.1f}:1"
        )
        
        return rationale
    
    def _generate_warnings(
        self, signal: SqueezeSignal, risk_pct: float, risk_reward: float
    ) -> List[str]:
        """Generate trade warnings."""
        warnings = []
        
        # High risk warning
        if risk_pct > 3.0:
            warnings.append(f"⚠️ High risk: {risk_pct:.1f}% per trade")
        
        # Low confidence warning
        if signal.confidence < 65:
            warnings.append(f"⚠️ Moderate confidence: {signal.confidence:.0f}%")
        
        # Volume warning
        if not signal.volume_declining:
            warnings.append("⚠️ Volume not declining - squeeze may be weak")
        
        # Squeeze duration warnings
        if signal.days_in_squeeze < 3:
            warnings.append(f"⚠️ Early squeeze: only {signal.days_in_squeeze} days")
        elif signal.days_in_squeeze > 10:
            warnings.append(f"⚠️ Old squeeze: {signal.days_in_squeeze} days")
        
        # Conflicting indicators
        if signal.direction == 'BULLISH' and signal.rsi > 70:
            warnings.append("⚠️ RSI overbought - may limit upside")
        elif signal.direction == 'BEARISH' and signal.rsi < 30:
            warnings.append("⚠️ RSI oversold - may limit downside")
        
        return warnings
