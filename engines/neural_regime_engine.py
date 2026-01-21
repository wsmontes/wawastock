"""
Neural Regime Engine V2 - Detecção de Regime com Temporal CNN.

Este engine resolve os problemas fundamentais do modelo anterior:
1. Prevê REGIME ao invés de retorno (UP, DOWN, SIDEWAYS, VOL states)
2. Usa Temporal CNN ao invés de MLP (captura padrões temporais)
3. Features robustas: liquidity, macro proxies, mean reversion
4. Loss baseada em Sharpe, não accuracy
5. Walk-forward training para adaptação contínua

Regimes detectados:
- STRONG_UP: Tendência de alta forte
- WEAK_UP: Tendência de alta fraca
- SIDEWAYS: Mercado lateral/consolidação
- WEAK_DOWN: Tendência de baixa fraca
- STRONG_DOWN: Tendência de baixa forte
- VOL_EXPANSION: Volatilidade expandindo
- VOL_CRUSH: Volatilidade contraindo
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import IntEnum
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from engines.base_engine import BaseEngine

# Lazy imports para torch
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None

console = Console()


class MarketRegime(IntEnum):
    """Regimes de mercado detectáveis."""
    STRONG_DOWN = 0
    WEAK_DOWN = 1
    SIDEWAYS = 2
    WEAK_UP = 3
    STRONG_UP = 4


class VolatilityState(IntEnum):
    """Estados de volatilidade."""
    VOL_CRUSH = 0      # Volatilidade contraindo
    VOL_NORMAL = 1     # Volatilidade normal
    VOL_EXPANSION = 2  # Volatilidade expandindo


@dataclass
class RegimeConfig:
    """Configuração do detector de regime neural."""
    # Arquitetura T-CNN
    num_filters: int = 64
    kernel_sizes: List[int] = field(default_factory=lambda: [3, 5, 7, 15])
    dropout: float = 0.3
    
    # Features
    sequence_length: int = 60  # Janela de lookback
    
    # Regime detection
    trend_threshold_strong: float = 0.02  # 2% para regime forte
    trend_threshold_weak: float = 0.005   # 0.5% para regime fraco
    vol_lookback: int = 20
    
    # Treinamento
    learning_rate: float = 0.001
    batch_size: int = 64
    epochs: int = 100
    early_stopping_patience: int = 15
    
    # Walk-forward
    walk_forward_window: int = 252  # ~1 ano de dados para treino
    retrain_frequency: int = 63     # Retreinar a cada ~3 meses
    
    # Loss weights
    sharpe_weight: float = 0.7
    accuracy_weight: float = 0.3
    
    # Regularização
    weight_decay: float = 1e-4
    gradient_clip: float = 1.0
    
    # Device
    device: str = 'auto'


class TemporalCNN(nn.Module):
    """
    Temporal Convolutional Neural Network para detecção de regime.
    
    Usa múltiplos kernels de diferentes tamanhos para capturar
    padrões em diferentes escalas temporais.
    """
    
    def __init__(self, input_size: int, config: RegimeConfig, num_classes: int = 5):
        super().__init__()
        self.config = config
        
        # Múltiplas convoluções com diferentes kernel sizes
        self.convs = nn.ModuleList([
            nn.Sequential(
                nn.Conv1d(input_size, config.num_filters, kernel_size=k, padding=k//2),
                nn.BatchNorm1d(config.num_filters),
                nn.ReLU(),
                nn.Dropout(config.dropout)
            )
            for k in config.kernel_sizes
        ])
        
        # Concatenar outputs de todas as convoluções
        concat_size = config.num_filters * len(config.kernel_sizes)
        
        # Global pooling + fully connected
        self.fc = nn.Sequential(
            nn.Linear(concat_size, concat_size // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(concat_size // 2, concat_size // 4),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(concat_size // 4, num_classes)
        )
        
        # Cabeça separada para volatilidade
        self.vol_head = nn.Sequential(
            nn.Linear(concat_size, 32),
            nn.ReLU(),
            nn.Linear(32, 3)  # VOL_CRUSH, VOL_NORMAL, VOL_EXPANSION
        )
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: Input tensor (batch, seq_len, features)
            
        Returns:
            regime_logits: (batch, num_classes)
            vol_logits: (batch, 3)
        """
        # Transpose para Conv1d: (batch, features, seq_len)
        x = x.transpose(1, 2)
        
        # Aplicar cada convolução
        conv_outputs = []
        for conv in self.convs:
            out = conv(x)
            # Global average pooling
            out = F.adaptive_avg_pool1d(out, 1).squeeze(-1)
            conv_outputs.append(out)
        
        # Concatenar
        x = torch.cat(conv_outputs, dim=1)
        
        # Classificação de regime
        regime_logits = self.fc(x)
        
        # Classificação de volatilidade
        vol_logits = self.vol_head(x)
        
        return regime_logits, vol_logits


