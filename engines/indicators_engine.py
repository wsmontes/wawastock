"""
Indicators Engine - Technical indicators calculation using pandas-ta.

Separated from data collection logic - operates at the database/storage level.
"""

import pandas as pd
import pandas_ta as ta
from loguru import logger


class IndicatorsEngine:
    """
    Calculates and adds technical indicators to OHLCV data.
    
    This engine is independent of data sources and operates on DataFrames
    that are about to be saved to the database.
    """
    
    def __init__(self, indicator_set: str = 'standard'):
        """
        Initialize the IndicatorsEngine.
        
        Args:
            indicator_set: Which set of indicators to calculate
                         'standard' - Common indicators (SMA, EMA, RSI, MACD, BB, ATR)
                         'minimal' - Only basic indicators (SMA, RSI)
                         'full' - All available indicators
        """
        self.indicator_set = indicator_set
        logger.info(f"IndicatorsEngine initialized with '{indicator_set}' indicator set")
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to a DataFrame with OHLCV data.
        
        Only calculates if indicators are not already present.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
        
        Returns:
            DataFrame with original data plus indicator columns
        """
        if df is None or df.empty:
            logger.warning("Empty DataFrame - skipping indicators")
            return df
        
        # Validate required columns
        required = {'open', 'high', 'low', 'close', 'volume'}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            logger.warning(f"Missing columns {missing} - skipping indicators")
            return df
        
        # Check if indicators already exist - if so, skip calculation
        indicator_patterns = ['SMA_', 'EMA_', 'RSI_', 'MACD', 'BBL_', 'BBM_', 'BBU_', 
                             'ATR_', 'OBV', 'VWAP', 'STOCH', 'ADX', 'BBB_', 'BBP_']
        existing_indicators = [col for col in df.columns 
                              if any(pattern in col for pattern in indicator_patterns)]
        
        if existing_indicators:
            logger.debug(f"Indicators already present ({len(existing_indicators)} columns) - skipping calculation")
            return df
        
        # Make a copy to avoid modifying original
        df_result = df.copy()
        
        try:
            if self.indicator_set == 'minimal':
                df_result = self._add_minimal_indicators(df_result)
            elif self.indicator_set == 'full':
                df_result = self._add_full_indicators(df_result)
            else:  # standard
                df_result = self._add_standard_indicators(df_result)
            
            added = len(df_result.columns) - len(df.columns)
            logger.info(f"✓ Added {added} indicator columns")
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df  # Return original on error
        
        return df_result
    
    def _add_minimal_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add minimal set of indicators."""
        # Moving averages
        df['SMA_20'] = ta.sma(df['close'], length=20)
        df['SMA_50'] = ta.sma(df['close'], length=50)
        
        # RSI
        df['RSI_14'] = ta.rsi(df['close'], length=14)
        
        return df
    
    def _add_standard_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add standard set of indicators (most commonly used)."""
        # Trend indicators
        df['SMA_20'] = ta.sma(df['close'], length=20)
        df['SMA_50'] = ta.sma(df['close'], length=50)
        df['SMA_200'] = ta.sma(df['close'], length=200)
        df['EMA_12'] = ta.ema(df['close'], length=12)
        df['EMA_26'] = ta.ema(df['close'], length=26)
        
        # Momentum indicators
        df['RSI_14'] = ta.rsi(df['close'], length=14)
        
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        
        # Volatility indicators
        bbands = ta.bbands(df['close'], length=20)
        if bbands is not None:
            df = pd.concat([df, bbands], axis=1)
        
        df['ATR_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Volume indicators
        df['OBV'] = ta.obv(df['close'], df['volume'])
        
        return df
    
    def _add_full_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add full set of indicators."""
        # Start with standard
        df = self._add_standard_indicators(df)
        
        # Additional trend indicators
        df['EMA_9'] = ta.ema(df['close'], length=9)
        df['EMA_21'] = ta.ema(df['close'], length=21)
        df['EMA_55'] = ta.ema(df['close'], length=55)
        
        # Additional momentum
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
        if stoch is not None:
            df = pd.concat([df, stoch], axis=1)
        
        # ADX for trend strength
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None:
            df = pd.concat([df, adx], axis=1)
        
        # VWAP
        vwap = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        if vwap is not None:
            df['VWAP'] = vwap
        
        return df
