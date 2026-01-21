"""
Reinforcement Learning Trading Engine
Uses Stable-Baselines3 for optimal entry/exit policy learning.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO, A2C, DQN
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback
import warnings
warnings.filterwarnings('ignore')


class BTCTradingEnv(gym.Env):
    """
    Custom Gymnasium environment for BTC trading.
    
    State: OHLCV + technical indicators (last N days)
    Actions: 0 = Hold/Stay Out, 1 = Buy/Hold Position
    Reward: Portfolio value change
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        window_size: int = 30,
        initial_balance: float = 100000.0,
        commission: float = 0.001,
        features: Optional[pd.DataFrame] = None
    ):
        super().__init__()
        
        self.df = df.reset_index(drop=True)
        self.window_size = window_size
        self.initial_balance = initial_balance
        self.commission = commission
        
        # Use provided features or create basic ones
        if features is not None:
            self.features = features.reset_index(drop=True)
        else:
            self.features = self._create_features()
        
        # Ensure same length
        min_len = min(len(self.df), len(self.features))
        self.df = self.df.iloc[:min_len]
        self.features = self.features.iloc[:min_len]
        
        # Action space: 0 = Stay out/Hold out, 1 = Buy/Hold position
        self.action_space = spaces.Discrete(2)
        
        # Observation space: window of features (normalized)
        n_features = self.features.shape[1]
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window_size, n_features),
            dtype=np.float32
        )
        
        # Episode variables
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0  # 0 = no position, 1 = in position
        self.entry_price = 0
        self.total_trades = 0
        self.profitable_trades = 0
        
    def _create_features(self) -> pd.DataFrame:
        """Create basic technical features if not provided."""
        features = pd.DataFrame()
        
        # Price features (normalized by current close)
        features['close_norm'] = self.df['close'] / self.df['close'].iloc[0]
        features['high_norm'] = self.df['high'] / self.df['close']
        features['low_norm'] = self.df['low'] / self.df['close']
        features['volume_norm'] = self.df['volume'] / self.df['volume'].rolling(20).mean()
        
        # Returns
        for period in [1, 7, 14, 30]:
            features[f'return_{period}d'] = self.df['close'].pct_change(period)
        
        # Moving averages
        for period in [7, 20, 50]:
            sma = self.df['close'].rolling(period).mean()
            features[f'sma_{period}_ratio'] = self.df['close'] / sma
        
        # Volatility
        features['volatility_7d'] = self.df['close'].pct_change().rolling(7).std()
        features['volatility_30d'] = self.df['close'].pct_change().rolling(30).std()
        
        # Fill NaN
        features = features.fillna(method='bfill').fillna(0)
        
        return features
    
    def reset(self, seed=None, options=None):
        """Reset environment to initial state."""
        super().reset(seed=seed)
        
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        self.total_trades = 0
        self.profitable_trades = 0
        
        return self._get_observation(), {}
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation (window of features)."""
        start = max(0, self.current_step - self.window_size)
        end = self.current_step
        
        obs = self.features.iloc[start:end].values
        
        # Pad if necessary
        if len(obs) < self.window_size:
            padding = np.zeros((self.window_size - len(obs), obs.shape[1]))
            obs = np.vstack([padding, obs])
        
        return obs.astype(np.float32)
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one step in the environment."""
        current_price = self.df.iloc[self.current_step]['close']
        
        reward = 0
        
        # Action 0: Stay out / Exit position
        if action == 0:
            if self.position == 1:
                # Exit position
                exit_value = self.balance * (1 - self.commission)
                profit = (current_price - self.entry_price) / self.entry_price
                self.balance = self.balance * (1 + profit) * (1 - self.commission)
                
                reward = profit * 100  # Reward = % profit
                
                if profit > 0:
                    self.profitable_trades += 1
                
                self.total_trades += 1
                self.position = 0
        
        # Action 1: Enter / Hold position
        else:
            if self.position == 0:
                # Enter position
                self.entry_price = current_price
                self.balance = self.balance * (1 - self.commission)
                self.position = 1
                reward = 0  # No immediate reward for entering
            else:
                # Hold position - reward based on unrealized profit
                unrealized_profit = (current_price - self.entry_price) / self.entry_price
                reward = unrealized_profit * 0.1  # Small reward for holding profitable position
        
        # Move to next step
        self.current_step += 1
        
        # Check if episode is done
        done = self.current_step >= len(self.df) - 1
        
        if done and self.position == 1:
            # Force exit at end
            profit = (current_price - self.entry_price) / self.entry_price
            self.balance = self.balance * (1 + profit) * (1 - self.commission)
            reward += profit * 100
        
        # Additional reward shaping
        # Penalize for too many trades (excessive trading)
        if self.total_trades > 0:
            trade_frequency_penalty = -0.1 * (self.total_trades / self.current_step)
            reward += trade_frequency_penalty
        
        # Bonus for final portfolio value
        if done:
            final_return = (self.balance - self.initial_balance) / self.initial_balance
            reward += final_return * 100
        
        obs = self._get_observation()
        info = {
            'balance': self.balance,
            'position': self.position,
            'total_trades': self.total_trades,
            'win_rate': self.profitable_trades / max(1, self.total_trades)
        }
        
        return obs, reward, done, False, info
    
    def render(self, mode='human'):
        """Render environment (optional)."""
        pass


