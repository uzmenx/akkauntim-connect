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
