"""
ML Feature Engineering Engine
Uses professional TA library for feature generation.
"""

import pandas as pd
import numpy as np
from typing import List
import ta
import warnings
warnings.filterwarnings('ignore')


class MLFeaturesEngine:
    """
    Extract comprehensive feature set for ML crash prediction.
    Uses 'ta' library - professional technical analysis indicators.
    """
    
    def __init__(self):
        self.feature_names = []
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract 80+ features using TA library.
        
        Args:
            df: DataFrame with columns [open, high, low, close, volume]
            
        Returns:
            DataFrame with technical indicators as features
        """
        # Ensure numeric types
        df_clean = df.copy()
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # Fill any NaN with forward fill then backward fill
        df_clean = df_clean.fillna(method='ffill').fillna(method='bfill')
        
        print(f"   Generating features from {len(df_clean)} bars...")
        
        # =====================================================================
        # USE TA LIBRARY - ALL INDICATORS AT ONCE
        # =====================================================================
        
        # Add ALL indicators from ta library
        df_with_ta = ta.add_all_ta_features(
            df_clean,
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            fillna=True
        )
        
        # Extract only the feature columns (exclude OHLCV)
        feature_cols = [col for col in df_with_ta.columns 
                       if col not in ['open', 'high', 'low', 'close', 'volume']]
        
        features = df_with_ta[feature_cols].copy()
        
        # =====================================================================
        # ADD CUSTOM MOMENTUM FEATURES
        # =====================================================================
        
        # Multi-period returns
        for period in [1, 3, 7, 14, 30, 60, 90, 180]:
            features[f'return_{period}d'] = df_clean['close'].pct_change(period)
            features[f'log_return_{period}d'] = np.log(df_clean['close'] / df_clean['close'].shift(period))
        
        # Return acceleration (2nd derivative)
        features['return_accel_7d'] = features['return_7d'].diff(7)
        features['return_accel_30d'] = features['return_30d'].diff(30)
        
        # Momentum ratios
        features['momentum_ratio_7_30'] = features['return_7d'] / (features['return_30d'].abs() + 1e-8)
        features['momentum_ratio_30_90'] = features['return_30d'] / (features['return_90d'].abs() + 1e-8)
        
        # =====================================================================
        # ADD CUSTOM MARKET STRUCTURE FEATURES
        # =====================================================================
        
        # SMA slopes (rate of change of moving averages)
        sma_20 = df_clean['close'].rolling(20).mean()
        sma_50 = df_clean['close'].rolling(50).mean()
        sma_200 = df_clean['close'].rolling(200).mean()
        
        features['sma_20_slope'] = sma_20.pct_change(5)
        features['sma_50_slope'] = sma_50.pct_change(10)
        features['sma_200_slope'] = sma_200.pct_change(20)
        
        # Distance from SMAs
        features['dist_sma_20'] = (df_clean['close'] - sma_20) / sma_20
        features['dist_sma_50'] = (df_clean['close'] - sma_50) / sma_50
        features['dist_sma_200'] = (df_clean['close'] - sma_200) / sma_200
        
        # SMA alignment (bullish when 20>50>200)
        features['sma_alignment'] = (sma_20 > sma_50).astype(int) + (sma_50 > sma_200).astype(int)
        
        # Price position in 52-week range
        roll_high_252 = df_clean['close'].rolling(252).max()
        roll_low_252 = df_clean['close'].rolling(252).min()
        features['price_position_52w'] = (df_clean['close'] - roll_low_252) / (roll_high_252 - roll_low_252 + 1e-8)
        
        # =====================================================================
        # ADD CUSTOM VOLUME FEATURES
        # =====================================================================
        
        # Volume trends
        volume_sma_20 = df_clean['volume'].rolling(20).mean()
        volume_sma_50 = df_clean['volume'].rolling(50).mean()
        
        features['volume_ratio_20'] = df_clean['volume'] / (volume_sma_20 + 1e-8)
        features['volume_ratio_50'] = df_clean['volume'] / (volume_sma_50 + 1e-8)
        features['volume_trend_20d'] = df_clean['volume'].pct_change(20)
        
        # Volume on up vs down days
        up_mask = df_clean['close'] > df_clean['close'].shift(1)
        volume_on_up = df_clean['volume'].where(up_mask, 0).rolling(20).mean()
        volume_on_down = df_clean['volume'].where(~up_mask, 0).rolling(20).mean()
        features['volume_up_down_ratio'] = volume_on_up / (volume_on_down + 1e-8)
        
        # =====================================================================
        # ADD CUSTOM VOLATILITY FEATURES
        # =====================================================================
        
        # Volatility across periods
        features['volatility_7d'] = df_clean['close'].pct_change().rolling(7).std()
        features['volatility_30d'] = df_clean['close'].pct_change().rolling(30).std()
        features['volatility_90d'] = df_clean['close'].pct_change().rolling(90).std()
        
        # Volatility ratios (acceleration/deceleration)
        features['volatility_ratio_7_30'] = features['volatility_7d'] / (features['volatility_30d'] + 1e-8)
        features['volatility_ratio_30_90'] = features['volatility_30d'] / (features['volatility_90d'] + 1e-8)
        
        # High-Low range as % of close
        features['hl_range_pct'] = (df_clean['high'] - df_clean['low']) / df_clean['close']
        features['hl_range_avg_20d'] = features['hl_range_pct'].rolling(20).mean()
        
        # =====================================================================
        # ADD EXHAUSTION SIGNALS
        # =====================================================================
        
        # Consecutive up/down days
        up_days = (df_clean['close'] > df_clean['close'].shift(1)).astype(int)
        features['consec_up'] = up_days.groupby((up_days != up_days.shift()).cumsum()).cumsum()
        
        down_days = (df_clean['close'] < df_clean['close'].shift(1)).astype(int)
        features['consec_down'] = down_days.groupby((down_days != down_days.shift()).cumsum()).cumsum()
        
        # Rally ratio (% of up days in last 20 days)
        features['rally_ratio_20d'] = up_days.rolling(20).mean()
        
        # Price vs volume divergence (price up but volume down = exhaustion)
        price_trend_20 = df_clean['close'].pct_change(20)
        volume_trend_20 = df_clean['volume'].pct_change(20)
        features['price_volume_divergence'] = np.where(
            (price_trend_20 > 0) & (volume_trend_20 < 0), 1,  # Bearish divergence
            np.where((price_trend_20 < 0) & (volume_trend_20 > 0), -1, 0)  # Bullish divergence
        )
        
        # =====================================================================
        # ADD CYCLE POSITION FEATURES
        # =====================================================================
        
        # Distance from cycle lows (assume 2-year lookback for crypto)
        roll_low_730 = df_clean['close'].rolling(730, min_periods=90).min()
        features['dist_from_2y_low'] = (df_clean['close'] - roll_low_730) / (roll_low_730 + 1e-8)
        
        # Z-score of returns (how extreme are current returns)
        features['return_zscore_90d'] = (
            (features['return_30d'] - features['return_30d'].rolling(90).mean()) / 
            (features['return_30d'].rolling(90).std() + 1e-8)
        )
        
        # Days since significant pullback (>-10%)
        pullback_mask = df_clean['close'].pct_change(30) < -0.10
        features['days_since_pullback'] = (~pullback_mask).cumsum() - (~pullback_mask).cumsum().where(pullback_mask).ffill().fillna(0)
        
        # =====================================================================
        # CLEAN UP
        # =====================================================================
        
        # Replace inf with NaN
        features = features.replace([np.inf, -np.inf], np.nan)
        
        # Forward fill then backward fill NaN
        features = features.fillna(method='ffill').fillna(method='bfill')
        
        # If still NaN, fill with 0
        features = features.fillna(0)
        
        # Store feature names
        self.feature_names = features.columns.tolist()
        
        print(f"   ✅ Generated {len(self.feature_names)} features")
        print(f"   ✅ {len(features)} valid samples (no NaN)")
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Return list of feature names."""
        return self.feature_names
    
    def get_feature_count(self) -> int:
        """Return number of features."""
        return len(self.feature_names)
