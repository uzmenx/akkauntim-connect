"""
Unit test for SQLite database indexes creation across all system modules.
"""

import sys
from unittest.mock import MagicMock

# Mock numpy if not installed
try:
    import numpy
except ImportError:
    mock_np = MagicMock()
    mock_np.floating = float
    mock_np.integer = int
    sys.modules['numpy'] = mock_np

try:
    import pandas
except ImportError:
    sys.modules['pandas'] = MagicMock()

import os
import sqlite3
import tempfile
from bot.learning.shadow_collector import ShadowStateCollector
from bot.engine.merger_tracker import ShadowMergerTracker
from bot.engine.decision_logger import DecisionLogger
from bot.core.db_manager import DBManager
from bot.learning.ai_memory import AIMemory

def test_sqlite_indexes_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. ShadowStateCollector
        shadow_db = os.path.join(tmpdir, "shadow.db")
        collector = ShadowStateCollector(db_path=shadow_db)
        
        conn = sqlite3.connect(shadow_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='shadow_states'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "idx_shadow_symbol_time" in indexes
        assert "idx_shadow_sym_tf_ts" in indexes
        assert "idx_shadow_decision" in indexes
        print("✅ shadow_states indexes verified:", indexes)

        # 2. ShadowMergerTracker
        merger = ShadowMergerTracker(db_path=shadow_db)
        conn = sqlite3.connect(shadow_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='shadow_merger_tracking'")
        merger_indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "idx_smt_sym_ts" in merger_indexes
        assert "idx_smt_sym_tf" in merger_indexes
        print("✅ shadow_merger_tracking indexes verified:", merger_indexes)

        # 3. DecisionLogger
        dec_db = os.path.join(tmpdir, "decisions.db")
        logger_obj = DecisionLogger(db_path=dec_db)
        conn = sqlite3.connect(dec_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='ai_decisions'")
        dec_indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "idx_decisions_pair" in dec_indexes
        assert "idx_decisions_ticket" in dec_indexes
        assert "idx_decisions_pair_id" in dec_indexes
        print("✅ ai_decisions indexes verified:", dec_indexes)

        # 4. DBManager
        reg_db = os.path.join(tmpdir, "regime.db")
        db_mgr = DBManager(db_path=reg_db)
        conn = sqlite3.connect(reg_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='regime_history'")
        reg_indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "idx_regime_sym_tf" in reg_indexes
        assert "idx_regime_ts" in reg_indexes
        print("✅ regime_history indexes verified:", reg_indexes)

        # 5. AIMemory
        mem_db = os.path.join(tmpdir, "memory.db")
        mem_obj = AIMemory(db_path=mem_db)
        conn = sqlite3.connect(mem_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='ai_lessons'")
        mem_indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert "idx_lessons_active_cat" in mem_indexes
        print("✅ ai_lessons indexes verified:", mem_indexes)

    print("\n🎉 ALL SQLITE DATABASE INDEXING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_sqlite_indexes_creation()
