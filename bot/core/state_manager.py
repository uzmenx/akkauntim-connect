import os
import json
import logging
from typing import Dict, Any, Optional
from .db_manager import DBManager

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'trade_state.db')

class StateManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db = DBManager(db_path)
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self):
        query = """
        CREATE TABLE IF NOT EXISTS trade_states (
            ticket INTEGER PRIMARY KEY,
            state_data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.db.execute(query)
        
        query2 = """
        CREATE TABLE IF NOT EXISTS account_state (
            key TEXT PRIMARY KEY,
            value REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.db.execute(query2)

        query_symbol_state = """
        CREATE TABLE IF NOT EXISTS symbol_ai_gate_state (
            symbol TEXT PRIMARY KEY,
            last_trend_internal TEXT,
            last_bos_price REAL,
            last_regime TEXT,
            last_ai_call_at TIMESTAMP,
            last_ai_decision TEXT
        )
        """
        self.db.execute(query_symbol_state)

    def set_trade_info(self, ticket: int, info: Dict[str, Any]):
        """Mavjud ma'lumotlarni yangilari bilan merge qiladi (eski tartibni saqlash)."""
        try:
            # Mavjud holatni olish va merge qilish
            existing = self.get_trade_info(ticket) or {}
            existing.update(info)
            state_json = json.dumps(existing)
            query = """
            INSERT INTO trade_states (ticket, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticket) DO UPDATE SET 
                state_data = excluded.state_data,
                updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute(query, (ticket, state_json))
        except Exception as e:
            self.logger.error(f"Failed to set trade info for ticket {ticket}: {e}")

    def get_trade_info(self, ticket: int) -> Optional[Dict[str, Any]]:
        try:
            row = self.db.fetchone("SELECT state_data FROM trade_states WHERE ticket = ?", (ticket,))
            if row:
                return json.loads(row["state_data"])
        except Exception as e:
            self.logger.error(f"Failed to get trade info for ticket {ticket}: {e}")
        return None

    def delete_trade_info(self, ticket: int):
        try:
            self.db.execute("DELETE FROM trade_states WHERE ticket = ?", (ticket,))
        except Exception as e:
            self.logger.error(f"Failed to delete trade info for ticket {ticket}: {e}")

    def get_all_trades(self) -> Dict[int, Dict[str, Any]]:
        trades = {}
        try:
            rows = self.db.fetchall("SELECT ticket, state_data FROM trade_states")
            for row in rows:
                try:
                    trades[row["ticket"]] = json.loads(row["state_data"])
                except Exception as e:
                    self.logger.error(f"Failed to parse trade state for ticket {row['ticket']}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get all trades: {e}")
        return trades

    def get_peak_balance(self) -> Optional[float]:
        try:
            row = self.db.fetchone("SELECT value FROM account_state WHERE key = 'peak_balance'")
            if row:
                return float(row["value"])
        except Exception as e:
            self.logger.error(f"Failed to get peak balance: {e}")
        return None

    def update_peak_balance(self, balance: float):
        try:
            query = """
            INSERT INTO account_state (key, value, updated_at)
            VALUES ('peak_balance', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute(query, (balance,))
        except Exception as e:
            self.logger.error(f"Failed to update peak balance: {e}")

    def get_symbol_gate_state(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            row = self.db.fetchone(
                "SELECT symbol, last_trend_internal, last_bos_price, last_regime, "
                "last_ai_call_at, last_ai_decision FROM symbol_ai_gate_state WHERE symbol = ?",
                (symbol,)
            )
            if not row:
                return None
            return {
                "symbol": row["symbol"],
                "last_trend_internal": row["last_trend_internal"],
                "last_bos_price": row["last_bos_price"],
                "last_regime": row["last_regime"],
                "last_ai_call_at": row["last_ai_call_at"],
                "last_ai_decision": row["last_ai_decision"],
            }
        except Exception as e:
            self.logger.error(f"Failed to get gate state for {symbol}: {e}")
            return None

    def update_symbol_gate_state(self, symbol: str, trend_internal: str,
                                 bos_price: Optional[float], regime: str,
                                 ai_decision: str) -> None:
        try:
            import datetime
            now = datetime.datetime.now().isoformat()
            self.db.execute(
                """
                INSERT INTO symbol_ai_gate_state
                    (symbol, last_trend_internal, last_bos_price, last_regime, last_ai_call_at, last_ai_decision)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    last_trend_internal = excluded.last_trend_internal,
                    last_bos_price = excluded.last_bos_price,
                    last_regime = excluded.last_regime,
                    last_ai_call_at = excluded.last_ai_call_at,
                    last_ai_decision = excluded.last_ai_decision
                """,
                (symbol, trend_internal, bos_price, regime, now, ai_decision)
            )
        except Exception as e:
            self.logger.error(f"Failed to update gate state for {symbol}: {e}")
