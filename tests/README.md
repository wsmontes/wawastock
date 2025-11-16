# Tests - WawaStock Backtesting Framework

## Overview

Test suite using pytest for the WawaStock backtesting framework.

## Installation

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Or individually
pip install pytest pytest-cov pytest-mock
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_local_data_store.py -v

# Run specific test
pytest tests/test_local_data_store.py::TestLocalDataStoreV2::test_init -v

# Run only unit tests (fast)
pytest tests/ -m unit

# Skip slow/network tests
pytest tests/ -m "not slow and not network"
```

## Test Results Summary

### ✅ All Tests Passing! (26/26 = 100%)

**LocalDataStore V2 Tests (7/7):**
- ✅ `test_init` - Store initialization
- ✅ `test_get_file_path_high_frequency` - Path generation for 1m data
- ✅ `test_get_file_path_low_frequency` - Path generation for 1d data  
- ✅ `test_save_and_get_data` - Save and retrieve data
- ✅ `test_has_data` - Data existence check
- ✅ `test_merge_duplicate_data` - Duplicate handling
- ✅ `test_catalog_update` - Catalog metadata tracking

**BacktestEngine Tests (10/10):**
- ✅ `test_initialization` - Engine initialization
- ✅ `test_custom_initial_cash` - Custom cash settings
- ✅ `test_create_cerebro` - Cerebro instance creation
- ✅ `test_run_backtest_insufficient_data` - Data validation
- ✅ `test_run_backtest_valid_data` - Successful backtest
- ✅ `test_backtest_returns_metrics` - Metrics validation
- ✅ `test_empty_dataframe` - Empty data handling
- ✅ `test_dataframe_with_nan_values` - NaN handling
- ✅ `test_multiple_strategies_same_data` - Multiple strategies
- ✅ `test_strategy_with_custom_params` - Custom parameters

**Strategy Tests (6/6):**
- ✅ `test_strategy_initialization` - RSI strategy init
- ✅ `test_strategy_params` - Custom parameters
- ✅ `test_strategy_on_sample_data` - RSI on sample data
- ✅ `test_strategy_initialization` - SMA strategy init
- ✅ `test_strategy_on_sample_data` - SMA on sample data
- ✅ `test_multiple_strategies` - Integration test

**Data Source Tests (3/3 + 3 skipped):**
- ✅ `test_initialization` - Yahoo data source init
- ✅ `test_invalid_symbol` - Invalid symbol handling
- ✅ `test_invalid_date_range` - Invalid date range handling

### ⏭️ Skipped Tests (3/29)

Network-dependent tests (marked with `@pytest.mark.skip`):
- ⏭️ `test_fetch_ohlcv_real_data` - Real data fetch
- ⏭️ `test_fetch_multiple_symbols` - Multiple symbols
- ⏭️ `test_different_timeframes` - Different timeframes

### 📊 Code Coverage

**Overall Coverage: 32%**

Core components coverage:
- **BacktestEngine**: 94% ✅
- **LocalDataStoreV2**: 80% ✅
- **RSIStrategy**: 96% ✅
- **SampleSMAStrategy**: 96% ✅
- **BaseStrategy**: 89% ✅
- YahooDataSource: 50% ⚠️
- DataEngine: 13% (not yet tested)
- Other data sources: 19-40% (not yet tested)

**High-priority components are well-tested!**

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Fixtures and configuration
├── pytest.ini                     # Pytest settings (in root)
├── requirements-test.txt          # Test dependencies
├── test_backtest_engine.py        # BacktestEngine tests
├── test_data_sources.py           # Data source tests
├── test_local_data_store.py       # LocalDataStore tests ✅
└── test_strategies.py             # Strategy tests
```

## Test Categories

Tests are marked with categories:

- `unit` - Fast unit tests, no external dependencies
- `integration` - Integration tests requiring setup
- `slow` - Tests that take longer to run
- `network` - Tests requiring network connection

## Coverage

To generate coverage report:

```bash
pytest tests/ --cov=engines --cov=strategies --cov-report=html
open htmlcov/index.html  # macOS
```

**Current Coverage: 32% overall**
- Core components (BacktestEngine, LocalDataStoreV2, Strategies): **80-96%** ✅
- Secondary components need more tests

## Next Steps

### Completed ✅

1. ✅ **All core tests passing** - 26/26 tests (100%)
2. ✅ **BacktestEngine fully tested** - 94% coverage
3. ✅ **LocalDataStoreV2 tested** - 80% coverage
4. ✅ **Strategies tested** - 96% coverage
5. ✅ **Error handling validated**

### Future Improvements:

- Add DataEngine tests (currently 13% coverage)
- Add tests for other data sources (Alpaca, Binance, CCXT)
- Add Recipe integration tests
- Add performance benchmarks
- Enable network tests in CI/CD with API keys

## Writing New Tests

Example test:

```python
import pytest
from engines.local_data_store_v2 import LocalDataStoreV2

def test_my_feature(temp_dir, sample_ohlcv_data):
    """Test description."""
    store = LocalDataStoreV2(
        duckdb_path=f"{temp_dir}/test.duckdb",
        base_dir=f"{temp_dir}/parquet"
    )
    
    # Test code here
    assert store is not None
```

## Current Status

**Test Health: � 100% Pass Rate (26/26)**

- ✅ Core functionality fully tested and working
- ✅ All critical paths covered
- ✅ Error handling validated
- � Secondary components need more coverage
- 📈 Strong foundation for continuous testing

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure tests pass locally
3. Update this README with new test status
4. Aim for >80% code coverage
