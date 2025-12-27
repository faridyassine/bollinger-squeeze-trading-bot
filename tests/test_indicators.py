"""Tests for technical indicators."""
import pytest
import pandas as pd
import numpy as np
from backend.indicators import (
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_macd,
    calculate_volume_indicators,
    SqueezeDetector
)


def test_bollinger_bands(sample_ohlcv_data):
    """Test Bollinger Bands calculation."""
    result = calculate_bollinger_bands(sample_ohlcv_data, period=20, std_dev=2.0)
    
    assert 'bb_upper' in result.columns
    assert 'bb_middle' in result.columns
    assert 'bb_lower' in result.columns
    assert 'bb_width' in result.columns
    
    # Check that upper is above middle is above lower (skip NaN values)
    valid_data = result.dropna()
    assert (valid_data['bb_upper'] >= valid_data['bb_middle']).all()
    assert (valid_data['bb_middle'] >= valid_data['bb_lower']).all()


def test_rsi(sample_ohlcv_data):
    """Test RSI calculation."""
    result = calculate_rsi(sample_ohlcv_data, period=14)
    
    assert 'rsi' in result.columns
    assert (result['rsi'] >= 0).all()
    assert (result['rsi'] <= 100).all()


def test_macd(sample_ohlcv_data):
    """Test MACD calculation."""
    result = calculate_macd(sample_ohlcv_data)
    
    assert 'macd' in result.columns
    assert 'macd_signal' in result.columns
    assert 'macd_histogram' in result.columns


def test_volume_indicators(sample_ohlcv_data):
    """Test volume indicators."""
    result = calculate_volume_indicators(sample_ohlcv_data, period=20)
    
    assert 'volume_sma' in result.columns
    assert 'volume_ratio' in result.columns
    assert 'volume_trend' in result.columns


def test_squeeze_detector(sample_ohlcv_data):
    """Test squeeze detector."""
    detector = SqueezeDetector(
        bollinger_period=20,
        bollinger_std=2.0,
        squeeze_threshold=0.5,
        min_days_in_squeeze=2,
        max_days_in_squeeze=10
    )
    
    result = detector.analyze(sample_ohlcv_data)
    
    assert 'in_squeeze' in result
    assert 'squeeze_strength' in result
    assert 'days_in_squeeze' in result
    assert 'direction' in result
    assert 'confidence' in result
    
    # Check value ranges
    assert result['squeeze_strength'] >= 0
    assert result['squeeze_strength'] <= 100
    assert result['confidence'] >= 0
    assert result['confidence'] <= 100
    assert result['direction'] in ['BULLISH', 'BEARISH', 'NEUTRAL']
