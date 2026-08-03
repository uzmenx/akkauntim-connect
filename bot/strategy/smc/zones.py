"""
zone_manager.py
===============
SQLite-based memory system for SMC Engine.
Tarixiy OB va FVG zonalarni bazada saqlash va ularning 
jonli narx bilan "mitigated" (ishlatilgan) holatini kuzatish moduli.
"""

import sqlite3
from typing import List, Dict, Any

class ZoneManager:
    def __init__(self, db_path: str = "smc_zones.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            
            # Zonalar jadvalini yaratish. Duplikat yozmaslik uchun UNIQUE ishlatamiz.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS zones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    zone_type TEXT,     -- "ob" yoki "fvg"
                    direction TEXT,     -- "demand" yoki "supply"
                    level TEXT,         -- "Major" yoki "Minor" (OB uchun)
                    origin TEXT,        -- "BoS", "ChoCh Main" (OB uchun)
                    top_price REAL,
                    bottom_price REAL,
                    status TEXT,        -- "fresh", "mitigated"
                    creation_time TEXT, -- yaratilgan vaqti (string formatda)
                    bar_index INTEGER,  -- sham indeksi
                    UNIQUE(symbol, timeframe, zone_type, direction, level, creation_time)
                )
            ''')
            conn.commit()

    def save_zones(self, symbol: str, timeframe: str, smc_result: dict) -> int:
        """
        SMC Engine tahlil natijasidagi (dict) barcha yangi zonalarni bazaga saqlaydi.
        Duplikat bo'lsa IGNORE qiladi. Qancha yangi zona yozilganini qaytaradi.
        """
        inserted_count = 0
        
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            
            # 1. Order Blocks saqlash
            for direction in ["demand", "supply"]:
                for ob in smc_result.get("order_blocks", {}).get(direction, []):
                    ts = ob.get("timestamp")
                    if ts and str(ts) != "None":
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO zones 
                                (symbol, timeframe, zone_type, direction, level, origin, 
                                 top_price, bottom_price, status, creation_time, bar_index)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                symbol, timeframe, "ob", direction, 
                                ob.get("level", ""), ob.get("origin", ""),
                                ob["top"], ob["bottom"], ob["status"], 
                                str(ts)[:19], ob.get("bar_index", 0)
                            ))
                            if cursor.rowcount > 0:
                                inserted_count += 1
                        except sqlite3.Error as e:
                            print(f"DB OB Error: {e}")

            # 2. FVG larni saqlash
            for direction in ["demand", "supply"]:
                for fvg in smc_result.get("fvg", {}).get(direction, []):
                    ts = fvg.get("timestamp")
                    if ts and str(ts) != "None":
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO zones 
                                (symbol, timeframe, zone_type, direction, level, origin, 
                                 top_price, bottom_price, status, creation_time, bar_index)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                symbol, timeframe, "fvg", direction, 
                                "", "", 
                                fvg["top"], fvg["bottom"], fvg["status"], 
                                str(ts)[:19], fvg.get("bar_index", 0)
                            ))
                            if cursor.rowcount > 0:
                                inserted_count += 1
                        except sqlite3.Error as e:
                            print(f"DB FVG Error: {e}")
                            
            conn.commit()
            
        return inserted_count

    def update_mitigations(self, symbol: str, timeframe: str, current_high: float, current_low: float) -> int:
        """
        Jonli narx tebranishlariga qarab "fresh" zonalarni "mitigated" ga o'zgartiradi.
        Demand zona -> narx pastga qarab topsa (low <= top_price)
        Supply zona -> narx yuqoriga qarab topsa (high >= bottom_price)
        """
        mitigated_count = 0
        
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                
                # Bazadan faqat "fresh" zonalarni o'qish
                cursor.execute('''
                    SELECT id, direction, top_price, bottom_price 
                    FROM zones 
                    WHERE symbol = ? AND timeframe = ? AND status = 'fresh'
                ''', (symbol, timeframe))
                
                fresh_zones = cursor.fetchall()
                
                for zone_id, direction, top_price, bottom_price in fresh_zones:
                    is_mitigated = False
                    
                    if direction == "demand" and current_low < bottom_price:
                        is_mitigated = True
                    elif direction == "supply" and current_high > top_price:
                        is_mitigated = True
                        
                    if is_mitigated:
                        cursor.execute('''
                            UPDATE zones SET status = 'mitigated' WHERE id = ?
                        ''', (zone_id,))
                        mitigated_count += 1
                        
                conn.commit()
        except sqlite3.Error as e:
            print(f"DB Update Mitigations Error: {e}")
            
        return mitigated_count

    def get_nearby_zones(self, symbol: str, timeframe: str, current_price: float, threshold_pct: float = 0.5) -> List[Dict]:
        """
        Joriy narxga `threshold_pct` (masalan, 0.5%) masofada bo'lgan 
        barcha "fresh" zonalarni bazadan qidirib topadi. (AI uchun xabar)
        """
        nearby_zones = []
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM zones 
                    WHERE symbol = ? AND timeframe = ? AND status = 'fresh'
                    ORDER BY creation_time DESC
                ''', (symbol, timeframe))
                
                rows = cursor.fetchall()
                
            for row in rows:
                zone = dict(row)
                mid_price = (zone["top_price"] + zone["bottom_price"]) / 2
                
                distance_pct = abs(current_price - mid_price) / current_price * 100
                
                if distance_pct <= threshold_pct:
                    zone["distance_pct"] = round(distance_pct, 4)
                    nearby_zones.append(zone)
                    
            # Masofasi bo'yicha tartiblash (eng yaqinlari birinchi)
            nearby_zones.sort(key=lambda x: x["distance_pct"])
        except sqlite3.Error as e:
            print(f"DB Get Nearby Zones Error: {e}")
            
        return nearby_zones

    def get_stats(self, symbol: str, timeframe: str) -> dict:
        """Baza haqida qisqacha statistika qaytaradi."""
        status_counts = {}
        type_counts = {}
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT status, COUNT(*) FROM zones 
                    WHERE symbol = ? AND timeframe = ? 
                    GROUP BY status
                ''', (symbol, timeframe))
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                cursor.execute('''
                    SELECT zone_type, COUNT(*) FROM zones 
                    WHERE symbol = ? AND timeframe = ? 
                    GROUP BY zone_type
                ''', (symbol, timeframe))
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            print(f"DB Get Stats Error: {e}")
            
        return {
            "status": status_counts,
            "type": type_counts,
            "total": sum(status_counts.values())
        }

    def get_active_zones(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Supabase sync va UI uchun mos keladigan aktiv (fresh) zonalarni qaytaradi.
        `zone_type`, `direction`, `top`, `bottom`, `status`, `formed_at` maydonlari
        Supabase smc_zones jadvali va Frontend UI bilan 100% moslashtirilgan.
        """
        active_zones = []
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM zones 
                    WHERE symbol = ? AND timeframe = ? AND status = 'fresh'
                    ORDER BY creation_time DESC
                ''', (symbol, timeframe))
                
                rows = cursor.fetchall()
                
            for row in rows:
                z = dict(row)
                z_type = "order_block" if z["zone_type"] == "ob" else z["zone_type"]
                active_zones.append({
                    "symbol": z["symbol"],
                    "timeframe": z["timeframe"],
                    "zone_type": z_type,
                    "direction": z["direction"],
                    "top": float(z["top_price"]),
                    "bottom": float(z["bottom_price"]),
                    "status": z["status"],
                    "formed_at": str(z["creation_time"])
                })
        except sqlite3.Error as e:
            print(f"DB Get Active Zones Error: {e}")
            
        return active_zones

