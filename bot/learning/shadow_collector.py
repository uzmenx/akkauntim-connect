import sqlite3
import json
import logging
import os
import numpy as np
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ShadowStateCollector:
    """
    Shadow AI Data Pipeline
    
    Har bir shamning holatini, barcha indikatorlar va bozor strukturasi (SMC) 
    bilan birgalikda orqa fonda saqlab boruvchi kollektor.
    Bu ma'lumotlar kelajakda Deep Learning (LSTM) va RL (Qora Quti) ni
    o'qitish uchun 'Dataset' bo'lib xizmat qiladi.
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
                CREATE TABLE IF NOT EXISTS shadow_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    price_open REAL,
                    price_high REAL,
                    price_low REAL,
                    price_close REAL,
                    tick_volume REAL,
                    smc_context TEXT,
                    indicators TEXT,
                    market_regime TEXT,
                    ai_decision TEXT
                )
            ''')
            
            # Kelajakda bashorat (label) bilan solishtirish uchun index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shadow_symbol_time ON shadow_states(symbol, timestamp)')
            
            conn.commit()
        except Exception as e:
            logger.error(f"ShadowStateCollector DB init xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def record_state(self, symbol: str, timeframe: str, candle: Dict[str, float], 
                     smc_context: Dict[str, Any], indicators: Dict[str, Any], 
                     market_regime: str, ai_decision: str = "HOLD"):
        """
        Joriy bozor holatini yozib qoldirish.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Sham vaqtini ishlatish (kompyuter vaqti emas)
            candle_time = candle.get('time', None)
            if candle_time:
                try:
                    ts = str(candle_time)
                except:
                    ts = datetime.now().isoformat()
            else:
                ts = datetime.now().isoformat()
            
            # NumPy tiplarini oddiy Python tipiga aylantirish (JSON uchun)
            def safe_json(obj):
                if obj is None:
                    return "{}"
                try:
                    return json.dumps(obj, ensure_ascii=False, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
                except:
                    return "{}"
            
            cursor.execute('''
                INSERT INTO shadow_states 
                (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ts,
                symbol,
                timeframe,
                float(candle.get('open', 0.0)),
                float(candle.get('high', 0.0)),
                float(candle.get('low', 0.0)),
                float(candle.get('close', 0.0)),
                float(candle.get('tick_volume', 0.0)),
                safe_json(smc_context),
                safe_json(indicators),
                market_regime,
                ai_decision
            ))
            
            conn.commit()
            
            # Har 10 ta yozuvda bir marta UI uchun statsni yangilaymiz (har siklda emas)
            if not hasattr(self, '_write_count'):
                self._write_count = 0
            self._write_count += 1
            if self._write_count % 10 == 0:
                self.export_stats_for_ui()
            
        except Exception as e:
            logger.error(f"Shadow state saqlashda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def export_stats_for_ui(self):
        """
        Baza holatini (Jami qatorlar, h.k.) public/shadow_stats.json ga chiqaradi.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM shadow_states")
            total_rows = cursor.fetchone()[0]
            
            # Qilingan qarorlar (BUY, SELL, LIMIT lar ham) soni
            cursor.execute("SELECT COUNT(*) FROM shadow_states WHERE ai_decision IN ('BUY', 'SELL', 'LIMIT_BUY', 'LIMIT_SELL', 'BUY_LIMIT', 'SELL_LIMIT')")
            trade_decisions = cursor.fetchone()[0]
            
            # Haqiqiy Win Rate: shadow_trade_history dagi natijalardan
            real_win_rate = 0
            try:
                cursor.execute("SELECT COUNT(*) FROM shadow_trade_history WHERE profit > 0")
                winning_trades = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM shadow_trade_history")
                closed_trades = cursor.fetchone()[0]
                
                if closed_trades > 0:
                    real_win_rate = int((winning_trades / closed_trades) * 100)
            except:
                real_win_rate = 0
            
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Haqiqiy "Bilimlar" sonini bazadan olish
            real_knowledge = 0
            try:
                mem_db = os.path.join(root_dir, 'ai_memory.db')
                if os.path.exists(mem_db):
                    with sqlite3.connect(mem_db) as m_conn:
                        real_knowledge += m_conn.execute("SELECT COUNT(*) FROM ai_lessons").fetchone()[0]
            except Exception:
                pass
                
            try:
                strat_db = os.path.join(root_dir, 'strategist_db.sqlite')
                if os.path.exists(strat_db):
                    with sqlite3.connect(strat_db) as s_conn:
                        real_knowledge += s_conn.execute("SELECT COUNT(*) FROM strategy_insights").fetchone()[0]
            except Exception:
                pass
            
            stats = {
                "total_shadow_trades": trade_decisions,
                "dataset_size": total_rows,
                "overall_win_rate": real_win_rate, 
                "knowledge_points": real_knowledge
            }
            
            public_dir = os.path.join(root_dir, 'public')
            if not os.path.exists(public_dir):
                try:
                    os.makedirs(public_dir)
                except:
                    pass
                    
            with open(os.path.join(public_dir, 'shadow_stats.json'), 'w') as f:
                json.dump(stats, f)
                
        except Exception as e:
            logger.error(f"Shadow stats eksportida xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