class RLTradingEngine:
    """
    Reinforcement Learning engine for trading strategy optimization.
    Uses PPO (Proximal Policy Optimization) algorithm.
    """
    
    def __init__(
        self,
        algorithm: str = 'PPO',
        policy: str = 'MlpPolicy',
        learning_rate: float = 0.0003,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        verbose: int = 1
    ):
        """
        Initialize RL engine.
        
        Args:
            algorithm: RL algorithm ('PPO', 'A2C', 'DQN')
            policy: Policy network type
            learning_rate: Learning rate
            n_steps: Steps per update (PPO)
            batch_size: Batch size
            n_epochs: Training epochs per update
            gamma: Discount factor
            verbose: Verbosity level
        """
        self.algorithm = algorithm
        self.policy = policy
        self.learning_rate = learning_rate
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.gamma = gamma
        self.verbose = verbose
        self.model = None
        self.env = None
    
    def train(
        self,
        df: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        total_timesteps: int = 100000,
        window_size: int = 30,
        eval_freq: int = 10000,
        save_path: Optional[str] = None
    ) -> Dict:
        """
        Train RL agent on historical data.
        
        Args:
            df: OHLCV DataFrame
            features: Pre-computed features (optional)
            total_timesteps: Total training steps
            window_size: Observation window size
            eval_freq: Evaluation frequency
            save_path: Path to save model
            
        Returns:
            Training metrics
        """
        print("\n" + "="*80)
        print("🤖 TRAINING RL AGENT")
        print("="*80)
        print(f"Algorithm: {self.algorithm}")
        print(f"Total timesteps: {total_timesteps:,}")
        print(f"Data points: {len(df)}")
        print("="*80 + "\n")
        
        # Create environment
        self.env = BTCTradingEnv(
            df=df,
            window_size=window_size,
            features=features
        )
        
        # Wrap in DummyVecEnv for stable-baselines3
        vec_env = DummyVecEnv([lambda: self.env])
        
        # Create model
        if self.algorithm == 'PPO':
            self.model = PPO(
                self.policy,
                vec_env,
                learning_rate=self.learning_rate,
                n_steps=self.n_steps,
                batch_size=self.batch_size,
                n_epochs=self.n_epochs,
                gamma=self.gamma,
                verbose=self.verbose
            )
        elif self.algorithm == 'A2C':
            self.model = A2C(
                self.policy,
                vec_env,
                learning_rate=self.learning_rate,
                gamma=self.gamma,
                verbose=self.verbose
            )
        elif self.algorithm == 'DQN':
            self.model = DQN(
                self.policy,
                vec_env,
                learning_rate=self.learning_rate,
                batch_size=self.batch_size,
                gamma=self.gamma,
                verbose=self.verbose
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
        
        # Train
        print("🔄 Training agent...")
        self.model.learn(total_timesteps=total_timesteps)
        print("✅ Training complete!\n")
        
        # Save model
        if save_path:
            self.model.save(save_path)
            print(f"💾 Model saved to: {save_path}\n")
        
        return {
            'total_timesteps': total_timesteps,
            'algorithm': self.algorithm
        }
    
    def predict(
        self,
        df: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        window_size: int = 30
    ) -> Tuple[np.ndarray, Dict]:
        """
        Generate predictions using trained agent.
        
        Args:
            df: OHLCV DataFrame
            features: Pre-computed features (optional)
            window_size: Observation window size
            
        Returns:
            (actions, info_dict)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Create environment
        test_env = BTCTradingEnv(
            df=df,
            window_size=window_size,
            features=features
        )
        
        # Run episode
        obs, _ = test_env.reset()
        actions = []
        infos = []
        
        done = False
        while not done:
            action, _ = self.model.predict(obs, deterministic=True)
            actions.append(action)
            
            obs, reward, done, truncated, info = test_env.step(action)
            infos.append(info)
        
        # Extract final metrics
        final_info = infos[-1] if infos else {}
        
        results = {
            'final_balance': final_info.get('balance', test_env.initial_balance),
            'total_trades': final_info.get('total_trades', 0),
            'win_rate': final_info.get('win_rate', 0),
            'actions': np.array(actions),
            'infos': infos
        }
        
        return np.array(actions), results
    
    def load_model(self, path: str):
        """Load trained model from disk."""
        if self.algorithm == 'PPO':
            self.model = PPO.load(path)
        elif self.algorithm == 'A2C':
            self.model = A2C.load(path)
        elif self.algorithm == 'DQN':
            self.model = DQN.load(path)
        
        print(f"✅ Model loaded from: {path}")
