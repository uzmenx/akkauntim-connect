import sqlite3
import json
import hashlib
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class DecisionLogger:
    def __init__(self, db_path: str = 'decisions_log.db'):
        self.db_path = db_path
        self.init_schema()
        
    def init_schema(self):
        """Creates table and runs migrations."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    pair TEXT,
                    timeframe TEXT,
                    context_json TEXT,
                    prompt TEXT,
                    ai_response TEXT,
                    final_decision TEXT,
                    risk_pct REAL
                )
            ''')
            conn.commit()
            
            # Cache ustunini qo'shish
            try:
                cursor.execute("ALTER TABLE ai_decisions ADD COLUMN context_hash TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass # Allaqachon mavjud
                
            # Tokenlar va cost ustunlarini qo'shish
            for col in ["input_tokens INTEGER", "output_tokens INTEGER", "cost REAL"]:
                try:
                    cursor.execute(f"ALTER TABLE ai_decisions ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass
            conn.commit()
                
            # Shadow Learner ustunlarini qo'shish
            for col in ["ticket INTEGER", "outcome_profit REAL", "outcome_label TEXT", "closed_at TEXT", "shadow_prediction TEXT", "shadow_confidence REAL"]:
                try:
                    cursor.execute(f"ALTER TABLE ai_decisions ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass
            conn.commit()
                
            # Used insight IDs ustunini qo'shish (RAG feedback uchun)
            try:
                cursor.execute("ALTER TABLE ai_decisions ADD COLUMN used_insight_ids TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
                
            # Close mechanism ustunini qo'shish (Qora quti MVP)
            try:
                cursor.execute("ALTER TABLE ai_decisions ADD COLUMN close_mechanism TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE ai_decisions ADD COLUMN news_coverage_gap BOOLEAN")
                conn.commit()
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE ai_decisions ADD COLUMN news_strategy_type TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
                
        except Exception as e:
            logger.error(f"Error initializing DB schema: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def log(self, pair: str, timeframe: str, context: Dict[str, Any], prompt: str, 
            response: Any, decision: str, risk_pct: float, 
            hash_val: Optional[str] = None, tokens: Optional[Dict[str, int]] = None, 
            cost: Optional[float] = None, ticket: Optional[int] = None,
            used_insight_ids: Optional[str] = None,
            news_coverage_gap: Optional[bool] = None,
            news_strategy_type: Optional[str] = None):
        """Logs a trading decision to SQLite."""
        
        input_tokens = tokens.get("input_tokens") if tokens else None
        output_tokens = tokens.get("output_tokens") if tokens else None
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ai_decisions 
                (timestamp, pair, timeframe, context_json, prompt, ai_response, final_decision, risk_pct, context_hash, input_tokens, output_tokens, cost, ticket, used_insight_ids, news_coverage_gap, news_strategy_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                pair,
                timeframe,
                json.dumps(context, ensure_ascii=False, default=str),
                prompt,
                json.dumps(response, ensure_ascii=False, default=str) if isinstance(response, dict) else str(response),
                decision,
                risk_pct,
                hash_val,
                input_tokens,
                output_tokens,
                cost,
                ticket,
                used_insight_ids,
                news_coverage_gap,
                news_strategy_type
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging decision: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def update_outcome(self, ticket: int, profit: float, close_mechanism: Optional[str] = None) -> None:
        """Updates the trade outcome for shadow learning, plus close_mechanism tag."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            cursor = conn.cursor()
            
            if profit > 0:
                outcome_label = 'WIN'
            elif profit == 0:
                outcome_label = 'BREAKEVEN'
            else:
                outcome_label = 'LOSS'
            
            closed_at = datetime.now().isoformat()
            
            cursor.execute('''
                UPDATE ai_decisions 
                SET outcome_profit = ?, outcome_label = ?, closed_at = ?, close_mechanism = ?
                WHERE ticket = ?
            ''', (profit, outcome_label, closed_at, close_mechanism, ticket))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating outcome for ticket {ticket}: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def get_insight_ids_for_ticket(self, ticket: int) -> List[str]:
        """Berilgan ticket uchun ishlatilgan insight ID larni qaytarish."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT used_insight_ids FROM ai_decisions WHERE ticket = ? ORDER BY id DESC LIMIT 1",
                (ticket,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return []
        except Exception as e:
            logger.error(f"Insight IDs olishda xatolik: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def get_last_hash(self, pair: str) -> Optional[str]:
        """Gets the hash of the last recorded decision for caching."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            cursor = conn.cursor()
            cursor.execute("SELECT context_hash FROM ai_decisions WHERE pair = ? ORDER BY id DESC LIMIT 1", (pair,))
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting last hash: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def get_last_cached_response(self, pair: str, hash_val: str) -> Optional[Dict[str, Any]]:
        """Gets the last cached response if the hash matches."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            cursor = conn.cursor()
            cursor.execute("SELECT context_hash, ai_response FROM ai_decisions WHERE pair = ? ORDER BY id DESC LIMIT 1", (pair,))
            row = cursor.fetchone()
            
            if row and row[0] == hash_val and row[1]:
                return json.loads(row[1])
            return None
        except Exception as e:
            logger.error(f"Cache o'qishda xatolik: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def create_state_hash(self, context: Dict[str, Any]) -> str:
        """SMC, Pattern, News va Risk holatidan iborat o'zgarmas holat xeshini (hash) yaratadi. Narx e'tiborga olinmaydi."""
        news = (context.get('news_context') or {})
        next_event = (news.get('next_event') or {})
        smc = (context.get('smc_structure') or {})
        risk = (context.get('risk_manager') or {})
        
        state = {
            "vote": (context.get('voting_result') or {}).get('signal'),
            "vote_risk": (context.get('voting_result') or {}).get('risk_pct'),
            "smc_trend": smc.get('trend'),
            "smc_events": smc.get('events'),
            "pat_signal": (context.get('harmonic_pattern') or {}).get('signal'),
            "news_status": news.get('status'),
            "news_event": next_event.get('name'),
            "news_time": next_event.get('minutes_to_release'),
            "drawdown": risk.get('daily_drawdown_pct')
        }
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.md5(state_str.encode('utf-8')).hexdigest()