class SharpeAwareLoss(nn.Module):
    """
    Loss function que considera Sharpe Ratio além de accuracy.
    
    Penaliza previsões que levariam a trades com retorno ajustado
    ao risco negativo.
    """
    
    def __init__(
        self, 
        sharpe_weight: float = 0.3,  # Reduzido de 0.7
        accuracy_weight: float = 0.7,  # Aumentado de 0.3
        class_weights: torch.Tensor = None
    ):
        super().__init__()
        self.sharpe_weight = sharpe_weight
        self.accuracy_weight = accuracy_weight
        # Usar class weights para balancear
        self.ce_loss = nn.CrossEntropyLoss(weight=class_weights)
    
    def forward(
        self, 
        regime_logits: torch.Tensor, 
        regime_targets: torch.Tensor,
        vol_logits: torch.Tensor,
        vol_targets: torch.Tensor,
        future_returns: torch.Tensor
    ) -> torch.Tensor:
        """
        Calcular loss combinada.
        
        Args:
            regime_logits: Previsões de regime
            regime_targets: Labels de regime
            vol_logits: Previsões de volatilidade
            vol_targets: Labels de volatilidade
            future_returns: Retornos futuros reais (para calcular Sharpe)
        """
        # Cross-entropy para classificação
        ce_regime = self.ce_loss(regime_logits, regime_targets)
        ce_vol = self.ce_loss(vol_logits, vol_targets)
        accuracy_loss = ce_regime + 0.5 * ce_vol
        
        # Sharpe-aware loss: penalizar previsões que levam a trades ruins
        # Converter logits em probabilidades
        regime_probs = F.softmax(regime_logits, dim=1)
        
        # Posição esperada baseada na previsão de regime
        # STRONG_DOWN=-1, WEAK_DOWN=-0.5, SIDEWAYS=0, WEAK_UP=0.5, STRONG_UP=1
        position_weights = torch.tensor([-1.0, -0.5, 0.0, 0.5, 1.0], device=regime_logits.device)
        expected_position = (regime_probs * position_weights).sum(dim=1)
        
        # Retorno esperado da posição
        expected_pnl = expected_position * future_returns
        
        # Sharpe aproximado (média / std)
        mean_pnl = expected_pnl.mean()
        std_pnl = expected_pnl.std() + 1e-8
        sharpe_proxy = mean_pnl / std_pnl
        
        # Loss: queremos maximizar Sharpe, então minimizamos o negativo
        sharpe_loss = -sharpe_proxy
        
        # Combinar losses
        total_loss = (
            self.accuracy_weight * accuracy_loss + 
            self.sharpe_weight * sharpe_loss
        )
        
        return total_loss


