"""
bot/strategy/base_manager.py
============================
Base Strategy Memory Manager for institutional trading bot strategies.
Provides common SQLite thread-safe connection management, WAL mode, CRUD methods,
and lifecycle management (get_active, get_recent, mark_stale, clear_old_records).
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class BaseStrategyManager:
    """
    Base class for strategy memory & zone managers.
    Child classes define table schema and specific save/update logic.
    """
    def __init__(self, db_path: str, table_name: str):
        self.db_path = db_path
        self.table_name = table_name
        self._init_base_db()

    @contextmanager
    def get_connection(self):
        """
        Creates and configures SQLite connection with WAL mode and dict row factory.

        NOTE: `with sqlite3.Connection(...) as conn:` on its own only manages
        commit/rollback — it does NOT close the connection (this is documented
        Python behavior, not a bug in sqlite3). Every call site in this class
        used that pattern without ever closing, which leaked one open SQLite
        connection per call. With 94 symbols re-syncing every few minutes,
        this accumulated into hundreds of open handles per cycle and was the
        direct cause of "database is locked" errors. Making this method an
        actual contextmanager (with try/finally close) fixes every call site
        below with no other code changes needed, since they already use
        `with self.get_connection() as conn:`.
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_base_db(self):
        """
        Base DB setup hook. Called during initialization.
        Child classes should override _init_db to create their specific tables.
        """
        self._init_db()

    def _init_db(self):
        """
        Override in child classes to create specific tables and indexes.
        """
        pass

    def get_active(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Fetches active/fresh records for a specific symbol and timeframe.
        """
        records = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    SELECT * FROM {self.table_name}
                    WHERE symbol = ? AND timeframe = ? AND status IN ('active', 'fresh')
                    ORDER BY id DESC
                """
                cursor.execute(query, (symbol, timeframe))
                rows = cursor.fetchall()
                records = [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"[{self.__class__.__name__}] Error in get_active: {e}")
        return records

    def get_recent(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches recent records with optional status filter.
        """
        records = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if status:
                    query = f"""
                        SELECT * FROM {self.table_name}
                        WHERE symbol = ? AND timeframe = ? AND status = ?
                        ORDER BY id DESC LIMIT ?
                    """
                    cursor.execute(query, (symbol, timeframe, status, limit))
                else:
                    query = f"""
                        SELECT * FROM {self.table_name}
                        WHERE symbol = ? AND timeframe = ?
                        ORDER BY id DESC LIMIT ?
                    """
                    cursor.execute(query, (symbol, timeframe, limit))
                rows = cursor.fetchall()
                records = [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"[{self.__class__.__name__}] Error in get_recent: {e}")
        return records

    def mark_stale(self, record_id: int, status: str = "stale") -> bool:
        """
        Marks a specific record as stale/mitigated/inactive.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"UPDATE {self.table_name} SET status = ? WHERE id = ?"
                cursor.execute(query, (status, record_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"[{self.__class__.__name__}] Error in mark_stale: {e}")
            return False

    def clear_old_records(self, days: int = 30) -> int:
        """
        Deletes records created earlier than the specified number of days.
        """
        deleted_count = 0
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"DELETE FROM {self.table_name} WHERE created_at < ?"
                cursor.execute(query, (cutoff_date,))
                conn.commit()
                deleted_count = cursor.rowcount
        except sqlite3.Error as e:
            print(f"[{self.__class__.__name__}] Error in clear_old_records: {e}")
        return deleted_count

    def count_records(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Returns count of records matching optional filters.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                conditions = []
                params = []
                if symbol:
                    conditions.append("symbol = ?")
                    params.append(symbol)
                if timeframe:
                    conditions.append("timeframe = ?")
                    params.append(timeframe)
                if status:
                    conditions.append("status = ?")
                    params.append(status)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                query = f"SELECT COUNT(*) FROM {self.table_name} {where_clause}"
                cursor.execute(query, params)
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"[{self.__class__.__name__}] Error in count_records: {e}")
            return 0

    def update_mitigations(self, symbol: str, timeframe: str, current_high: float, current_low: float) -> int:
        """
        Jonli narx yoki vaqt tebranishlariga qarab "fresh" zonalarni "stale" ga o'zgartiradi.
        Barcha child class'lar uchun umumiy vaqtga asoslangan tozalash (48 soat).
        Maxsus narxga asoslangan mantiqni child class'larda override qilish mumkin.
        """
        stale_count = 0
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    UPDATE {self.table_name} 
                    SET status = 'stale' 
                    WHERE symbol = ? AND timeframe = ? AND status IN ('active', 'fresh') 
                    AND created_at < datetime('now', '-2 days')
                """
                cursor.execute(query, (symbol, timeframe))
                conn.commit()
                stale_count = cursor.rowcount
        except sqlite3.Error as e:
            print(f"[{self.__class__.__name__}] Error in update_mitigations: {e}")
        return stale_count
