"""Backtesting package."""
from .engine import BacktestEngine
from .metrics import (
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_information_ratio,
    calculate_trade_metrics,
    calculate_monthly_returns,
    calculate_risk_metrics
)
from .reports import generate_html_report

__all__ = [
    'BacktestEngine',
    'calculate_sortino_ratio',
    'calculate_calmar_ratio',
    'calculate_information_ratio',
    'calculate_trade_metrics',
    'calculate_monthly_returns',
    'calculate_risk_metrics',
    'generate_html_report'
]