class NeuralRegimeEngine(BaseEngine):
    """
    Engine para detecção de regime de mercado usando Temporal CNN.
    
    Features:
    - Detecta regime de mercado (não tenta prever retorno)
    - Temporal CNN para padrões em múltiplas escalas
    - Features robustas: liquidity, macro, mean reversion
    - Loss baseada em Sharpe
    - Walk-forward training
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        """Inicializar engine."""
        super().__init__()
        
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch não está instalado. Execute: pip install torch")
        
        self.config = config or RegimeConfig()
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.training_history = []
        
        # Setup device
        if self.config.device == 'auto':
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
            elif torch.backends.mps.is_available():
                self.device = torch.device('mps')
            else:
                self.device = torch.device('cpu')
        else:
            self.device = torch.device(self.config.device)
        
        self.logger.info(f"NeuralRegimeEngine initialized on {self.device}")
    
    def run(self):
        """Execute não implementado - use train() e predict()."""
        raise NotImplementedError("Use train() and predict() methods")
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extrair features robustas para detecção de regime.
        
        Três categorias principais:
        1. Liquidity / Microstructure
        2. Regime / Macro proxies
        3. Mean reversion strength
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            DataFrame com features
        """
        features = pd.DataFrame(index=df.index)
        
        # Normalizar nomes de colunas (aceitar tanto maiúsculas quanto minúsculas)
        df_norm = df.copy()
        df_norm.columns = df_norm.columns.str.lower()
        
        close = df_norm['close']
        high = df_norm['high']
        low = df_norm['low']
        volume = df_norm['volume']
        
        # =====================================================================
        # 1. LIQUIDITY / MICROSTRUCTURE
        # =====================================================================
        
        # Volume features
        vol_sma_20 = volume.rolling(20).mean()
        vol_sma_50 = volume.rolling(50).mean()
        features['volume_ratio_20'] = volume / (vol_sma_20 + 1e-10)
        features['volume_ratio_50'] = volume / (vol_sma_50 + 1e-10)
        features['volume_trend'] = vol_sma_20 / (vol_sma_50 + 1e-10)
        features['volume_std_20'] = volume.rolling(20).std() / (vol_sma_20 + 1e-10)
        
        # Volatility features
        returns = close.pct_change()
        features['realized_vol_5'] = returns.rolling(5).std() * np.sqrt(252)
        features['realized_vol_20'] = returns.rolling(20).std() * np.sqrt(252)
        features['realized_vol_60'] = returns.rolling(60).std() * np.sqrt(252)
        
        # Volatility compression/expansion
        features['vol_ratio_5_20'] = features['realized_vol_5'] / (features['realized_vol_20'] + 1e-10)
        features['vol_ratio_20_60'] = features['realized_vol_20'] / (features['realized_vol_60'] + 1e-10)
        
        # ATR e ATR slope
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr_14 = tr.rolling(14).mean()
        features['atr_normalized'] = atr_14 / close
        features['atr_slope'] = atr_14.pct_change(5)
        
        # Range compression
        features['hl_ratio'] = (high - low) / close
        features['hl_ratio_sma'] = features['hl_ratio'].rolling(10).mean()
        features['hl_compression'] = features['hl_ratio'] / (features['hl_ratio_sma'] + 1e-10)
        
        # =====================================================================
        # 2. REGIME / MACRO PROXIES
        # =====================================================================
        
        # Trend filters em múltiplas escalas
        for period in [10, 20, 50, 100, 200]:
            sma = close.rolling(period).mean()
            features[f'price_vs_sma_{period}'] = (close - sma) / sma
            features[f'sma_{period}_slope'] = sma.pct_change(5)
        
        # EMA crossovers
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        ema_50 = close.ewm(span=50).mean()
        features['ema_12_26_spread'] = (ema_12 - ema_26) / close
        features['ema_26_50_spread'] = (ema_26 - ema_50) / close
        
        # Trend strength (ADX proxy)
        plus_dm = (high - high.shift()).clip(lower=0)
        minus_dm = (low.shift() - low).clip(lower=0)
        plus_di = 100 * plus_dm.rolling(14).mean() / (atr_14 + 1e-10)
        minus_di = 100 * minus_dm.rolling(14).mean() / (atr_14 + 1e-10)
        features['trend_strength'] = (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        
        # Market phase score
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        sma_200 = close.rolling(200).mean()
        features['market_phase'] = (
            (close > sma_20).astype(float) +
            (close > sma_50).astype(float) +
            (close > sma_200).astype(float) +
            (sma_20 > sma_50).astype(float) +
            (sma_50 > sma_200).astype(float)
        ) / 5
        
        # Higher highs / Lower lows
        features['hh_count_20'] = ((high > high.shift()).rolling(20).sum()) / 20
        features['ll_count_20'] = ((low < low.shift()).rolling(20).sum()) / 20
        
        # Momentum multi-period
        for period in [5, 10, 20, 60]:
            features[f'momentum_{period}'] = close / close.shift(period) - 1
        
        # Rate of change acceleration
        features['roc_accel'] = features['momentum_10'].diff(5)
        
        # =====================================================================
        # 3. MEAN REVERSION STRENGTH
        # =====================================================================
        
        # Distance to rolling median
        median_20 = close.rolling(20).median()
        median_50 = close.rolling(50).median()
        features['dist_median_20'] = (close - median_20) / median_20
        features['dist_median_50'] = (close - median_50) / median_50
        
        # Z-score of returns
        for period in [20, 60]:
            ret_mean = returns.rolling(period).mean()
            ret_std = returns.rolling(period).std()
            features[f'return_zscore_{period}'] = (returns - ret_mean) / (ret_std + 1e-10)
        
        # Bollinger band position
        bb_sma = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_sma + 2 * bb_std
        bb_lower = bb_sma - 2 * bb_std
        features['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower + 1e-10)
        features['bb_width'] = (bb_upper - bb_lower) / bb_sma
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        features['rsi_14'] = 100 - (100 / (1 + rs))
        features['rsi_normalized'] = (features['rsi_14'] - 50) / 50  # -1 to 1
        
        # Distance from 52-week high/low
        high_252 = close.rolling(252).max()
        low_252 = close.rolling(252).min()
        features['dist_52w_high'] = (close - high_252) / high_252
        features['dist_52w_low'] = (close - low_252) / low_252
        features['position_52w_range'] = (close - low_252) / (high_252 - low_252 + 1e-10)
        
        # =====================================================================
        # CLEANUP
        # =====================================================================
        
        # Replace inf with NaN
        features = features.replace([np.inf, -np.inf], np.nan)
        
        # Forward fill then backward fill
        features = features.ffill().bfill().fillna(0)
        
        self.feature_names = features.columns.tolist()
        self.logger.info(f"Extracted {len(self.feature_names)} features")
        
        return features
    
    def create_regime_labels(self, df: pd.DataFrame, horizon: int = 10) -> Tuple[pd.Series, pd.Series]:
        """
        Criar labels de regime baseados em retornos futuros.
        
        Args:
            df: DataFrame com preços
            horizon: Horizonte para calcular regime (dias)
            
        Returns:
            regime_labels: Series com labels de regime (0-4)
            vol_labels: Series com labels de volatilidade (0-2)
        """
        # Normalizar nomes de colunas
        df_norm = df.copy()
        df_norm.columns = df_norm.columns.str.lower()
        
        close = df_norm['close']
        returns = close.pct_change()
        
        # Retorno futuro
        future_return = close.shift(-horizon) / close - 1
        
        # Classificar regime de tendência
        strong_up = self.config.trend_threshold_strong
        weak_up = self.config.trend_threshold_weak
        
        regime_labels = pd.Series(index=df.index, dtype=int)
        regime_labels[future_return >= strong_up] = MarketRegime.STRONG_UP
        regime_labels[(future_return >= weak_up) & (future_return < strong_up)] = MarketRegime.WEAK_UP
        regime_labels[(future_return > -weak_up) & (future_return < weak_up)] = MarketRegime.SIDEWAYS
        regime_labels[(future_return > -strong_up) & (future_return <= -weak_up)] = MarketRegime.WEAK_DOWN
        regime_labels[future_return <= -strong_up] = MarketRegime.STRONG_DOWN
        
        # Classificar volatilidade
        vol = returns.rolling(self.config.vol_lookback).std() * np.sqrt(252)
        vol_mean = vol.rolling(60).mean()
        vol_std = vol.rolling(60).std()
        vol_zscore = (vol - vol_mean) / (vol_std + 1e-10)
        
        vol_labels = pd.Series(index=df.index, dtype=int)
        vol_labels[vol_zscore < -0.5] = VolatilityState.VOL_CRUSH
        vol_labels[(vol_zscore >= -0.5) & (vol_zscore <= 0.5)] = VolatilityState.VOL_NORMAL
        vol_labels[vol_zscore > 0.5] = VolatilityState.VOL_EXPANSION
        
        return regime_labels, vol_labels
    
    def create_sequences(
        self, 
        features: np.ndarray, 
        regime_labels: np.ndarray,
        vol_labels: np.ndarray,
        future_returns: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Criar sequências para treinamento."""
        seq_length = self.config.sequence_length
        
        X, y_regime, y_vol, y_returns = [], [], [], []
        
        for i in range(seq_length, len(features)):
            X.append(features[i - seq_length:i])
            y_regime.append(regime_labels[i])
            y_vol.append(vol_labels[i])
            y_returns.append(future_returns[i])
        
        return (
            np.array(X), 
            np.array(y_regime), 
            np.array(y_vol),
            np.array(y_returns)
        )
    
    def train(
        self, 
        df: pd.DataFrame,
        validation_split: float = 0.2,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Treinar modelo de detecção de regime.
        
        Args:
            df: DataFrame com dados OHLCV
            validation_split: Fração para validação
            verbose: Mostrar progresso
            
        Returns:
            Dict com métricas de treinamento
        """
        self.logger.info("Starting regime detection training...")
        
        # Normalizar nomes de colunas
        df_norm = df.copy()
        df_norm.columns = df_norm.columns.str.lower()
        
        # Extrair features
        features_df = self.extract_features(df)
        regime_labels, vol_labels = self.create_regime_labels(df)
        
        # Retorno futuro para Sharpe loss
        future_returns = df_norm['close'].pct_change(10).shift(-10)
        
        # Alinhar índices
        common_idx = features_df.index.intersection(regime_labels.dropna().index)
        common_idx = common_idx.intersection(future_returns.dropna().index)
        
        features_df = features_df.loc[common_idx]
        regime_labels = regime_labels.loc[common_idx]
        vol_labels = vol_labels.loc[common_idx]
        future_returns = future_returns.loc[common_idx]
        
        # Normalizar features
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(features_df.values)
        
        # Criar sequências
        X, y_regime, y_vol, y_returns = self.create_sequences(
            features_scaled, 
            regime_labels.values,
            vol_labels.values,
            future_returns.values
        )
        
        self.logger.info(f"Dataset shape: X={X.shape}")
        
        # Split temporal
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_regime_train, y_regime_val = y_regime[:split_idx], y_regime[split_idx:]
        y_vol_train, y_vol_val = y_vol[:split_idx], y_vol[split_idx:]
        y_returns_train, y_returns_val = y_returns[:split_idx], y_returns[split_idx:]
        
        # Converter para tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        X_val_t = torch.FloatTensor(X_val).to(self.device)
        y_regime_train_t = torch.LongTensor(y_regime_train).to(self.device)
        y_regime_val_t = torch.LongTensor(y_regime_val).to(self.device)
        y_vol_train_t = torch.LongTensor(y_vol_train).to(self.device)
        y_vol_val_t = torch.LongTensor(y_vol_val).to(self.device)
        y_returns_train_t = torch.FloatTensor(y_returns_train).to(self.device)
        y_returns_val_t = torch.FloatTensor(y_returns_val).to(self.device)
        
        # DataLoader
        train_dataset = TensorDataset(
            X_train_t, y_regime_train_t, y_vol_train_t, y_returns_train_t
        )
        train_loader = DataLoader(
            train_dataset, 
            batch_size=self.config.batch_size,
            shuffle=True
        )
        
        # Criar modelo
        input_size = X.shape[2]
        self.model = TemporalCNN(input_size, self.config).to(self.device)
        
        # Calcular class weights para balanceamento
        from collections import Counter
        regime_counts = Counter(y_regime_train)
        n_samples = len(y_regime_train)
        n_classes = 5  # 5 regimes
        
        # Inverse frequency weighting
        class_weights = []
        for i in range(n_classes):
            count = regime_counts.get(i, 1)  # Evita divisão por zero
            weight = n_samples / (n_classes * count)
            class_weights.append(weight)
        
        class_weights_tensor = torch.FloatTensor(class_weights).to(self.device)
        
        # Loss e optimizer com class weights
        criterion = SharpeAwareLoss(
            sharpe_weight=self.config.sharpe_weight,
            accuracy_weight=self.config.accuracy_weight,
            class_weights=class_weights_tensor
        )
        
        optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        
        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0
        self.training_history = []
        
        if verbose:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            )
            task = progress.add_task("Training...", total=self.config.epochs)
            progress.start()
        
        for epoch in range(self.config.epochs):
            # Training
            self.model.train()
            train_loss = 0
            
            for batch_X, batch_regime, batch_vol, batch_returns in train_loader:
                optimizer.zero_grad()
                
                regime_logits, vol_logits = self.model(batch_X)
                loss = criterion(
                    regime_logits, batch_regime,
                    vol_logits, batch_vol,
                    batch_returns
                )
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), 
                    self.config.gradient_clip
                )
                optimizer.step()
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                regime_logits_val, vol_logits_val = self.model(X_val_t)
                val_loss = criterion(
                    regime_logits_val, y_regime_val_t,
                    vol_logits_val, y_vol_val_t,
                    y_returns_val_t
                ).item()
                
                # Accuracy
                regime_preds = regime_logits_val.argmax(dim=1)
                regime_acc = (regime_preds == y_regime_val_t).float().mean().item()
                
                vol_preds = vol_logits_val.argmax(dim=1)
                vol_acc = (vol_preds == y_vol_val_t).float().mean().item()
            
            scheduler.step(val_loss)
            
            # History
            self.training_history.append({
                'epoch': epoch,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'regime_accuracy': regime_acc,
                'vol_accuracy': vol_acc,
                'lr': optimizer.param_groups[0]['lr']
            })
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = self.model.state_dict().copy()
            else:
                patience_counter += 1
            
            if patience_counter >= self.config.early_stopping_patience:
                if verbose:
                    console.print(f"\n[yellow]Early stopping at epoch {epoch}[/yellow]")
                break
            
            if verbose:
                progress.update(task, advance=1)
        
        if verbose:
            progress.stop()
        
        # Restaurar melhor modelo
        self.model.load_state_dict(best_state)
        
        # Métricas finais
        self.model.eval()
        with torch.no_grad():
            regime_logits_val, vol_logits_val = self.model(X_val_t)
            regime_preds = regime_logits_val.argmax(dim=1)
            vol_preds = vol_logits_val.argmax(dim=1)
            
            regime_acc = (regime_preds == y_regime_val_t).float().mean().item()
            vol_acc = (vol_preds == y_vol_val_t).float().mean().item()
            
            # Calcular Sharpe simulado
            position_weights = torch.tensor([-1.0, -0.5, 0.0, 0.5, 1.0], device=self.device)
            regime_probs = F.softmax(regime_logits_val, dim=1)
            expected_position = (regime_probs * position_weights).sum(dim=1)
            expected_pnl = expected_position * y_returns_val_t
            
            sharpe = (expected_pnl.mean() / (expected_pnl.std() + 1e-8)).item()
        
        results = {
            'best_val_loss': best_val_loss,
            'final_epoch': epoch,
            'regime_accuracy': regime_acc,
            'vol_accuracy': vol_acc,
            'simulated_sharpe': sharpe,
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'n_features': input_size
        }
        
        self.logger.info(f"Training completed: {results}")
        
        return results
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gerar previsões de regime.
        
        Args:
            df: DataFrame com dados OHLCV
            
        Returns:
            DataFrame com previsões de regime e volatilidade
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Extrair features
        features_df = self.extract_features(df)
        
        # Normalizar
        features_scaled = self.scaler.transform(features_df.values)
        
        # Criar sequências
        seq_length = self.config.sequence_length
        sequences = []
        valid_indices = []
        
        for i in range(seq_length, len(features_scaled)):
            sequences.append(features_scaled[i - seq_length:i])
            valid_indices.append(features_df.index[i])
        
        if len(sequences) == 0:
            raise ValueError(f"Not enough data. Need at least {seq_length} bars.")
        
        sequences = np.array(sequences)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(sequences).to(self.device)
            regime_logits, vol_logits = self.model(X_tensor)
            
            regime_probs = F.softmax(regime_logits, dim=1).cpu().numpy()
            vol_probs = F.softmax(vol_logits, dim=1).cpu().numpy()
            
            regime_preds = regime_logits.argmax(dim=1).cpu().numpy()
            vol_preds = vol_logits.argmax(dim=1).cpu().numpy()
        
        # Criar DataFrame de resultados
        predictions = pd.DataFrame(index=valid_indices)
        
        predictions['regime'] = regime_preds
        predictions['regime_name'] = [MarketRegime(r).name for r in regime_preds]
        
        predictions['vol_state'] = vol_preds
        predictions['vol_state_name'] = [VolatilityState(v).name for v in vol_preds]
        
        # Probabilidades
        for i, regime in enumerate(MarketRegime):
            predictions[f'prob_{regime.name.lower()}'] = regime_probs[:, i]
        
        for i, vol in enumerate(VolatilityState):
            predictions[f'prob_{vol.name.lower()}'] = vol_probs[:, i]
        
        # Posição sugerida (-1 a 1)
        position_weights = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])
        predictions['suggested_position'] = (regime_probs * position_weights).sum(axis=1)
        
        # Confiança
        predictions['regime_confidence'] = regime_probs.max(axis=1)
        predictions['vol_confidence'] = vol_probs.max(axis=1)
        
        return predictions
    
    def get_trading_signals(self, df: pd.DataFrame, confidence_threshold: float = 0.4) -> Dict:
        """
        Gerar sinais de trading baseados em regime.
        
        Args:
            df: DataFrame com dados OHLCV
            confidence_threshold: Confiança mínima para agir
            
        Returns:
            Dict mapeando date -> {'signal': int, 'position': float, 'regime': str}
        """
        predictions = self.predict(df)
        
        signals = {}
        for idx, row in predictions.iterrows():
            date = idx.date() if hasattr(idx, 'date') else idx
            
            # Só agir se confiança suficiente
            if row['regime_confidence'] >= confidence_threshold:
                # Sinal baseado em regime
                if row['regime'] >= MarketRegime.WEAK_UP:  # WEAK_UP ou STRONG_UP
                    signal = 1  # Buy
                elif row['regime'] <= MarketRegime.WEAK_DOWN:  # WEAK_DOWN ou STRONG_DOWN
                    signal = -1  # Sell/Short
                else:
                    signal = 0  # Hold/Flat
            else:
                signal = 0  # Incerteza -> não fazer nada
            
            signals[date] = {
                'signal': signal,
                'position': row['suggested_position'],
                'regime': row['regime_name'],
                'vol_state': row['vol_state_name'],
                'confidence': row['regime_confidence']
            }
        
        return signals
    
    def save_model(self, path: str):
        """Salvar modelo treinado."""
        if self.model is None:
            raise ValueError("No model to save")
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config.__dict__,
            'scaler_mean': self.scaler.mean_,
            'scaler_scale': self.scaler.scale_,
            'feature_names': self.feature_names
        }, path)
        
        self.logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Carregar modelo treinado."""
        from sklearn.preprocessing import StandardScaler
        
        checkpoint = torch.load(path, map_location=self.device)
        
        # Reconstruir config
        self.config = RegimeConfig()
        for k, v in checkpoint['config'].items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        
        self.feature_names = checkpoint['feature_names']
        
        # Reconstruir scaler
        self.scaler = StandardScaler()
        self.scaler.mean_ = checkpoint['scaler_mean']
        self.scaler.scale_ = checkpoint['scaler_scale']
        
        # Reconstruir modelo
        input_size = len(self.feature_names)
        self.model = TemporalCNN(input_size, self.config).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        self.logger.info(f"Model loaded from {path}")
