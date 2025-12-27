"""Tests for backtesting engine."""
import pytest
import pandas as pd
from backend.backtesting import BacktestEngine
from backend.strategies import BollingerSqueezeStrategy


def test_backtest_engine_initialization():
    """Test backtest engine initialization."""
    strategy = BollingerSqueezeStrategy()
    engine = BacktestEngine(strategy, initial_capital=10000)
    
    assert engine.initial_capital == 10000
    assert engine.capital == 10000
    assert engine.trades == []


def test_backtest_run(sample_ohlcv_data):
    """Test running a backtest."""
    strategy = BollingerSqueezeStrategy()
    engine = BacktestEngine(strategy, initial_capital=10000)
    
    results = engine.run('TEST', sample_ohlcv_data)
    
    assert 'symbol' in results
    assert 'total_return' in results
    assert 'win_rate' in results
    assert 'total_trades' in results
    assert 'sharpe_ratio' in results
    assert 'max_drawdown' in results
    
    assert results['symbol'] == 'TEST'
    assert isinstance(results['total_return'], (int, float))
    assert results['win_rate'] >= 0
    assert results['win_rate'] <= 100
