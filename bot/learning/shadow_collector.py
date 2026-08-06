import sqlite3
import json
import logging
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

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
                    ai_decision TEXT,
                    f12_features TEXT
                )
            ''')
            
            # Yangi ustunlarni eski bazalarga ham qo'shish
            for col_def in [
                ('f12_features', 'TEXT'),
                ('outcome_label', 'TEXT'),     # WIN / LOSS / BREAKEVEN
                ('outcome_pnl', 'REAL'),        # Foyda/zarar qiymati
                ('labeled_at', 'TEXT'),          # Qachon belgilangani
            ]:
                try:
                    cursor.execute(f'ALTER TABLE shadow_states ADD COLUMN {col_def[0]} {col_def[1]}')
                except Exception:
                    pass
            
            # Kelajakda bashorat (label) bilan solishtirish uchun index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shadow_symbol_time ON shadow_states(symbol, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shadow_sym_tf_ts ON shadow_states(symbol, timeframe, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shadow_decision ON shadow_states(ai_decision)')
            
            conn.commit()
        except Exception as e:
            logger.error(f"ShadowStateCollector DB init xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def _compute_12_features_for_candle(self, symbol: str, timeframe: str, candle: Dict[str, Any], recent_candles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Joriy sham uchun 12 ta xususiyatni (OHLCV, RSI-14, ATR-14, MA-diff, Momentum, Vol_change, Body_ratio, Time_sin)
        aniq va xatolarga chidamli tarzda hisoblash.
        """
        from bot.learning.features import compute_12_features, compute_12_features_dict

        candle_list = []
        if recent_candles and isinstance(recent_candles, list) and len(recent_candles) > 0:
            candle_list = list(recent_candles)
            if candle and (not candle_list or candle_list[-1].get('time') != candle.get('time')):
                candle_list.append(candle)
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                query = "SELECT timestamp as time, price_open as open, price_high as high, price_low as low, price_close as close, tick_volume as volume FROM shadow_states WHERE symbol = ? AND timeframe = ? ORDER BY timestamp DESC LIMIT 25"
                df_prev = pd.read_sql_query(query, conn, params=(symbol, timeframe))
                conn.close()
                if not df_prev.empty:
                    df_prev = df_prev.iloc[::-1]
                    candle_list = df_prev.to_dict('records')
            except Exception as e:
                logger.debug(f"DB'dan shamlar o'qishda xatolik: {e}")

            if candle:
                candle_list.append(candle)

        if candle_list:
            return compute_12_features_dict(candle_list)

        return compute_12_features_dict(candle or {})


    def record_state(self, symbol: str, timeframe: str, candle: Dict[str, float], 
                     smc_context: Dict[str, Any], indicators: Dict[str, Any], 
                     market_regime: str, ai_decision: str = "HOLD",
                     recent_candles: Optional[List[Dict[str, Any]]] = None):
        """
        Joriy bozor holatini va 12 ta institutional xususiyatni yozib qoldirish.
        """
        try:
            # Zero / corrupt candle validation
            open_p = float(candle.get('open', 0.0) or 0.0)
            high_p = float(candle.get('high', 0.0) or 0.0)
            low_p = float(candle.get('low', 0.0) or 0.0)
            close_p = float(candle.get('close', 0.0) or 0.0)

            if open_p <= 0 or high_p <= 0 or low_p <= 0 or close_p <= 0:
                logger.warning(f"[{symbol}] Noto'g'ri/nol narxli sham shadow_states ga yozilmadi: {candle}")
                return

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
            
            # 12 ta xususiyatni hisoblash
            f12_dict = self._compute_12_features_for_candle(symbol, timeframe, candle, recent_candles)
            
            # indicators obyektini 12 ta feature bilan boyitish
            indicators_enriched = dict(indicators) if isinstance(indicators, dict) else {}
            indicators_enriched["f12_features"] = f12_dict

            cursor.execute('''
                INSERT INTO shadow_states 
                (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision, f12_features)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ts,
                symbol,
                timeframe,
                float(candle.get('open', 0.0)),
                float(candle.get('high', 0.0)),
                float(candle.get('low', 0.0)),
                float(candle.get('close', 0.0)),
                float(candle.get('tick_volume', candle.get('volume', 0.0))),
                safe_json(smc_context),
                safe_json(indicators_enriched),
                market_regime,
                ai_decision,
                safe_json(f12_dict)
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

    def label_past_states(self, symbol: str, timeframe: str, direction: str, 
                          pnl: float, trade_open_time: str, trade_close_time: str):
        """
        Savdo yopilganda, o'sha savdo davridagi shadow_states qatorlarini belgilash.
        Bu LSTM uchun supervised learning label'lari bo'ladi.
        
        Args:
            symbol: Valyuta juftligi (EURUSD)
            timeframe: Vaqt oynasi (H1)
            direction: Savdo yo'nalishi (BUY/SELL)
            pnl: Foyda/zarar ($)
            trade_open_time: Savdo ochilgan vaqt (ISO format)
            trade_close_time: Savdo yopilgan vaqt (ISO format)
        """
        try:
            # Outcome label aniqlash
            if pnl > 0:
                outcome = "WIN"
            elif pnl < 0:
                outcome = "LOSS"
            else:
                outcome = "BREAKEVEN"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now_iso = datetime.now().isoformat()
            
            # Savdo ochilishidan oldingi N ta shamni ham label'laymiz
            # (chunki qaror shu shamlar asosida qilingan)
            cursor.execute('''
                UPDATE shadow_states 
                SET outcome_label = ?, outcome_pnl = ?, labeled_at = ?
                WHERE symbol = ? AND timeframe = ? 
                AND timestamp >= ? AND timestamp <= ?
                AND outcome_label IS NULL
            ''', (outcome, pnl, now_iso, symbol, timeframe, 
                  trade_open_time, trade_close_time))
            
            updated = cursor.rowcount
            
            # Agar savdo ochilish vaqtidagi shamlar topilmasa,
            # eng yaqin 5 ta shamni belgilaymiz
            if updated == 0:
                cursor.execute('''
                    UPDATE shadow_states 
                    SET outcome_label = ?, outcome_pnl = ?, labeled_at = ?
                    WHERE id IN (
                        SELECT id FROM shadow_states 
                        WHERE symbol = ? AND timeframe = ? 
                        AND outcome_label IS NULL
                        AND timestamp <= ?
                        ORDER BY timestamp DESC LIMIT 5
                    )
                ''', (outcome, pnl, now_iso, symbol, timeframe, trade_close_time))
                updated = cursor.rowcount
            
            conn.commit()
            logger.info(f"Shadow states labeled: {updated} rows → {outcome} ({pnl:.2f}) [{symbol} {timeframe}]")
            
        except Exception as e:
            logger.error(f"Shadow states label qilishda xatolik: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def get_labeled_count(self, symbol: Optional[str] = None) -> int:
        """
        Labeled (outcome_label != NULL) bo'lgan shadow_states qatorlari sonini qaytaradi.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if symbol:
                cursor.execute(
                    "SELECT COUNT(*) FROM shadow_states WHERE outcome_label IS NOT NULL AND symbol = ?",
                    (symbol,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM shadow_states WHERE outcome_label IS NOT NULL")
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Labeled count olishda xatolik: {e}")
            return 0
        finally:
            if 'conn' in locals():
                conn.close()

    def get_label_stats(self) -> Dict[str, Any]:
        """
        Labeled ma'lumotlar statistikasini qaytaradi.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM shadow_states")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM shadow_states WHERE outcome_label IS NOT NULL")
            labeled = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT outcome_label, COUNT(*) FROM shadow_states "
                "WHERE outcome_label IS NOT NULL GROUP BY outcome_label"
            )
            by_label = dict(cursor.fetchall())
            
            return {
                "total_states": total,
                "labeled_states": labeled,
                "unlabeled_states": total - labeled,
                "label_ratio": round(labeled / max(total, 1), 3),
                "by_label": by_label
            }
        except Exception as e:
            logger.error(f"Label stats olishda xatolik: {e}")
            return {}
        finally:
            if 'conn' in locals():
                conn.close()

