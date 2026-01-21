"""
ML Crash Prediction Engine
Uses XGBoost to predict BTC crashes with walk-forward validation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import joblib
from pathlib import Path

from engines.ml_features_engine import MLFeaturesEngine


class CrashPredictorEngine:
    """
    XGBoost-based crash prediction with walk-forward validation.
    
    Predicts probability of >-30% crash in next 30 days.
    """
    
    def __init__(
        self,
        crash_threshold: float = -0.30,
        lookahead_days: int = 30,
        min_train_days: int = 730,  # 2 years minimum
        model_params: Optional[Dict] = None
    ):
        """
        Initialize crash predictor.
        
        Args:
            crash_threshold: Define crash as this % drop (e.g., -0.30 = -30%)
            lookahead_days: Predict crash in next N days
            min_train_days: Minimum days needed for training
            model_params: XGBoost hyperparameters
        """
        self.crash_threshold = crash_threshold
        self.lookahead_days = lookahead_days
        self.min_train_days = min_train_days
        
        # Default XGBoost params (tuned for crash prediction)
        self.model_params = model_params or {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'scale_pos_weight': 10,  # Handle class imbalance (crashes are rare)
            'random_state': 42
        }
        
        self.feature_engine = MLFeaturesEngine()
        self.model = None
        self.feature_names = []
        self.feature_importance = None
    
    def create_labels(self, df: pd.DataFrame) -> pd.Series:
        """
        Create crash labels for training.
        
        Label = 1 if crash (drop > threshold) happens in next lookahead_days
        Label = 0 otherwise
        
        Args:
            df: DataFrame with 'close' column
            
        Returns:
            Series of binary labels
        """
        # Calculate forward returns
        forward_return = df['close'].pct_change(self.lookahead_days).shift(-self.lookahead_days)
        
        # Label crashes
        labels = (forward_return < self.crash_threshold).astype(int)
        
        # Remove last lookahead_days (no future data)
        labels.iloc[-self.lookahead_days:] = np.nan
        
        return labels
    
    def prepare_dataset(
        self, 
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare full dataset: features + labels.
        
        Args:
            df: Raw OHLCV DataFrame
            
        Returns:
            (features_df, labels_series)
        """
        print("📊 Extracting features...")
        features = self.feature_engine.extract_features(df)
        
        print("🏷️  Creating crash labels...")
        labels = self.create_labels(df)
        
        # Remove NaN rows
        valid_idx = ~(features.isna().any(axis=1) | labels.isna())
        features_clean = features[valid_idx]
        labels_clean = labels[valid_idx]
        
        # Store feature names
        self.feature_names = features_clean.columns.tolist()
        
        print(f"✅ Dataset ready: {len(features_clean)} samples, {len(self.feature_names)} features")
        print(f"   Crashes: {labels_clean.sum()} ({labels_clean.mean()*100:.1f}%)")
        print(f"   Normal: {(1-labels_clean).sum()} ({(1-labels_clean.mean())*100:.1f}%)")
        
        return features_clean, labels_clean
    
    def train_walk_forward(
        self,
        df: pd.DataFrame,
        n_splits: int = 5,
        save_path: Optional[str] = None
    ) -> Dict:
        """
        Train model with walk-forward validation.
        
        Args:
            df: Raw OHLCV DataFrame
            n_splits: Number of walk-forward splits
            save_path: Path to save trained model
            
        Returns:
            Dictionary with validation metrics
        """
        print("\n" + "="*80)
        print("🎯 TRAINING CRASH PREDICTOR (Walk-Forward Validation)")
        print("="*80 + "\n")
        
        # Prepare dataset
        X, y = self.prepare_dataset(df)
        
        # Walk-forward cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        results = {
            'fold_metrics': [],
            'feature_importance': None,
            'confusion_matrices': []
        }
        
        print(f"\n🔄 Walk-Forward Validation ({n_splits} folds):")
        print("-" * 80)
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
            print(f"\nFold {fold}/{n_splits}:")
            print(f"  Train: {len(train_idx)} samples ({X.index[train_idx[0]]} to {X.index[train_idx[-1]]})")
            print(f"  Test:  {len(test_idx)} samples ({X.index[test_idx[0]]} to {X.index[test_idx[-1]]})")
            
            # Split data
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # Train model
            model = xgb.XGBClassifier(**self.model_params)
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
            
            # Predict
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            
            # Metrics
            try:
                auc = roc_auc_score(y_test, y_prob)
            except:
                auc = 0.0
            
            accuracy = (y_pred == y_test).mean()
            
            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            print(f"  Accuracy:  {accuracy:.3f}")
            print(f"  AUC:       {auc:.3f}")
            print(f"  Precision: {precision:.3f}")
            print(f"  Recall:    {recall:.3f}")
            print(f"  F1:        {f1:.3f}")
            print(f"  Confusion: TN={tn}, FP={fp}, FN={fn}, TP={tp}")
            
            results['fold_metrics'].append({
                'fold': fold,
                'accuracy': accuracy,
                'auc': auc,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'confusion_matrix': cm
            })
            results['confusion_matrices'].append(cm)
        
        # Train final model on all data
        print("\n📦 Training final model on full dataset...")
        self.model = xgb.XGBClassifier(**self.model_params)
        self.model.fit(X, y, verbose=False)
        
        # Feature importance
        self.feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        results['feature_importance'] = self.feature_importance
        
        # Average metrics
        avg_metrics = {
            'accuracy': np.mean([m['accuracy'] for m in results['fold_metrics']]),
            'auc': np.mean([m['auc'] for m in results['fold_metrics']]),
            'precision': np.mean([m['precision'] for m in results['fold_metrics']]),
            'recall': np.mean([m['recall'] for m in results['fold_metrics']]),
            'f1': np.mean([m['f1'] for m in results['fold_metrics']])
        }
        
        print("\n" + "="*80)
        print("📊 AVERAGE METRICS (Walk-Forward):")
        print("="*80)
        print(f"  Accuracy:  {avg_metrics['accuracy']:.3f}")
        print(f"  AUC:       {avg_metrics['auc']:.3f}")
        print(f"  Precision: {avg_metrics['precision']:.3f}")
        print(f"  Recall:    {avg_metrics['recall']:.3f}")
        print(f"  F1:        {avg_metrics['f1']:.3f}")
        
        print("\n🔝 TOP 20 MOST IMPORTANT FEATURES:")
        print("-" * 80)
        for idx, row in self.feature_importance.head(20).iterrows():
            print(f"  {row['feature']:30s} {row['importance']:.4f}")
        
        # Save model
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(self.model, save_path)
            print(f"\n💾 Model saved to: {save_path}")
        
        results['average_metrics'] = avg_metrics
        
        return results
    
    def predict_crash_probability(
        self,
        df: pd.DataFrame,
        start_idx: Optional[int] = None,
        end_idx: Optional[int] = None
    ) -> pd.Series:
        """
        Predict crash probability for each day.
        
        Args:
            df: Raw OHLCV DataFrame
            start_idx: Start index for prediction (default: all)
            end_idx: End index for prediction (default: all)
            
        Returns:
            Series with crash probabilities [0-1]
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train_walk_forward() first.")
        
        # Extract features
        features = self.feature_engine.extract_features(df)
        
        # Handle slice
        if start_idx is not None or end_idx is not None:
            features = features.iloc[start_idx:end_idx]
        
        # Fill NaN with 0 (for prediction only, not training)
        features_filled = features.fillna(0)
        
        # Predict probabilities
        crash_probs = self.model.predict_proba(features_filled)[:, 1]
        
        # Return as Series with same index
        return pd.Series(crash_probs, index=features.index, name='crash_prob')
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """Get top N most important features."""
        if self.feature_importance is None:
            raise ValueError("Model not trained yet.")
        
        return self.feature_importance.head(top_n)
    
    def save_model(self, path: str):
        """Save trained model to disk."""
        if self.model is None:
            raise ValueError("No model to save.")
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance,
            'params': {
                'crash_threshold': self.crash_threshold,
                'lookahead_days': self.lookahead_days,
                'min_train_days': self.min_train_days
            }
        }, path)
        print(f"💾 Model saved to: {path}")
    
    def load_model(self, path: str):
        """Load trained model from disk."""
        data = joblib.load(path)
        self.model = data['model']
        self.feature_names = data['feature_names']
        self.feature_importance = data['feature_importance']
        
        # Restore params
        params = data['params']
        self.crash_threshold = params['crash_threshold']
        self.lookahead_days = params['lookahead_days']
        self.min_train_days = params['min_train_days']
        
        print(f"✅ Model loaded from: {path}")
