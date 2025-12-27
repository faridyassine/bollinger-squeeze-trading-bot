"""Continuous monitoring of active squeezes."""
from typing import Dict, List
from datetime import datetime
from backend.core.database import Database, Squeeze
from backend.core.config import config
from backend.core.logging_config import get_logger
from backend.scanner.market_scanner import MarketScanner

logger = get_logger(__name__)


class SqueezeMonitor:
    """Monitors active squeezes and tracks their lifecycle."""
    
    def __init__(self, db: Database = None):
        """Initialize squeeze monitor.
        
        Args:
            db: Database instance
        """
        self.db = db or Database(
            db_type=config.database.get('type', 'sqlite'),
            db_path=config.database.get('path', 'data/trading.db')
        )
        self.scanner = MarketScanner()
    
    def update_squeeze(self, squeeze_data: Dict) -> Squeeze:
        """Update or create squeeze record in database.
        
        Args:
            squeeze_data: Squeeze analysis result
            
        Returns:
            Squeeze database record
        """
        session = self.db.get_session()
        
        try:
            # Check if squeeze exists
            existing = session.query(Squeeze).filter_by(
                symbol=squeeze_data['symbol'],
                status='active'
            ).first()
            
            if existing:
                # Update existing squeeze
                existing.price = squeeze_data['price']
                existing.squeeze_strength = squeeze_data['squeeze_strength']
                existing.days_in_squeeze = squeeze_data['days_in_squeeze']
                existing.direction = squeeze_data['direction']
                existing.confidence = squeeze_data['confidence']
                existing.bb_width = squeeze_data['bb_width']
                existing.rsi = squeeze_data['rsi']
                existing.macd = squeeze_data['macd']
                existing.volume = squeeze_data.get('avg_volume', 0)
                existing.updated_at = datetime.utcnow()
                
                logger.debug(f"Updated squeeze for {squeeze_data['symbol']}")
                squeeze = existing
            else:
                # Create new squeeze
                squeeze = Squeeze(
                    symbol=squeeze_data['symbol'],
                    price=squeeze_data['price'],
                    squeeze_strength=squeeze_data['squeeze_strength'],
                    days_in_squeeze=squeeze_data['days_in_squeeze'],
                    direction=squeeze_data['direction'],
                    confidence=squeeze_data['confidence'],
                    bb_width=squeeze_data['bb_width'],
                    rsi=squeeze_data['rsi'],
                    macd=squeeze_data['macd'],
                    volume=squeeze_data.get('avg_volume', 0),
                    status='active'
                )
                session.add(squeeze)
                logger.info(f"New squeeze detected for {squeeze_data['symbol']}")
            
            session.commit()
            return squeeze
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating squeeze: {e}")
            raise
        finally:
            session.close()
    
    def mark_squeeze_expired(self, symbol: str):
        """Mark squeeze as expired.
        
        Args:
            symbol: Stock symbol
        """
        session = self.db.get_session()
        
        try:
            squeeze = session.query(Squeeze).filter_by(
                symbol=symbol,
                status='active'
            ).first()
            
            if squeeze:
                squeeze.status = 'expired'
                squeeze.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"Marked squeeze as expired: {symbol}")
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking squeeze expired: {e}")
        finally:
            session.close()
    
    def mark_squeeze_breakout(self, symbol: str):
        """Mark squeeze as broken out.
        
        Args:
            symbol: Stock symbol
        """
        session = self.db.get_session()
        
        try:
            squeeze = session.query(Squeeze).filter_by(
                symbol=symbol,
                status='active'
            ).first()
            
            if squeeze:
                squeeze.status = 'breakout'
                squeeze.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"Marked squeeze as breakout: {symbol}")
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking squeeze breakout: {e}")
        finally:
            session.close()
    
    def get_active_squeezes(self) -> List[Squeeze]:
        """Get all active squeezes from database.
        
        Returns:
            List of active squeeze records
        """
        session = self.db.get_session()
        
        try:
            squeezes = session.query(Squeeze).filter_by(status='active').order_by(
                Squeeze.squeeze_strength.desc()
            ).all()
            return squeezes
        finally:
            session.close()
    
    def monitor_and_update(self, symbols: List[str] = None):
        """Monitor symbols and update squeeze status.
        
        Args:
            symbols: List of symbols to monitor (default: from config)
        """
        logger.info("Starting squeeze monitoring cycle")
        
        # Scan market
        results = self.scanner.scan_market(symbols)
        
        # Get currently active symbols from database
        active_squeezes = self.get_active_squeezes()
        active_symbols = {sq.symbol for sq in active_squeezes}
        
        # Update detected squeezes
        found_symbols = set()
        for result in results:
            self.update_squeeze(result)
            found_symbols.add(result['symbol'])
        
        # Mark missing squeezes as expired
        for symbol in active_symbols - found_symbols:
            self.mark_squeeze_expired(symbol)
        
        logger.info(f"Monitoring complete: {len(results)} active squeezes")
