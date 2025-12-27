"""Pydantic models for API request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class SqueezeResponse(BaseModel):
    """Response model for squeeze data."""
    symbol: str
    price: float
    squeeze_strength: float
    days_in_squeeze: int
    direction: str
    confidence: float
    bb_width: float
    bb_percentile: float
    rsi: float
    rsi_signal: str
    macd: float
    macd_signal: str
    volume_ratio: float
    volume_declining: bool
    detected_at: Optional[datetime] = None
    status: str = "active"


class BacktestRequest(BaseModel):
    """Request model for backtest."""
    symbol: str = Field(..., description="Stock symbol to backtest")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(10000, gt=0, description="Initial capital")
    strategy: str = Field("bollinger_squeeze", description="Strategy name")
    parameters: Optional[Dict] = Field(None, description="Strategy parameters")


class BacktestResponse(BaseModel):
    """Response model for backtest results."""
    symbol: str
    initial_capital: float
    final_equity: float
    total_return: float
    buy_hold_return: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    avg_win: float
    avg_loss: float
    start_date: datetime
    end_date: datetime


class WatchlistItem(BaseModel):
    """Model for watchlist item."""
    symbol: str
    added_at: Optional[datetime] = None
    notes: Optional[str] = None


class WatchlistAddRequest(BaseModel):
    """Request to add symbol to watchlist."""
    symbol: str = Field(..., description="Stock symbol")
    notes: Optional[str] = Field(None, description="Optional notes")


class AlertResponse(BaseModel):
    """Response model for alert."""
    id: int
    type: str
    channel: str
    message: str
    sent_at: datetime
    success: bool
    error: Optional[str] = None


class StatsResponse(BaseModel):
    """Response model for system statistics."""
    active_squeezes: int
    watchlist_size: int
    total_alerts_sent: int
    total_backtests_run: int
    scanner_status: str
    last_scan: Optional[datetime] = None


class ScanRequest(BaseModel):
    """Request to scan specific symbols."""
    symbols: List[str] = Field(..., description="List of symbols to scan")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Generic success response."""
    message: str
    data: Optional[Dict] = None
