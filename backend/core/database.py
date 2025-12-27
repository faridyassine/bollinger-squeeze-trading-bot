"""Database models and connection management."""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pathlib import Path

Base = declarative_base()


class Squeeze(Base):
    """Model for detected squeeze patterns."""
    
    __tablename__ = 'squeezes'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    price = Column(Float, nullable=False)
    squeeze_strength = Column(Float, nullable=False)
    days_in_squeeze = Column(Integer, default=0)
    direction = Column(String(10))  # BULLISH, BEARISH, NEUTRAL
    confidence = Column(Float)
    bb_width = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    volume = Column(Float)
    status = Column(String(20), default='active')  # active, breakout, expired
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    alerts = relationship("Alert", back_populates="squeeze")


class Alert(Base):
    """Model for sent alerts."""
    
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    squeeze_id = Column(Integer, ForeignKey('squeezes.id'))
    type = Column(String(20), nullable=False)  # squeeze_detected, breakout, exit
    channel = Column(String(20), nullable=False)  # telegram, discord, email
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error = Column(Text)
    
    squeeze = relationship("Squeeze", back_populates="alerts")


class Backtest(Base):
    """Model for backtest results."""
    
    __tablename__ = 'backtests'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    strategy = Column(String(50), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    total_trades = Column(Integer)
    parameters = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trades = relationship("Trade", back_populates="backtest")


class Trade(Base):
    """Model for individual trades."""
    
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey('backtests.id'), nullable=True)
    symbol = Column(String(10), nullable=False)
    entry_date = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_date = Column(DateTime)
    exit_price = Column(Float)
    quantity = Column(Float, nullable=False)
    side = Column(String(10), nullable=False)  # LONG, SHORT
    pnl = Column(Float)
    pnl_percent = Column(Float)
    status = Column(String(20), default='open')  # open, closed
    entry_reason = Column(Text)
    exit_reason = Column(Text)
    
    backtest = relationship("Backtest", back_populates="trades")


class Watchlist(Base):
    """Model for watchlist symbols."""
    
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)


class Database:
    """Database connection manager."""
    
    def __init__(self, db_type: str = "sqlite", db_path: str = "data/trading.db"):
        """Initialize database connection.
        
        Args:
            db_type: Database type (sqlite or postgresql)
            db_path: Path to SQLite database or PostgreSQL connection string
        """
        if db_type == "sqlite":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            connection_string = f"sqlite:///{db_path}"
        else:
            connection_string = db_path
        
        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()
