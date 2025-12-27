"""Tests for trading strategies."""
import pytest
import pandas as pd
from backend.strategies import BollingerSqueezeStrategy


def test_bollinger_squeeze_strategy_initialization():
    """Test strategy initialization."""
    strategy = BollingerSqueezeStrategy()
    
    assert strategy.name == 'BollingerSqueeze'
    assert 'bollinger_period' in strategy.params
    assert 'squeeze_threshold' in strategy.params


def test_generate_signals(sample_ohlcv_data):
    """Test signal generation."""
    strategy = BollingerSqueezeStrategy()
    
    result = strategy.generate_signals(sample_ohlcv_data)
    
    assert 'signal' in result.columns
    assert result['signal'].isin([0, 1, -1]).all()


def test_position_sizing():
    """Test position size calculation."""
    strategy = BollingerSqueezeStrategy()
    
    capital = 10000
    price = 100
    atr = 2.0
    
    shares = strategy.calculate_position_size(capital, price, atr=atr)
    
    assert shares > 0
    assert isinstance(shares, int)
