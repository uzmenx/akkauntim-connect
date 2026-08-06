import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

class AdaptiveWeightManager:
    def __init__(self, db_path='bot_learning.db'):
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(root_dir, db_path)
            self._init_db()
        except Exception as e:
            logger.error(f"Error initializing AdaptiveWeightManager: {e}")

    def _init_db(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS adaptive_signal_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    lstm_direction TEXT,
                    voting_direction TEXT,
                    rl_direction TEXT,
                    actual_direction TEXT,
                    pnl REAL DEFAULT 0.0
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_asw_sym_tf 
                ON adaptive_signal_weights(symbol, timeframe, timestamp)
            ''')
            conn.commit()
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
        finally:
            if conn:
                conn.close()

    def record_outcome(self, symbol: str, timeframe: str, lstm_dir: str, voting_dir: str, rl_dir: str, actual_direction: str, pnl: float):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO adaptive_signal_weights (
                    timestamp, symbol, timeframe, lstm_direction, voting_direction, rl_direction, actual_direction, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.utcnow().isoformat(), symbol, timeframe, lstm_dir, voting_dir, rl_dir, actual_direction, pnl))
            conn.commit()
        except Exception as e:
            logger.error(f"Error recording outcome for {symbol} {timeframe}: {e}")
        finally:
            if conn:
                conn.close()

    def get_weights(self, symbol: str, timeframe: str) -> Dict[str, float]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT lstm_direction, voting_direction, rl_direction, actual_direction
                FROM adaptive_signal_weights
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', (symbol, timeframe))
            rows = cursor.fetchall()
            
            if not rows:
                return {'lstm': 0.35, 'voting': 0.40, 'rl': 0.25}
                
            outcomes = list(reversed(rows)) # Ascending order for EMA
            return self._compute_weights(outcomes)
        except Exception as e:
            logger.error(f"Error getting weights for {symbol} {timeframe}: {e}")
            return {'lstm': 0.35, 'voting': 0.40, 'rl': 0.25}
        finally:
            if conn:
                conn.close()

    def _compute_weights(self, outcomes: List[tuple]) -> Dict[str, float]:
        try:
            if not outcomes:
                return {'lstm': 0.35, 'voting': 0.40, 'rl': 0.25}
                
            ema = {'lstm': 0.35, 'voting': 0.40, 'rl': 0.25}
            alpha = 0.1
            
            for row in outcomes:
                lstm_dir, voting_dir, rl_dir, actual = row
                acc = {
                    'lstm': 1.0 if lstm_dir == actual else 0.0,
                    'voting': 1.0 if voting_dir == actual else 0.0,
                    'rl': 1.0 if rl_dir == actual else 0.0
                }
                
                for k in ema:
                    ema[k] = alpha * acc[k] + (1 - alpha) * ema[k]
                    
            total = 0.0
            constrained = {}
            for k, v in ema.items():
                val = max(0.1, min(0.7, v))
                constrained[k] = val
                total += val
                
            if total > 0:
                normalized = {k: v / total for k, v in constrained.items()}
            else:
                normalized = {'lstm': 0.35, 'voting': 0.40, 'rl': 0.25}
                
            return normalized
        except Exception as e:
            logger.error(f"Error computing weights: {e}")
            return {'lstm': 0.35, 'voting': 0.40, 'rl': 0.25}

    def get_weight_summary(self) -> dict:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT symbol, timeframe
                FROM adaptive_signal_weights
            ''')
            rows = cursor.fetchall()
            
            summary = {}
            for symbol, timeframe in rows:
                key = f"{symbol}_{timeframe}"
                summary[key] = self.get_weights(symbol, timeframe)
            return summary
            
        except Exception as e:
            logger.error(f"Error getting weight summary: {e}")
            return {}
        finally:
            if conn:
                conn.close()
