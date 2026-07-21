import sqlite3
import threading
import logging
from typing import Optional, List, Tuple, Any, Dict

class DBManager:
    _instances: Dict[str, 'DBManager'] = {}
    _lock = threading.Lock()

    def __new__(cls, db_path: str):
        with cls._lock:
            if db_path not in cls._instances:
                instance = super(DBManager, cls).__new__(cls)
                instance._initialized = False
                cls._instances[db_path] = instance
            return cls._instances[db_path]

    def __init__(self, db_path: str):
        if self._initialized:
            return
        self.db_path = db_path
        self._local = threading.local()
        self.logger = logging.getLogger(__name__)
        self._initialized = True

    def _check_connection(self):
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.execute("SELECT 1")
            except sqlite3.Error:
                self._local.conn.close()
                self._local.conn = None

    def _get_connection(self) -> sqlite3.Connection:
        self._check_connection()
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = self._get_connection()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor
        except sqlite3.Error as e:
            self.logger.error(f"Database error on execute: {e}\nQuery: {query}")
            conn.rollback()
            raise

    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def migrate(self, table_name: str, column_defs: List[Tuple[str, str]]):
        """
        Helper to run ALTER TABLE ADD COLUMN migrations cleanly.
        column_defs should be a list of (column_name, column_type)
        """
        cursor = self.execute(f"PRAGMA table_info({table_name})")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        for col_name, col_type in column_defs:
            if col_name not in existing_cols:
                try:
                    self.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                    self.logger.info(f"Added column {col_name} to {table_name} in {self.db_path}")
                except sqlite3.Error as e:
                    self.logger.error(f"Error adding column {col_name} to {table_name}: {e}")
