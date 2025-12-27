"""FastAPI REST endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from backend.api.models import (
    SqueezeResponse,
    BacktestRequest,
    BacktestResponse,
    WatchlistItem,
    WatchlistAddRequest,
    AlertResponse,
    StatsResponse,
    ScanRequest,
    SuccessResponse,
    ErrorResponse
)
from backend.core.config import config
from backend.core.database import Database, Squeeze, Alert, Watchlist, Backtest
from backend.scanner import MarketScanner
from backend.strategies import BollingerSqueezeStrategy
from backend.backtesting import BacktestEngine
from backend.data import YahooFinanceProvider
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Initialize components
db = Database(
    db_type=config.database.get('type', 'sqlite'),
    db_path=config.database.get('path', 'data/trading.db')
)
scanner = MarketScanner()
data_provider = YahooFinanceProvider()


@router.get("/squeezes", response_model=List[SqueezeResponse])
async def get_squeezes(
    status: str = Query("active", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results")
):
    """Get active squeezes."""
    session = db.get_session()
    
    try:
        squeezes = session.query(Squeeze).filter_by(status=status).order_by(
            Squeeze.squeeze_strength.desc()
        ).limit(limit).all()
        
        return [
            SqueezeResponse(
                symbol=sq.symbol,
                price=sq.price,
                squeeze_strength=sq.squeeze_strength,
                days_in_squeeze=sq.days_in_squeeze,
                direction=sq.direction,
                confidence=sq.confidence,
                bb_width=sq.bb_width,
                bb_percentile=0.0,  # Calculate if needed
                rsi=sq.rsi,
                rsi_signal="neutral",  # Calculate if needed
                macd=sq.macd,
                macd_signal="neutral",  # Calculate if needed
                volume_ratio=1.0,  # Calculate if needed
                volume_declining=False,  # Calculate if needed
                detected_at=sq.detected_at,
                status=sq.status
            )
            for sq in squeezes
        ]
    finally:
        session.close()


@router.get("/symbols/{symbol}", response_model=SqueezeResponse)
async def get_symbol_detail(symbol: str):
    """Get detailed squeeze analysis for a symbol."""
    try:
        result = scanner.scan_single_symbol_detailed(symbol)
        
        if not result['in_squeeze']:
            raise HTTPException(status_code=404, detail=f"No squeeze detected for {symbol}")
        
        return SqueezeResponse(
            symbol=result['symbol'],
            price=result['price'],
            squeeze_strength=result['squeeze_strength'],
            days_in_squeeze=result['days_in_squeeze'],
            direction=result['direction'],
            confidence=result['confidence'],
            bb_width=result['bb_width'],
            bb_percentile=result['bb_percentile'],
            rsi=result['rsi'],
            rsi_signal=result['rsi_signal'],
            macd=result['macd'],
            macd_signal=result['macd_signal'],
            volume_ratio=result['volume_ratio'],
            volume_declining=result['volume_declining'],
            detected_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error getting symbol detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """Run backtest for a strategy."""
    try:
        # Parse dates
        start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(request.end_date, '%Y-%m-%d')
        
        # Download data
        data = data_provider.get_historical_data(
            request.symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {request.symbol}")
        
        # Initialize strategy
        strategy_params = request.parameters or config.strategy.get('bollinger_squeeze', {})
        strategy = BollingerSqueezeStrategy(params=strategy_params)
        
        # Run backtest
        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=request.initial_capital,
            commission=config.backtesting.get('commission', 0.001),
            slippage=config.backtesting.get('slippage', 0.0005)
        )
        
        results = engine.run(request.symbol, data)
        
        # Save to database
        session = db.get_session()
        try:
            backtest = Backtest(
                symbol=request.symbol,
                strategy=request.strategy,
                start_date=results['start_date'],
                end_date=results['end_date'],
                initial_capital=results['initial_capital'],
                final_capital=results['final_equity'],
                total_return=results['total_return'],
                win_rate=results['win_rate'],
                profit_factor=results['profit_factor'],
                sharpe_ratio=results['sharpe_ratio'],
                max_drawdown=results['max_drawdown'],
                total_trades=results['total_trades'],
                parameters=str(strategy_params)
            )
            session.add(backtest)
            session.commit()
        finally:
            session.close()
        
        return BacktestResponse(
            symbol=results['symbol'],
            initial_capital=results['initial_capital'],
            final_equity=results['final_equity'],
            total_return=results['total_return'],
            buy_hold_return=results['buy_hold_return'],
            total_trades=results['total_trades'],
            wins=results['wins'],
            losses=results['losses'],
            win_rate=results['win_rate'],
            profit_factor=results['profit_factor'],
            sharpe_ratio=results['sharpe_ratio'],
            max_drawdown=results['max_drawdown'],
            avg_win=results['avg_win'],
            avg_loss=results['avg_loss'],
            start_date=results['start_date'],
            end_date=results['end_date']
        )
    
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist", response_model=List[WatchlistItem])
async def get_watchlist():
    """Get watchlist symbols."""
    session = db.get_session()
    
    try:
        items = session.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
        
        return [
            WatchlistItem(
                symbol=item.symbol,
                added_at=item.added_at,
                notes=item.notes
            )
            for item in items
        ]
    finally:
        session.close()


@router.post("/watchlist", response_model=SuccessResponse)
async def add_to_watchlist(request: WatchlistAddRequest):
    """Add symbol to watchlist."""
    session = db.get_session()
    
    try:
        # Check if already exists
        existing = session.query(Watchlist).filter_by(symbol=request.symbol).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"{request.symbol} already in watchlist")
        
        # Add to database
        item = Watchlist(
            symbol=request.symbol,
            notes=request.notes
        )
        session.add(item)
        session.commit()
        
        # Add to scanner
        if request.symbol not in scanner.symbols:
            scanner.symbols.append(request.symbol)
        
        return SuccessResponse(
            message=f"Added {request.symbol} to watchlist",
            data={"symbol": request.symbol}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/watchlist/{symbol}", response_model=SuccessResponse)
async def remove_from_watchlist(symbol: str):
    """Remove symbol from watchlist."""
    session = db.get_session()
    
    try:
        item = session.query(Watchlist).filter_by(symbol=symbol).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
        
        session.delete(item)
        session.commit()
        
        # Remove from scanner
        if symbol in scanner.symbols:
            scanner.symbols.remove(symbol)
        
        return SuccessResponse(
            message=f"Removed {symbol} from watchlist",
            data={"symbol": symbol}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error removing from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(limit: int = Query(50, ge=1, le=100)):
    """Get alert history."""
    session = db.get_session()
    
    try:
        alerts = session.query(Alert).order_by(Alert.sent_at.desc()).limit(limit).all()
        
        return [
            AlertResponse(
                id=alert.id,
                type=alert.type,
                channel=alert.channel,
                message=alert.message,
                sent_at=alert.sent_at,
                success=alert.success,
                error=alert.error
            )
            for alert in alerts
        ]
    finally:
        session.close()


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics."""
    session = db.get_session()
    
    try:
        active_squeezes = session.query(Squeeze).filter_by(status='active').count()
        watchlist_size = session.query(Watchlist).count()
        total_alerts = session.query(Alert).count()
        total_backtests = session.query(Backtest).count()
        
        # Get last scan time (from most recent squeeze update)
        last_squeeze = session.query(Squeeze).order_by(Squeeze.updated_at.desc()).first()
        last_scan = last_squeeze.updated_at if last_squeeze else None
        
        return StatsResponse(
            active_squeezes=active_squeezes,
            watchlist_size=watchlist_size,
            total_alerts_sent=total_alerts,
            total_backtests_run=total_backtests,
            scanner_status="active",
            last_scan=last_scan
        )
    finally:
        session.close()


@router.post("/scan", response_model=SuccessResponse)
async def trigger_scan(request: Optional[ScanRequest] = None):
    """Trigger immediate market scan."""
    try:
        symbols = request.symbols if request else None
        results = scanner.scan_market(symbols)
        
        return SuccessResponse(
            message=f"Scan complete: {len(results)} squeezes found",
            data={"squeezes_found": len(results)}
        )
    except Exception as e:
        logger.error(f"Error triggering scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
