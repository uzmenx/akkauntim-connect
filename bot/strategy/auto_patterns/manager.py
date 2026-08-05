"""
auto_patterns/manager.py
========================
SQLite-based memory system for Auto Patterns (Chart Patterns).
Double Top, Double Bottom, Head & Shoulders va boshqa grafik patternlarni saqlash va boshqarish moduli.
BaseStrategyManager klassidan vorislik olgan.
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from bot.strategy.base_manager import BaseStrategyManager

class AutoPatternManager(BaseStrategyManager):
    def __init__(self, db_path: str = "auto_patterns.db"):
        super().__init__(db_path=db_path, table_name="auto_patterns")

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auto_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    res_slope REAL,
                    sup_slope REAL,
                    pivots_json TEXT,
                    pattern_points_json TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, pattern_name, signal, created_at)
                )
            ''')
            conn.commit()

    def save_pattern(self, symbol: str, timeframe: str, pattern_result: dict) -> int:
        """
        Auto Pattern Engine natijalarini bazaga saqlaydi.
        Pattern bo'lmasa ("None" bo'lsa) saqlamaydi. Duplikat IGNORE qilinadi.
        """
        inserted_count = 0
        if not pattern_result:
            return 0

        pattern_name = pattern_result.get("pattern_name", "None")
        if pattern_name == "None":
            return 0

        signal = pattern_result.get("signal", "NEUTRAL")
        confidence = pattern_result.get("confidence", 0.0)
        slopes = pattern_result.get("slopes", {})
        res_slope = slopes.get("res")
        sup_slope = slopes.get("sup")

        pivots = pattern_result.get("pivots", [])
        pattern_points = pattern_result.get("pattern_points", {})

        pivots_json = json.dumps(pivots) if pivots else None
        pattern_points_json = json.dumps(pattern_points) if pattern_points else None

        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO auto_patterns (
                        symbol, timeframe, pattern_name, signal, confidence,
                        res_slope, sup_slope, pivots_json, pattern_points_json,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                ''', (
                    symbol, timeframe, pattern_name, signal, confidence,
                    res_slope, sup_slope, pivots_json, pattern_points_json,
                    datetime.now(timezone.utc).isoformat()
                ))
                if cursor.rowcount > 0:
                    inserted_count += cursor.rowcount
            except sqlite3.Error as e:
                print(f"Auto Pattern Save Error: {e}")

            conn.commit()

        return inserted_count

    def _parse_json_fields(self, pat_dict: Dict[str, Any]) -> Dict[str, Any]:
        if pat_dict.get("pivots_json"):
            try:
                pat_dict["pivots"] = json.loads(pat_dict["pivots_json"])
            except Exception:
                pat_dict["pivots"] = []
        if pat_dict.get("pattern_points_json"):
            try:
                pat_dict["pattern_points"] = json.loads(pat_dict["pattern_points_json"])
            except Exception:
                pat_dict["pattern_points"] = {}
        return pat_dict

    def get_active_patterns(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        raw_patterns = self.get_active(symbol, timeframe)
        return [self._parse_json_fields(pat) for pat in raw_patterns]

    def get_all_patterns(self, symbol: str, timeframe: str, limit: int = 50) -> List[Dict[str, Any]]:
        raw_patterns = self.get_recent(symbol, timeframe, limit=limit)
        return [self._parse_json_fields(pat) for pat in raw_patterns]

    def update_mitigations(self, symbol: str, timeframe: str, current_high: float, current_low: float) -> int:
        """
        Auto Patterns uchun narxga asoslangan invalidatsiya.
        Agar signal BUY bo'lsa va narx pattern eng past nuqtasidan (pivot) 0.5% tushib ketsa -> invalid
        Agar signal SELL bo'lsa va narx pattern eng baland nuqtasidan (pivot) 0.5% oshib ketsa -> invalid
        """
        mitigated_count = super().update_mitigations(symbol, timeframe, current_high, current_low)
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT id, signal, pivots_json FROM {self.table_name} WHERE symbol = ? AND timeframe = ? AND status = 'active'", (symbol, timeframe))
                fresh = cursor.fetchall()
                for row in fresh:
                    is_invalid = False
                    signal = row["signal"].upper()
                    
                    try:
                        pivots = json.loads(row["pivots_json"]) if row["pivots_json"] else []
                    except:
                        pivots = []
                        
                    if pivots:
                        prices = [p["price"] for p in pivots if "price" in p]
                        if prices:
                            min_p = min(prices)
                            max_p = max(prices)
                            if signal == "BUY" and current_low < min_p * 0.995:
                                is_invalid = True
                            elif signal == "SELL" and current_high > max_p * 1.005:
                                is_invalid = True
                    
                    if is_invalid:
                        cursor.execute(f"UPDATE {self.table_name} SET status = 'stale' WHERE id = ?", (row["id"],))
                        mitigated_count += 1
                conn.commit()
        except sqlite3.Error as e:
            print(f"Auto Pattern Update Mitigations Error: {e}")
        return mitigated_count
