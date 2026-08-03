"""
wyckoff/manager.py
==================
SQLite-based memory system for Wyckoff Events & Phases.
Wyckoff Spring, Upthrust, SOS, SOW hodisalari hamda savdo diapazonlarini bazada saqlash moduli.
BaseStrategyManager klassidan vorislik olgan.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from bot.strategy.base_manager import BaseStrategyManager

class WyckoffEventManager(BaseStrategyManager):
    def __init__(self, db_path: str = "wyckoff_events.db"):
        super().__init__(db_path=db_path, table_name="wyckoff_events")

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wyckoff_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_bar_index INTEGER,
                    event_time TEXT,
                    price REAL,
                    level_broken REAL,
                    range_top REAL,
                    range_bottom REAL,
                    momentum_sign TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, event_type, event_time, price)
                )
            ''')
            conn.commit()

    def save_events(self, symbol: str, timeframe: str, wyckoff_result: dict) -> int:
        """
        Wyckoff Engine natijalaridagi Spring / Upthrust / SOS / SOW va Range ma'lumotlarini saqlaydi.
        Duplikat bo'lsa IGNORE qiladi. Yangi yozuvlar sonini qaytaradi.
        """
        inserted_count = 0
        if not wyckoff_result:
            return 0

        phase = wyckoff_result.get("phase", "Unknown")
        tr_data = wyckoff_result.get("trading_range", {})
        range_top = tr_data.get("top")
        range_bottom = tr_data.get("bottom")
        momentum_sign = wyckoff_result.get("momentum_sign", "None")

        # 1. Spring / Upthrust Hodisalari
        event_details = wyckoff_result.get("event_details", {})
        event_type = event_details.get("type", wyckoff_result.get("spring_upthrust", "None"))

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if event_type and event_type != "None":
                ev_bar_idx = event_details.get("event_bar_index", event_details.get("bar_index"))
                ev_time = event_details.get("event_time", event_details.get("time"))
                ev_price = event_details.get("price")
                level_broken = event_details.get("level_broken")

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO wyckoff_events (
                            symbol, timeframe, phase, event_type,
                            event_bar_index, event_time, price, level_broken,
                            range_top, range_bottom, momentum_sign, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                    ''', (
                        symbol, timeframe, phase, event_type,
                        ev_bar_idx, ev_time, ev_price, level_broken,
                        range_top, range_bottom, momentum_sign, datetime.utcnow().isoformat()
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += cursor.rowcount
                except sqlite3.Error as e:
                    print(f"Wyckoff Event Save Error: {e}")

            # 2. Momentum Details (SOS / SOW)
            mom_details = wyckoff_result.get("momentum_details", {})
            mom_type = mom_details.get("type", momentum_sign)
            if mom_type and mom_type != "None" and mom_type != event_type:
                m_bar_idx = mom_details.get("event_bar_index", mom_details.get("bar_index"))
                m_time = mom_details.get("event_time", mom_details.get("time"))
                m_price = mom_details.get("price")

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO wyckoff_events (
                            symbol, timeframe, phase, event_type,
                            event_bar_index, event_time, price, level_broken,
                            range_top, range_bottom, momentum_sign, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                    ''', (
                        symbol, timeframe, phase, mom_type,
                        m_bar_idx, m_time, m_price, None,
                        range_top, range_bottom, momentum_sign, datetime.utcnow().isoformat()
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += cursor.rowcount
                except sqlite3.Error as e:
                    print(f"Wyckoff Momentum Event Save Error: {e}")

            conn.commit()

        return inserted_count

    def get_active_events(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        return self.get_active(symbol, timeframe)

    def get_all_events(self, symbol: str, timeframe: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_recent(symbol, timeframe, limit=limit)

    def update_mitigations(self, symbol: str, timeframe: str, current_high: float, current_low: float) -> int:
        """
        Wyckoff eventlar uchun narxga asoslangan invalidatsiya.
        Spring / SOS (Bullish): agar current_low < price * 0.995 (0.5% pastga)
        Upthrust / SOW (Bearish): agar current_high > price * 1.005 (0.5% tepaga)
        """
        mitigated_count = super().update_mitigations(symbol, timeframe, current_high, current_low)
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT id, event_type, price FROM {self.table_name} WHERE symbol = ? AND timeframe = ? AND status = 'active'", (symbol, timeframe))
                fresh = cursor.fetchall()
                for row in fresh:
                    is_invalid = False
                    ev = row["event_type"].lower()
                    if ev in ("spring", "sos", "jac", "buy") and current_low < row["price"] * 0.995:
                        is_invalid = True
                    elif ev in ("upthrust", "sow", "utad", "sell") and current_high > row["price"] * 1.005:
                        is_invalid = True
                    
                    if is_invalid:
                        cursor.execute(f"UPDATE {self.table_name} SET status = 'stale' WHERE id = ?", (row["id"],))
                        mitigated_count += 1
                conn.commit()
        except sqlite3.Error as e:
            print(f"Wyckoff Update Mitigations Error: {e}")
        return mitigated_count
