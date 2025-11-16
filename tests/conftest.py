"""
Pytest configuration and fixtures.
"""

import pytest
import sys
from pathlib import Path
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(100)]
    
    # Generate realistic price movement with random walk
    np.random.seed(42)  # Reproducible
    base_price = 100.0
    price_changes = np.random.randn(100) * 2  # Random walk
    prices = base_price + np.cumsum(price_changes)
    prices = np.maximum(prices, 50.0)  # Keep positive
    
    data = {
        'timestamp': dates,
        'open': [],
        'high': [],
        'low': [],
        'close': prices,
        'volume': [np.random.randint(1000000, 5000000) for _ in range(100)]
    }
    
    # Generate realistic OHLC
    for close_price in prices:
        daily_range = close_price * 0.02  # 2% daily range
        high = close_price + np.random.uniform(0, daily_range)
        low = close_price - np.random.uniform(0, daily_range)
        open_price = np.random.uniform(low, high)
        
        data['open'].append(open_price)
        data['high'].append(high)
        data['low'].append(low)
    
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    return df


@pytest.fixture
def mock_data_engine(temp_dir):
    """Create a DataEngine with temporary storage."""
    from engines.data_engine import DataEngine
    
    db_path = str(Path(temp_dir) / "test_trader.duckdb")
    engine = DataEngine(db_path=db_path, use_cache=True)
    
    yield engine
    
    # Cleanup
    if hasattr(engine, 'close'):
        engine.close()
