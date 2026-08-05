"""
harmonic/manager.py
===================
SQLite-based memory system for Harmonic Patterns.
Harmonic XABCD va boshqa deteksiya qilingan patternlarni bazada saqlash va boshqarish moduli.
BaseStrategyManager klassidan vorislik olgan.
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any
from bot.strategy.base_manager import BaseStrategyManager

class HarmonicPatternManager(BaseStrategyManager):
    def __init__(self, db_path: str = "harmonic_patterns.db"):
        super().__init__(db_path=db_path, table_name="harmonic_patterns")

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS harmonic_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    x_price REAL,
                    x_time TEXT,
                    x_bar_index INTEGER,
                    a_price REAL,
                    a_time TEXT,
                    a_bar_index INTEGER,
                    b_price REAL,
                    b_time TEXT,
                    b_bar_index INTEGER,
                    c_price REAL,
                    c_time TEXT,
                    c_bar_index INTEGER,
                    d_price REAL,
                    d_time TEXT,
                    d_bar_index INTEGER,
                    bars_since_d INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, pattern_name, direction, d_time, d_price)
                )
            ''')
            conn.commit()

    def save_patterns(self, symbol: str, timeframe: str, harmonic_result: dict) -> int:
        """
        Harmonic Engine natijalarini SQLite bazaga saqlaydi.
        Duplikat bo'lsa IGNORE qiladi. Yangi kiritilgan yozuvlar sonini qaytaradi.
        """
        inserted_count = 0
        if not harmonic_result:
            return 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Active pattern
            active_pat = harmonic_result.get("active_pattern")
            if active_pat:
                p_name = active_pat.get("name", "Unknown")
                direction = active_pat.get("direction", "Neutral")
                xabcd_coords = active_pat.get("xabcd_coords", {})
                bars_since_d = active_pat.get("bars_since_d", 0)

                x_info = xabcd_coords.get("x", {})
                a_info = xabcd_coords.get("a", {})
                b_info = xabcd_coords.get("b", {})
                c_info = xabcd_coords.get("c", {})
                d_info = xabcd_coords.get("d", {})

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO harmonic_patterns (
                            symbol, timeframe, pattern_name, direction,
                            x_price, x_time, x_bar_index,
                            a_price, a_time, a_bar_index,
                            b_price, b_time, b_bar_index,
                            c_price, c_time, c_bar_index,
                            d_price, d_time, d_bar_index,
                            bars_since_d, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                    ''', (
                        symbol, timeframe, p_name, direction,
                        x_info.get("price"), x_info.get("time"), x_info.get("bar_index"),
                        a_info.get("price"), a_info.get("time"), a_info.get("bar_index"),
                        b_info.get("price"), b_info.get("time"), b_info.get("bar_index"),
                        c_info.get("price"), c_info.get("time"), c_info.get("bar_index"),
                        d_info.get("price"), d_info.get("time"), d_info.get("bar_index"),
                        bars_since_d, datetime.now(timezone.utc).isoformat()
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += cursor.rowcount
                except sqlite3.Error as e:
                    print(f"Harmonic Pattern Save Error: {e}")

            # 2. All detected patterns list
            detected_patterns = harmonic_result.get("all_detected_patterns", [])
            for det in detected_patterns:
                p_name = det.get("name", "Unknown")
                direction = det.get("direction", "Neutral")
                d_price = det.get("d_price")
                d_time = det.get("time")
                d_bar_index = det.get("bar_index")

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO harmonic_patterns (
                            symbol, timeframe, pattern_name, direction,
                            d_price, d_time, d_bar_index,
                            status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'history', ?)
                    ''', (
                        symbol, timeframe, p_name, direction,
                        d_price, d_time, d_bar_index,
                        datetime.now(timezone.utc).isoformat()
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += cursor.rowcount
                except sqlite3.Error as e:
                    print(f"Harmonic Detected Pattern Save Error: {e}")

            conn.commit()

        return inserted_count

    def get_active_patterns(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        return self.get_active(symbol, timeframe)

    def get_all_patterns(self, symbol: str, timeframe: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_recent(symbol, timeframe, limit=limit)

    def update_mitigations(self, symbol: str, timeframe: str, current_high: float, current_low: float) -> int:
        """
        Harmonic patternlar uchun narxga asoslangan invalidatsiya.
        Bullish: agar current_low < d_price * 0.995 (0.5% pastga) bo'lsa invalid
        Bearish: agar current_high > d_price * 1.005 (0.5% tepaga) bo'lsa invalid
        """
        mitigated_count = super().update_mitigations(symbol, timeframe, current_high, current_low)
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT id, direction, d_price FROM {self.table_name} WHERE symbol = ? AND timeframe = ? AND status IN ('active', 'fresh')", (symbol, timeframe))
                fresh = cursor.fetchall()
                for row in fresh:
                    is_invalid = False
                    if row["direction"].upper() == "BULLISH" and current_low < row["d_price"] * 0.995:
                        is_invalid = True
                    elif row["direction"].upper() == "BEARISH" and current_high > row["d_price"] * 1.005:
                        is_invalid = True
                    
                    if is_invalid:
                        cursor.execute(f"UPDATE {self.table_name} SET status = 'stale' WHERE id = ?", (row["id"],))
                        mitigated_count += 1
                conn.commit()
        except sqlite3.Error as e:
            print(f"Harmonic Update Mitigations Error: {e}")
        return mitigated_count
