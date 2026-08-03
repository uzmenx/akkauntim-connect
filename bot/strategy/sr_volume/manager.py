"""
sr_volume/manager.py
====================
SQLite-based memory system for SR Volume (Support & Resistance) Zones.
Hajm (Volume) asosida aniqlangan support va resistance zonalarini saqlash va ularning holatini kuzatish moduli.
BaseStrategyManager klassidan vorislik olgan.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from bot.strategy.base_manager import BaseStrategyManager

class SRVolumeZoneManager(BaseStrategyManager):
    def __init__(self, db_path: str = "sr_volume_zones.db"):
        super().__init__(db_path=db_path, table_name="sr_volume_zones")

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sr_volume_zones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    zone_type TEXT NOT NULL,
                    top_price REAL NOT NULL,
                    bottom_price REAL NOT NULL,
                    bar_index INTEGER,
                    event_time TEXT,
                    signal TEXT DEFAULT 'NEUTRAL',
                    confidence REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'fresh',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, zone_type, event_time, top_price, bottom_price)
                )
            ''')
            conn.commit()

    def save_zones(self, symbol: str, timeframe: str, sr_result: dict) -> int:
        """
        SR Volume Engine natijalaridagi support va resistance zonalarni bazaga saqlaydi.
        Duplikat bo'lsa IGNORE qiladi. Yangi yozuvlar sonini qaytaradi.
        """
        inserted_count = 0
        if not sr_result:
            return 0

        signal = sr_result.get("signal", "NEUTRAL")
        confidence = sr_result.get("confidence", 0.0)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Support zone
            sup_zone = sr_result.get("support_zone")
            if sup_zone and isinstance(sup_zone, dict):
                top_p = sup_zone.get("top")
                bot_p = sup_zone.get("bottom")
                b_idx = sup_zone.get("bar_index")
                e_time = sup_zone.get("time")

                if top_p is not None and bot_p is not None:
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO sr_volume_zones (
                                symbol, timeframe, zone_type, top_price, bottom_price,
                                bar_index, event_time, signal, confidence, status, created_at
                            ) VALUES (?, ?, 'support', ?, ?, ?, ?, ?, ?, 'fresh', ?)
                        ''', (
                            symbol, timeframe, top_p, bot_p,
                            b_idx, e_time, signal, confidence, datetime.utcnow().isoformat()
                        ))
                        if cursor.rowcount > 0:
                            inserted_count += cursor.rowcount
                    except sqlite3.Error as e:
                        print(f"SR Volume Support Save Error: {e}")

            # 2. Resistance zone
            res_zone = sr_result.get("resistance_zone")
            if res_zone and isinstance(res_zone, dict):
                top_p = res_zone.get("top")
                bot_p = res_zone.get("bottom")
                b_idx = res_zone.get("bar_index")
                e_time = res_zone.get("time")

                if top_p is not None and bot_p is not None:
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO sr_volume_zones (
                                symbol, timeframe, zone_type, top_price, bottom_price,
                                bar_index, event_time, signal, confidence, status, created_at
                            ) VALUES (?, ?, 'resistance', ?, ?, ?, ?, ?, ?, 'fresh', ?)
                        ''', (
                            symbol, timeframe, top_p, bot_p,
                            b_idx, e_time, signal, confidence, datetime.utcnow().isoformat()
                        ))
                        if cursor.rowcount > 0:
                            inserted_count += cursor.rowcount
                    except sqlite3.Error as e:
                        print(f"SR Volume Resistance Save Error: {e}")

            conn.commit()

        return inserted_count

    def get_active_zones(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        return self.get_active(symbol, timeframe)

    def get_all_zones(self, symbol: str, timeframe: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_recent(symbol, timeframe, limit=limit)
