"""Test configuration for pytest."""
import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100, freq='D')
    
    data = pd.DataFrame({
        'open': np.random.uniform(100, 110, 100),
        'high': np.random.uniform(105, 115, 100),
        'low': np.random.uniform(95, 105, 100),
        'close': np.random.uniform(100, 110, 100),
        'volume': np.random.uniform(1000000, 5000000, 100)
    }, index=dates)
    
    return data
