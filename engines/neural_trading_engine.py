"""
Neural Trading Engine - Redes Neurais para Trading com PyTorch.

Este engine treina modelos de deep learning para prever movimentos de preço
e gerar sinais de compra/venda para o BacktestEngine.

Features:
- Arquitetura parametrizável (LSTM, GRU, Transformer, MLP)
- Otimização de hiperparâmetros via Optuna
- Walk-forward validation
- Feature engineering integrado
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .base_engine import BaseEngine

# Lazy imports para torch (pode não estar instalado)
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None

console = Console()


@dataclass
class NeuralConfig:
    """Configuração da rede neural."""
    # Arquitetura
    model_type: str = 'lstm'  # 'lstm', 'gru', 'transformer', 'mlp'
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.2
    bidirectional: bool = False
    
    # Transformer específico
    num_heads: int = 4
    
    # Treinamento
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 15
    
    # Features
    sequence_length: int = 30  # Dias de lookback
    prediction_horizon: int = 5  # Dias à frente para prever
    
    # Target
    target_type: str = 'direction'  # 'direction', 'return', 'volatility'
    threshold_pct: float = 1.0  # Threshold para classificação binária
    
    # Regularização
    weight_decay: float = 1e-5
    gradient_clip: float = 1.0
    
    # Device
    device: str = 'auto'


class LSTMModel(nn.Module):
    """Modelo LSTM para previsão de séries temporais."""
    
    def __init__(self, input_size: int, config: NeuralConfig, output_size: int = 1):
        super().__init__()
        self.config = config
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            batch_first=True,
            dropout=config.dropout if config.num_layers > 1 else 0,
            bidirectional=config.bidirectional
        )
        
        lstm_output_size = config.hidden_size * (2 if config.bidirectional else 1)
        
        self.fc = nn.Sequential(
            nn.Linear(lstm_output_size, config.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_size // 2, output_size)
        )
        
        if config.target_type == 'direction':
            self.activation = nn.Sigmoid()
        else:
            self.activation = nn.Identity()
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        # Usar apenas o último timestep
        out = self.fc(lstm_out[:, -1, :])
        return self.activation(out)


class GRUModel(nn.Module):
    """Modelo GRU para previsão de séries temporais."""
    
    def __init__(self, input_size: int, config: NeuralConfig, output_size: int = 1):
        super().__init__()
        self.config = config
        
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            batch_first=True,
            dropout=config.dropout if config.num_layers > 1 else 0,
            bidirectional=config.bidirectional
        )
        
        gru_output_size = config.hidden_size * (2 if config.bidirectional else 1)
        
        self.fc = nn.Sequential(
            nn.Linear(gru_output_size, config.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_size // 2, output_size)
        )
        
        if config.target_type == 'direction':
            self.activation = nn.Sigmoid()
        else:
            self.activation = nn.Identity()
    
    def forward(self, x):
        gru_out, _ = self.gru(x)
        out = self.fc(gru_out[:, -1, :])
        return self.activation(out)


class TransformerModel(nn.Module):
    """Transformer para previsão de séries temporais."""
    
    def __init__(self, input_size: int, config: NeuralConfig, output_size: int = 1):
        super().__init__()
        self.config = config
        
        # Embedding layer
        self.embedding = nn.Linear(input_size, config.hidden_size)
        
        # Positional encoding
        self.pos_encoder = nn.Parameter(
            torch.zeros(1, config.sequence_length, config.hidden_size)
        )
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.hidden_size,
            nhead=config.num_heads,
            dim_feedforward=config.hidden_size * 4,
            dropout=config.dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.num_layers
        )
        
        # Output
        self.fc = nn.Sequential(
            nn.Linear(config.hidden_size, config.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_size // 2, output_size)
        )
        
        if config.target_type == 'direction':
            self.activation = nn.Sigmoid()
        else:
            self.activation = nn.Identity()
    
    def forward(self, x):
        # Embedding + positional encoding
        x = self.embedding(x) + self.pos_encoder[:, :x.size(1), :]
        
        # Transformer
        x = self.transformer(x)
        
        # Usar último timestep
        out = self.fc(x[:, -1, :])
        return self.activation(out)


class MLPModel(nn.Module):
    """MLP simples para previsão (baseline)."""
    
    def __init__(self, input_size: int, config: NeuralConfig, output_size: int = 1):
        super().__init__()
        self.config = config
        
        # Flatten input: sequence_length * input_size
        flat_size = config.sequence_length * input_size
        
        layers = []
        current_size = flat_size
        
        for i in range(config.num_layers):
            next_size = config.hidden_size // (2 ** i)
            layers.extend([
                nn.Linear(current_size, next_size),
                nn.ReLU(),
                nn.Dropout(config.dropout)
            ])
            current_size = next_size
        
        layers.append(nn.Linear(current_size, output_size))
        self.network = nn.Sequential(*layers)
        
        if config.target_type == 'direction':
            self.activation = nn.Sigmoid()
        else:
            self.activation = nn.Identity()
    
    def forward(self, x):
        # Flatten
        x = x.view(x.size(0), -1)
        out = self.network(x)
        return self.activation(out)


class NeuralTradingEngine(BaseEngine):
    """
    Engine para trading baseado em redes neurais.
    
    Features:
    - Múltiplas arquiteturas (LSTM, GRU, Transformer, MLP)
    - Feature engineering automático
    - Walk-forward validation
    - Integração com Optuna para otimização
    """
    
    MODEL_CLASSES = {
        'lstm': LSTMModel,
        'gru': GRUModel,
        'transformer': TransformerModel,
        'mlp': MLPModel
    }
    
    def __init__(self, config: Optional[NeuralConfig] = None):
        """
        Inicializar NeuralTradingEngine.
        
        Args:
            config: Configuração da rede neural
        """
        super().__init__()
        
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch não está instalado. Execute:\n"
                "pip install torch"
            )
        
        self.config = config or NeuralConfig()
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.training_history = []
        
        # Setup device
        if self.config.device == 'auto':
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
            elif torch.backends.mps.is_available():
                self.device = torch.device('mps')  # Apple Silicon
            else:
                self.device = torch.device('cpu')
        else:
            self.device = torch.device(self.config.device)
        
        self.logger.info(f"NeuralTradingEngine initialized on {self.device}")
    
    def run(self):
        """Execute não implementado - use train() e predict()."""
        raise NotImplementedError("Use train() and predict() methods instead")
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extrair features técnicas do DataFrame OHLCV.
        
        Args:
            df: DataFrame com colunas open, high, low, close, volume
            
        Returns:
            DataFrame com features extraídas
        """
        features = pd.DataFrame(index=df.index)
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Returns
        for period in [1, 3, 5, 10, 20]:
            features[f'return_{period}d'] = close.pct_change(period)
            features[f'log_return_{period}d'] = np.log(close / close.shift(period))
        
        # Volatilidade
        for period in [5, 10, 20, 30]:
            features[f'volatility_{period}d'] = close.pct_change().rolling(period).std()
        
        # RSI
        for period in [7, 14, 21]:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / (loss + 1e-10)
            features[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            sma = close.rolling(period).mean()
            features[f'sma_{period}_ratio'] = close / sma
            features[f'sma_{period}_slope'] = sma.pct_change(5)
        
        # EMA
        for period in [12, 26, 50]:
            ema = close.ewm(span=period).mean()
            features[f'ema_{period}_ratio'] = close / ema
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        features['macd'] = macd / close  # Normalizado
        features['macd_signal'] = signal / close
        features['macd_hist'] = (macd - signal) / close
        
        # Bollinger Bands
        for period in [20]:
            sma = close.rolling(period).mean()
            std = close.rolling(period).std()
            features[f'bb_upper_dist_{period}'] = (close - (sma + 2 * std)) / close
            features[f'bb_lower_dist_{period}'] = (close - (sma - 2 * std)) / close
            features[f'bb_width_{period}'] = (4 * std) / sma
            features[f'bb_position_{period}'] = (close - (sma - 2 * std)) / (4 * std + 1e-10)
        
        # Volume
        vol_sma = volume.rolling(20).mean()
        features['volume_ratio'] = volume / (vol_sma + 1e-10)
        features['volume_trend'] = volume.pct_change(5)
        
        # High-Low range
        features['hl_ratio'] = (high - low) / close
        features['hl_ratio_sma'] = features['hl_ratio'].rolling(10).mean()
        
        # ATR normalizado
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        features['atr_14'] = tr.rolling(14).mean() / close
        
        # Momentum
        features['momentum_10'] = close / close.shift(10) - 1
        features['momentum_20'] = close / close.shift(20) - 1
        
        # Distance from highs/lows
        features['dist_52w_high'] = close / close.rolling(252).max() - 1
        features['dist_52w_low'] = close / close.rolling(252).min() - 1
        
        # Limpar NaN e inf
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.ffill().bfill().fillna(0)
        
        self.feature_names = features.columns.tolist()
        self.logger.info(f"Extracted {len(self.feature_names)} features")
        
        return features
    
    def create_sequences(
        self, 
        features: np.ndarray, 
        targets: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Criar sequências para treinamento LSTM/GRU.
        
        Args:
            features: Array de features (n_samples, n_features)
            targets: Array de targets (n_samples,)
            
        Returns:
            Tuple de (X_sequences, y_targets)
        """
        seq_length = self.config.sequence_length
        horizon = self.config.prediction_horizon
        
        X, y = [], []
        
        for i in range(seq_length, len(features) - horizon):
            X.append(features[i - seq_length:i])
            y.append(targets[i + horizon - 1])
        
        return np.array(X), np.array(y)
    
    def create_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Criar target para o modelo.
        
        Args:
            df: DataFrame com dados de preço
            
        Returns:
            Series com target
        """
        close = df['close']
        horizon = self.config.prediction_horizon
        
        if self.config.target_type == 'direction':
            # Classificação binária: preço sobe (1) ou desce (0)
            future_return = close.shift(-horizon) / close - 1
            threshold = self.config.threshold_pct / 100
            target = (future_return > threshold).astype(float)
        
        elif self.config.target_type == 'return':
            # Regressão: retorno futuro
            target = close.shift(-horizon) / close - 1
        
        elif self.config.target_type == 'volatility':
            # Prever volatilidade futura
            returns = close.pct_change()
            target = returns.rolling(horizon).std().shift(-horizon)
        
        else:
            raise ValueError(f"Unknown target type: {self.config.target_type}")
        
        return target
    
    def train(
        self, 
        df: pd.DataFrame,
        validation_split: float = 0.2,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Treinar o modelo neural.
        
        Args:
            df: DataFrame com dados OHLCV
            validation_split: Fração para validação
            verbose: Mostrar progresso
            
        Returns:
            Dict com métricas de treinamento
        """
        self.logger.info("Starting neural network training...")
        
        # Extrair features
        features_df = self.extract_features(df)
        targets = self.create_target(df)
        
        # Alinhar índices
        common_idx = features_df.index.intersection(targets.dropna().index)
        features_df = features_df.loc[common_idx]
        targets = targets.loc[common_idx]
        
        # Normalizar features
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(features_df.values)
        
        # Criar sequências
        X, y = self.create_sequences(features_scaled, targets.values)
        
        self.logger.info(f"Dataset shape: X={X.shape}, y={y.shape}")
        
        # Split train/val (temporal)
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Converter para tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_t = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)
        X_val_t = torch.FloatTensor(X_val).to(self.device)
        y_val_t = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)
        
        # DataLoaders
        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(
            train_dataset, 
            batch_size=self.config.batch_size,
            shuffle=True
        )
        
        # Criar modelo
        input_size = X.shape[2]
        model_class = self.MODEL_CLASSES[self.config.model_type]
        self.model = model_class(input_size, self.config).to(self.device)
        
        # Loss e optimizer
        if self.config.target_type == 'direction':
            criterion = nn.BCELoss()
        else:
            criterion = nn.MSELoss()
        
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
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                
                # Gradient clipping
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
                val_outputs = self.model(X_val_t)
                val_loss = criterion(val_outputs, y_val_t).item()
                
                # Accuracy para classificação
                if self.config.target_type == 'direction':
                    val_preds = (val_outputs > 0.5).float()
                    val_acc = (val_preds == y_val_t).float().mean().item()
                else:
                    val_acc = 0
            
            scheduler.step(val_loss)
            
            # History
            self.training_history.append({
                'epoch': epoch,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'val_accuracy': val_acc,
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
            val_outputs = self.model(X_val_t)
            
            if self.config.target_type == 'direction':
                val_preds = (val_outputs > 0.5).float()
                accuracy = (val_preds == y_val_t).float().mean().item()
                
                # Precision/Recall para classe positiva (compra)
                tp = ((val_preds == 1) & (y_val_t == 1)).sum().item()
                fp = ((val_preds == 1) & (y_val_t == 0)).sum().item()
                fn = ((val_preds == 0) & (y_val_t == 1)).sum().item()
                
                precision = tp / (tp + fp + 1e-10)
                recall = tp / (tp + fn + 1e-10)
                f1 = 2 * precision * recall / (precision + recall + 1e-10)
            else:
                accuracy = 0
                precision = 0
                recall = 0
                f1 = 0
        
        results = {
            'best_val_loss': best_val_loss,
            'final_epoch': epoch,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'n_features': input_size
        }
        
        self.logger.info(f"Training completed: {results}")
        
        return results
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gerar previsões para um DataFrame.
        
        Args:
            df: DataFrame com dados OHLCV
            
        Returns:
            DataFrame com previsões (signal, probability)
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
            outputs = self.model(X_tensor)
            probabilities = outputs.cpu().numpy().flatten()
        
        # Criar DataFrame de resultados
        predictions = pd.DataFrame(index=valid_indices)
        predictions['probability'] = probabilities
        
        if self.config.target_type == 'direction':
            predictions['signal'] = (probabilities > 0.5).astype(int)
        else:
            predictions['signal'] = (probabilities > 0).astype(int)
        
        return predictions
    
    def get_signals_dict(self, df: pd.DataFrame) -> Dict:
        """
        Gerar dicionário de sinais para uso com estratégia backtrader.
        
        Args:
            df: DataFrame com dados OHLCV
            
        Returns:
            Dict mapeando date -> signal (1=buy, 0=hold/sell)
        """
        predictions = self.predict(df)
        
        signals = {}
        for idx, row in predictions.iterrows():
            if hasattr(idx, 'date'):
                date_key = idx.date()
            else:
                date_key = idx
            signals[date_key] = int(row['signal'])
        
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
        
        self.config = NeuralConfig(**checkpoint['config'])
        self.feature_names = checkpoint['feature_names']
        
        # Reconstruir scaler
        self.scaler = StandardScaler()
        self.scaler.mean_ = checkpoint['scaler_mean']
        self.scaler.scale_ = checkpoint['scaler_scale']
        
        # Reconstruir modelo
        input_size = len(self.feature_names)
        model_class = self.MODEL_CLASSES[self.config.model_type]
        self.model = model_class(input_size, self.config).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        self.logger.info(f"Model loaded from {path}")
