import sqlite3
import os
import logging
from datetime import datetime
from bot.prediction.signal_merger import merge_signals

logger = logging.getLogger(__name__)

class ShadowMergerTracker:
    """
    "Agar men faqat voting engine'ga ishonganimda" va 
    "agar men merged signal'ga ishonganimda" degan gipotezalarni 
    alohida virtual kuzatish (shadow tracking) uchun klass.
    """
    def __init__(self, db_path: str = 'bot_learning.db'):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(root_dir, db_path)
        else:
            self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shadow_merger_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    voting_direction TEXT,
                    voting_confidence REAL,
                    lstm_direction TEXT,
                    lstm_confidence REAL,
                    merged_direction TEXT,
                    merged_confidence REAL,
                    agreement BOOLEAN,
                    stat_weight_used REAL,
                    lstm_weight_used REAL,
                    actual_outcome REAL DEFAULT 0.0,
                    audit_trail TEXT
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_smt_sym_ts ON shadow_merger_tracking(symbol, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_smt_sym_tf ON shadow_merger_tracking(symbol, timeframe)')
            conn.commit()
        except Exception as e:
            logger.error(f"ShadowMergerTracker DB init xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def record_signals(self, symbol: str, timeframe: str,
                       voting_direction: str, voting_confidence: float,
                       lstm_direction: str, lstm_confidence: float,
                       shadow_win_rate: float, shadow_trade_count: int,
                       rl_direction: str = "HOLD"):
        """
        Voting va LSTM signallarini olib, merge qilingan natija bilan birga bazaga yozadi.
        """
        if voting_direction == "HOLD":
            voting_direction = "NEUTRAL"
        if lstm_direction == "HOLD":
            lstm_direction = "NEUTRAL"
        if rl_direction == "HOLD":
            rl_direction = "NEUTRAL"

        try:
            # Merge logic ishga tushadi
            merged = merge_signals(
                symbol=symbol,
                timeframe=timeframe,
                voting_direction=voting_direction,
                voting_confidence=voting_confidence,
                lstm_direction=lstm_direction,
                lstm_confidence=lstm_confidence,
                shadow_win_rate=shadow_win_rate,
                shadow_trade_count=shadow_trade_count,
                stat_direction=rl_direction,
                stat_confidence=1.0,
                stat_weight_base=0.25
            )

            ts = datetime.now().isoformat()
            
            import json
            audit_trail_json = json.dumps(merged.audit_trail) if merged.audit_trail else "{}"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO shadow_merger_tracking 
                (timestamp, symbol, timeframe, voting_direction, voting_confidence, 
                 lstm_direction, lstm_confidence, merged_direction, merged_confidence, 
                 agreement, stat_weight_used, lstm_weight_used, audit_trail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ts, symbol, timeframe,
                voting_direction, voting_confidence,
                lstm_direction, lstm_confidence,
                merged.direction, merged.confidence,
                merged.agreement, merged.stat_weight_used, merged.lstm_weight_used,
                audit_trail_json
            ))
            
            conn.commit()
            
            if voting_direction != merged.direction:
                logger.info(f"[{symbol}] 🎭 MERGER SHADOW: Voting '{voting_direction}' dedi, lekin Merged '{merged.direction}' ga o'zgardi (LSTM: {lstm_direction}, W={merged.lstm_weight_used}).")

        except Exception as e:
            logger.error(f"ShadowMergerTracker yozishda xato: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def get_shadow_lstm_stats(self, symbol: str) -> dict:
        """
        Symbol bo'yicha LSTM ishtirok etgan shadow savdolar statistikasini qaytaradi.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM shadow_trade_history WHERE symbol=?", (symbol,))
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM shadow_trade_history WHERE symbol=? AND profit > 0", (symbol,))
            wins = c.fetchone()[0]
            conn.close()
            win_rate = (wins / total) if total > 0 else 0.5
            return {"win_rate": win_rate, "trade_count": total}
        except Exception as e:
            logger.warning(f"Shadow stats o'qishda xato: {e}")
            return {"win_rate": 0.5, "trade_count": 0}
