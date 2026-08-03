import os
import sqlite3
import logging
import numpy as np
import pandas as pd
import json

try:
    import gymnasium as gym
    from gymnasium import spaces
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import SubprocVecEnv
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False
    logging.warning("gymnasium yoki stable-baselines3 o'rnatilmagan! Qora Quti simulyatori ishlamaydi.")

logger = logging.getLogger(__name__)

class TradingEnv(gym.Env if RL_AVAILABLE else object):
    """
    Qora Quti (Black Box) Simulyatori.
    Botning o'tgan ma'lumotlari asosida Virtual Savdo muhiti.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, db_path: str, symbol=None, initial_balance=1000.0, max_steps=1000, curriculum_level=3, is_eval=False):
        super().__init__()
        self.db_path = db_path
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.max_steps = max_steps
        self.curriculum_level = curriculum_level
        self.is_eval = is_eval
        
        if not RL_AVAILABLE:
            return

        # Ma'lumotlarni yuklash (1-bosqichdagi Shadow DB dan)
        self.df = self._load_data(self.symbol)
        
        # Harakatlar: 0=HOLD, 1=BUY, 2=SELL, 3=CLOSE
        # Action space kengaytirilishi (masalan pozitsiya hajmi uchun MultiDiscrete) mumkin,
        # lekin hozirgi bosqichda PPO training barqarorligi uchun Discrete(4) da qoldirildi.
        # Xavf va lot o'lchami alohida Risk Manager orqali boshqariladi.
        self.action_space = spaces.Discrete(4)
        
        # Holat: [balance_ratio, open, high, low, close, volume, has_open_position, profit_ratio] (8 ta)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(8,), dtype=np.float32)

        self.reset()

    def _load_data(self, symbol=None):
        if not os.path.exists(self.db_path):
            return pd.DataFrame()
        try:
            conn = sqlite3.connect(self.db_path)
            
            if symbol is None:
                cursor = conn.cursor()
                cursor.execute("SELECT symbol FROM shadow_states GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT 1")
                res = cursor.fetchone()
                if res:
                    symbol = res[0]
                else:
                    symbol = "EURUSD"
                    
            df = pd.read_sql_query("SELECT price_open, price_high, price_low, price_close, tick_volume FROM shadow_states WHERE symbol = ? ORDER BY timestamp ASC LIMIT 50000", conn, params=(symbol,))
            conn.close()
            
            # OOS (Out-Of-Sample) split: last 20% for eval
            split_idx = int(len(df) * 0.8)
            if hasattr(self, 'is_eval') and self.is_eval:
                df = df.iloc[split_idx:].reset_index(drop=True)
            else:
                df = df.iloc[:split_idx].reset_index(drop=True)
            
            # Normalizatsiya (sodda usul) va statistikalarni saqlash
            norm_stats = {}
            for col in df.columns:
                mean = df[col].mean()
                std = df[col].std() + 1e-8
                df[col] = (df[col] - mean) / std
                norm_stats[col] = {"mean": mean, "std": std}
                
            norm_stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'norm_stats.json')
            with open(norm_stats_path, 'w') as f:
                json.dump(norm_stats, f, indent=2)
                
            return df
        except Exception as e:
            logger.error(f"Simulator ma'lumot yuklashda xatolik: {e}")
            return pd.DataFrame()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.balance = self.initial_balance
        self.current_step = 0
        self.position = 0 # 0=none, 1=buy, -1=sell
        self.entry_price = 0.0
        
        # Risk (drawdown) metriclari
        self.trade_peak_profit = 0.0
        self.trade_max_drawdown = 0.0
        
        if self.df.empty or len(self.df) < self.max_steps + 10:
            self.max_steps = max(10, len(self.df) - 10) if not self.df.empty else 10
            
        self.start_idx = np.random.randint(0, max(1, len(self.df) - self.max_steps - 1)) if len(self.df) > self.max_steps else 0
        
        if getattr(self, 'curriculum_level', 3) < 3 and len(self.df) > self.max_steps + 10:
            if 'volatility' not in self.df.columns:
                self.df['volatility'] = (self.df['price_high'] - self.df['price_low']).abs()
            vol_roll = self.df['volatility'].rolling(self.max_steps).mean().shift(-self.max_steps)
            
            if self.curriculum_level == 1:
                q = vol_roll.quantile(0.33)
                valid_indices = vol_roll[vol_roll <= q].index
            elif self.curriculum_level == 2:
                q1 = vol_roll.quantile(0.33)
                q2 = vol_roll.quantile(0.66)
                valid_indices = vol_roll[(vol_roll > q1) & (vol_roll <= q2)].index
            else:
                valid_indices = []
                
            valid_indices = [i for i in valid_indices if i <= len(self.df) - self.max_steps - 1]
            if valid_indices:
                self.start_idx = int(np.random.choice(valid_indices))
        
        return self._get_obs(), {}

    def _get_obs(self):
        if self.df.empty:
            return np.zeros(8, dtype=np.float32)
            
        idx = min(self.start_idx + self.current_step, len(self.df) - 1)
        row = self.df.iloc[idx]
        
        unrealized_profit = 0.0
        if self.position == 1:
            unrealized_profit = (row['price_close'] - self.entry_price) * 1000 # shunchaki koeffitsient
        elif self.position == -1:
            unrealized_profit = (self.entry_price - row['price_close']) * 1000

        obs = np.array([
            self.balance / self.initial_balance,
            row['price_open'],
            row['price_high'],
            row['price_low'],
            row['price_close'],
            row['tick_volume'],
            1.0 if self.position != 0 else 0.0,
            unrealized_profit / self.initial_balance
        ], dtype=np.float32)
        
        return obs

    def step(self, action):
        if self.df.empty:
            return self._get_obs(), 0.0, True, False, {}
            
        idx = min(self.start_idx + self.current_step, len(self.df) - 1)
        current_price = self.df.iloc[idx]['price_close']
        
        reward = 0.0
        done = False
        
        def calc_risk_adjusted_reward(profit, max_dd):
            # Sharpe/Sortino ga o'xshash risk-adjusted reward
            # Agar drawdown katta bo'lsa (yoki katta minusga kirib chiqqan bo'lsa), jazolaymiz
            # Penalty factor = 0.5 (drawdown summasining yarmi)
            penalty = max_dd * 0.5
            return profit - penalty

        # Action logic
        # 0 = HOLD, 1 = BUY, 2 = SELL, 3 = CLOSE
        if action == 1: # BUY
            if self.position == 0:
                self.position = 1
                self.entry_price = current_price
                self.trade_peak_profit = 0.0
                self.trade_max_drawdown = 0.0
                reward = -0.01
            elif self.position == -1: # Close Sell
                profit = (self.entry_price - current_price) * 1000
                self.balance += profit
                reward = calc_risk_adjusted_reward(profit, self.trade_max_drawdown) - 0.01
                self.position = 1
                self.entry_price = current_price
                self.trade_peak_profit = 0.0
                self.trade_max_drawdown = 0.0
                
        elif action == 2: # SELL
            if self.position == 0:
                self.position = -1
                self.entry_price = current_price
                self.trade_peak_profit = 0.0
                self.trade_max_drawdown = 0.0
                reward = -0.01
            elif self.position == 1: # Close Buy
                profit = (current_price - self.entry_price) * 1000
                self.balance += profit
                reward = calc_risk_adjusted_reward(profit, self.trade_max_drawdown) - 0.01
                self.position = -1
                self.entry_price = current_price
                self.trade_peak_profit = 0.0
                self.trade_max_drawdown = 0.0
                
        elif action == 3: # CLOSE
            if self.position == 1:
                profit = (current_price - self.entry_price) * 1000
                self.balance += profit
                reward = calc_risk_adjusted_reward(profit, self.trade_max_drawdown)
                self.position = 0
                self.entry_price = 0.0
                self.trade_peak_profit = 0.0
                self.trade_max_drawdown = 0.0
            elif self.position == -1:
                profit = (self.entry_price - current_price) * 1000
                self.balance += profit
                reward = calc_risk_adjusted_reward(profit, self.trade_max_drawdown)
                self.position = 0
                self.entry_price = 0.0
                self.trade_peak_profit = 0.0
                self.trade_max_drawdown = 0.0
            else:
                reward = 0.0
                
        else: # HOLD
            if self.position != 0:
                # Update drawdown tracking while position is open
                if self.position == 1:
                    unrealized_profit = (current_price - self.entry_price) * 1000
                else:
                    unrealized_profit = (self.entry_price - current_price) * 1000
                    
                if unrealized_profit > self.trade_peak_profit:
                    self.trade_peak_profit = unrealized_profit
                
                current_dd = self.trade_peak_profit - unrealized_profit
                if current_dd > self.trade_max_drawdown:
                    self.trade_max_drawdown = current_dd
                    
                reward = -0.1
            else:
                reward = 0.0

        self.current_step += 1
        if self.current_step >= self.max_steps or self.balance <= 0:
            done = True
            if self.balance <= 0:
                reward -= 100 # Qattiq jazo
                
        return self._get_obs(), float(reward), done, False, {"balance": self.balance}


class RLAgentRunner:
    def __init__(self, db_path: str = 'bot_learning.db'):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(root_dir, db_path)
        else:
            self.db_path = db_path
            
        self.model_path = os.path.join(root_dir, 'bot', 'learning', 'ppo_agent')
        self.stats_path = os.path.join(root_dir, 'public', 'blackbox.json')
        
        self._cached_model = None
        self._model_mtime = 0
        
    def train_agent(self, total_timesteps=1000):
        if not RL_AVAILABLE:
            logger.warning("RL libraries yo'q. Train qilib bo'lmaydi.")
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM shadow_states")
            total_rows = cursor.fetchone()[0]
            conn.close()
            
            # Agar ma'lumot kam bo'lsa (masalan 10,000 qatordan kam), PPO overfit bo'lishi mumkin
            if total_rows < 5000:
                logger.warning(f"RL PPO uchun ma'lumotlar yetarli emas ({total_rows} ta). Kamida 5000 ta shadow_states kutiladi. Train bekor qilindi.")
                return
            else:
                logger.info(f"RL PPO training uchun yetarli ma'lumot topildi: {total_rows} ta qator (kamida {total_rows // 1000} ta to'liq epizod bo'lishi mumkin).")
        except Exception as e:
            logger.warning(f"Ma'lumotlar hajmini tekshirishda xato: {e}")

        logger.info("Qora Quti (Black Box) simulyatsiyasi boshlandi... (Curriculum Learning)")
        
        curriculum_stages = [
            {"level": 1, "timesteps": int(total_timesteps * 0.2), "desc": "Past volatillik (Easy)"},
            {"level": 2, "timesteps": int(total_timesteps * 0.3), "desc": "O'rtacha volatillik (Medium)"},
            {"level": 3, "timesteps": int(total_timesteps * 0.5), "desc": "Barcha sharoitlar (Hard)"}
        ]
        
        model = None
        for stage in curriculum_stages:
            if stage["timesteps"] <= 0:
                continue
                
            logger.info(f"PPO Curriculum Stage: {stage['desc']} - {stage['timesteps']} qadam")
            env = make_vec_env(lambda: TradingEnv(self.db_path, curriculum_level=stage["level"]), n_envs=4, vec_env_cls=SubprocVecEnv)
            
            if model is None:
                if os.path.exists(self.model_path + ".zip"):
                    model = PPO.load(self.model_path, env=env)
                    logger.info("Oldingi RL modeli yuklandi.")
                else:
                    model = PPO("MlpPolicy", env, 
                                learning_rate=0.0003,
                                n_steps=2048,
                                batch_size=256,
                                ent_coef=0.01,
                                gamma=0.99,
                                verbose=0)
            else:
                model.set_env(env)
                
            model.learn(total_timesteps=stage['timesteps'])
            
        model.save(self.model_path)
        
        logger.info("RL Agent o'qitish yakunlandi.")
        self._update_ui_stats(env, model, total_timesteps)
        
    def _update_ui_stats(self, env, model, timesteps_played):
        try:
            # OOS test uchun yangi muhit
            eval_env = make_vec_env(lambda: TradingEnv(self.db_path, is_eval=True), n_envs=1)
            obs = eval_env.reset()
            total_reward = 0
            wins = 0
            trades = 0
            
            for _ in range(100):
                action, _states = model.predict(obs, deterministic=True)
                obs, rewards, dones, infos = eval_env.step(action)
                
                # Agar harakat qilsa va reward o'zgarsa, savdo deb qaraymiz
                # reward 100 dan kichik bo'lsa (yutqazish jarimasi 100)
                if rewards[0] != 0 and rewards[0] != -100:
                    trades += 1
                    if rewards[0] > 0:
                        wins += 1
                total_reward += rewards[0]
            
            win_rate = (wins / trades * 100) if trades > 0 else 0.0
            avg_reward = total_reward / 100.0

            stats = {}
            if os.path.exists(self.stats_path):
                try:
                    with open(self.stats_path, 'r') as f:
                        stats = json.load(f)
                except Exception:
                    pass
            
            # Eski progress bo'lsa shunga qo'shamiz
            old_progress = stats.get("rl_agent_progress", {
                "episodes_played": 0, "avg_reward": 0, "win_rate_simulation": 0, "growth": 0
            })
            
            stats["rl_agent_progress"] = {
                "episodes_played": old_progress.get("episodes_played", 0) + (timesteps_played // 100),
                "avg_reward": round(float(avg_reward), 2),
                "win_rate_simulation": round(float(win_rate), 1),
                "growth": round(float(win_rate - old_progress.get("win_rate_simulation", 50.0)), 1)
            }
            stats["updated_at"] = pd.Timestamp.now().isoformat()
            
            with open(self.stats_path, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Qora quti natijalari UI uchun saqlandi. WR: {win_rate:.1f}%")
        except Exception as e:
            logger.error(f"UI stats yangilashda xato: {e}")

    def predict_action(self, obs_data: list) -> str:
        """
        Jonli bozorda (MT5 dan olingan) holatga qarab agent qarorini qaytaradi.
        obs_data: [balance_ratio, open, high, low, close, volume, position_status, unrealized_profit_ratio]
        """
        model_file = self.model_path + ".zip"
        if not RL_AVAILABLE or not os.path.exists(model_file):
            return "HOLD"
            
        try:
            mtime = os.path.getmtime(model_file)
            if self._cached_model is None or self._model_mtime != mtime:
                self._cached_model = PPO.load(self.model_path)
                self._model_mtime = mtime
                
            obs_data = list(obs_data)
            
            # Normalize input
            norm_stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'norm_stats.json')
            if os.path.exists(norm_stats_path):
                with open(norm_stats_path, 'r') as f:
                    norm_stats = json.load(f)
                cols = ['price_open', 'price_high', 'price_low', 'price_close', 'tick_volume']
                for i, col in enumerate(cols):
                    if col in norm_stats:
                        obs_data[i+1] = (obs_data[i+1] - norm_stats[col]['mean']) / norm_stats[col]['std']
                        
            # Fix position encoding
            obs_data[6] = 1.0 if obs_data[6] != 0 else 0.0
            
            obs = np.array(obs_data, dtype=np.float32)
            action, _ = self._cached_model.predict(obs, deterministic=True)
            
            mapping = {0: "HOLD", 1: "BUY", 2: "SELL", 3: "CLOSE"}
            return mapping.get(int(action), "HOLD")
        except Exception as e:
            logger.debug(f"RL Agent predict xatolik: {e}")
            return "HOLD"
